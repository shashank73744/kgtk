"""
This runs the Posix sort command to sort KGTK files.
A backgropund data processing pipeline is initiated that
runs in parallel with the Python process.

1) The data processing pipeline reads stdin or a named file.
   The named file is fed to the data processing pipeline by `cat`,
   avoiding having it read by Python.

2) The header line is stripped out of the input stream by a
   shell `read` command.

3) The header line is then coped to the output stream using a shell
   'printf' command.

4) A copy of the header line is sent via a pipe to the Python control
   process.

5) The data processing pipeline then waits to read sort options
   from a second pipe.

6) The Python control process feeds the header line to KgtkReader and
   and builds the sort key options.

6) The sort key options are sent from Python to the data processing pipeline
   via the second pipe.

7) The data processing pipeline receives the sort command options via
   the shell `read` command, and passes them to the `sort` program.

8) The sort command reads the rest of the input stream,
   sorts it, and writes the sorted data ro the output stream.
"""
from argparse import Namespace, SUPPRESS
import typing

from kgtk.cli_argparse import KGTKArgumentParser, KGTKFiles
from kgtk.exceptions import KGTKException

def parser():
    return {
        'help': 'Sort file based on one or more columns',
        'aliases': ['sort2']
    }

def add_arguments_extended(parser: KGTKArgumentParser, parsed_shared_args: Namespace):
    from kgtk.io.kgtkreader import KgtkReader, KgtkReaderOptions
    from kgtk.utils.argparsehelpers import optional_bool
    from kgtk.value.kgtkvalueoptions import KgtkValueOptions

    _expert: bool = parsed_shared_args._expert

    # This helper function makes it easy to suppress options from
    # The help message.  The options are still there, and initialize
    # what they need to initialize.
    def h(msg: str)->str:
        if _expert:
            return msg
        else:
            return SUPPRESS

    parser.add_input_file(positional=True, metavar="INPUT",
                          who="Input file to sort.")
    parser.add_output_file(options=['-o', '--out', '--output-file'],
                           who='Output file to write to.')

    parser.add_argument('-c', '--column', '--columns', action='store', dest='columns', nargs='*',
                        help="space and/or comma-separated list of column names to sort on. " +
                        "(defaults to id for node files, " +
                        "(node1, label, node2) for edge files without ID, (id, node1, label, node2) for edge files with ID)")

    parser.add_argument(      '--locale', dest='locale', type=str, default='C',
                              help="LC_ALL locale controls the sorting order. (default=%(default)s)")

    parser.add_argument('-r', '--reverse', dest='reverse', metavar="True|False",
                        help="When True, generate output in reverse sort order. (default=%(default)s)",
                        type=optional_bool, nargs='?', const=True, default=False)

    parser.add_argument(      '--pure-python', dest='pure_python', metavar="True|False",
                        help="When True, sort in-memory with Python code. (default=%(default)s)",
                        type=optional_bool, nargs='?', const=True, default=False)

    parser.add_argument('-X', '--extra', default='', action='store', dest='extra',
                        help="extra options to supply to the sort program. (default=None)")

    parser.add_argument(      '--bash-command', dest='bash_command', type=str, default="bash",
                        help=h("The bash command or its substitute. (default=%(default)s)"))

    parser.add_argument(      '--bzip2-command', dest='bzip2_command', type=str, default="bzip2",
                        help=h("The bzip2 command or its substitute. (default=%(default)s)"))

    parser.add_argument(      '--gzip-command', dest='gzip_command', type=str, default="gzip",
                        help=h("The gzip command or its substitute. (default=%(default)s)"))

    parser.add_argument(      '--pgrep-command', dest='pgrep_command', type=str, default="pgrep",
                        help=h("The pgrep command or its substitute. (default=%(default)s)"))

    parser.add_argument(      '--sort-command', dest='sort_command', type=str, default="sort",
                        help=h("The sort command or its substitute. (default=%(default)s)"))

    parser.add_argument(      '--xz-command', dest='xz_command', type=str, default="xz",
                        help=h("The xz command or its substitute. (default=%(default)s)"))

    KgtkReader.add_debug_arguments(parser, expert=_expert)
    KgtkReaderOptions.add_arguments(parser, mode_options=True, expert=_expert)
    KgtkValueOptions.add_arguments(parser, expert=_expert)

def custom_progress()->bool:
    return True # We want to start a custom progress monitor.

header_read_fd : int = -1
header_write_fd: int = -1
sortopt_read_fd : int = -1
sortopt_write_fd: int = -1
cat_proc = None
cmd_proc = None
def cleanup():
    # Clean up the file descriptors and processes, just in case.
    import os
    if header_read_fd >= 0:
        try:
            os.close(header_read_fd)
        except os.error:
            pass

    if header_write_fd >= 0:
        try:
            os.close(header_write_fd)
        except os.error:
            pass
            
    if sortopt_read_fd >= 0:
        try:
            os.close(sortopt_read_fd)
        except os.error:
            pass
            
    if sortopt_write_fd >= 0:
        try:
            os.close(sortopt_write_fd)
        except os.error:
            pass
            
    global cat_proc
    if cat_proc is not None:
        try:
            cat_proc.kill_group()
        except os.error:
            pass
        cat_proc = None

    global cmd_proc
    if cmd_proc is not None:
        try:
            cmd_proc.kill_group()
        except os.error:
            pass
        cat_proc = None

def keyboard_interrupt():
    cleanup()

def run(input_file: KGTKFiles,
        output_file: KGTKFiles,
        columns: typing.Optional[typing.List[str]] = None,
        locale: str = "C",
        reverse: bool = False,
        pure_python: bool = False,
        extra: typing.Optional[str] = None,

        bash_command: str = "bash",
        bzip2_command: str = "bzip2",
        gzip_command: str = "gzip",
        pgrep_command: str = "pgrep",
        sort_command: str = "sort",
        xz_command: str = "xz",

        errors_to_stdout: bool = False,
        errors_to_stderr: bool = True,
        show_options: bool = False,
        verbose: bool = False,
        very_verbose: bool = False,

        **kwargs # Whatever KgtkFileOptions and KgtkValueOptions want.       
)->int:
    from io import StringIO
    import os
    from pathlib import Path
    import sh # type: ignore
    import sys
    import typing

    from kgtk.cli_entry import progress_startup
    from kgtk.kgtkformat import KgtkFormat
    from kgtk.io.kgtkreader import KgtkReader, KgtkReaderOptions
    from kgtk.io.kgtkwriter import KgtkWriter
    from kgtk.value.kgtkvalueoptions import KgtkValueOptions

    input_path: Path = KGTKArgumentParser.get_input_file(input_file)
    output_path: Path = KGTKArgumentParser.get_output_file(output_file)

    # Select where to send error messages, defaulting to stderr.
    error_file: typing.TextIO = sys.stdout if errors_to_stdout else sys.stderr

    # Build the option structures.
    reader_options: KgtkReaderOptions = KgtkReaderOptions.from_dict(kwargs)
    value_options: KgtkValueOptions = KgtkValueOptions.from_dict(kwargs)

    def python_sort():
        if verbose:
            print("Opening the input file: %s" % str(input_path), file=error_file, flush=True)
        kr: KgtkReader = KgtkReader.open(input_path,
                                         options=reader_options,
                                         value_options = value_options,
                                         error_file=error_file,
                                         verbose=verbose,
                                         very_verbose=very_verbose,
        )

        sort_idx: int
        key_idxs: typing.List[int] = [ ]
        if columns is not None and len(columns) > 0:
            # Process the list of column names, including splitting
            # comma-separated lists of column names.
            column_name: str
            for column_name in columns:
                column_name_2: str
                for column_name_2 in column_name.split(","):
                    column_name_2 = column_name_2.strip()
                    if len(column_name_2) == 0:
                        continue
                    if column_name_2.isdigit():
                        sort_idx = int(column_name_2)
                        if sort_idx > len(kr.column_names):
                            kr.close()
                            cleanup()
                            raise KGTKException("Invalid column number %d (max %d)." % (sort_idx, len(kr.column_names)))
                        key_idxs.append(sort_idx - 1)
                    else:
                        if column_name_2 not in kr.column_names:
                            kr.close()
                            cleanup()
                            raise KGTKException("Unknown column_name %s" % column_name_2)
                        key_idxs.append(kr.column_name_map[column_name_2])
        else:
            if kr.is_node_file:
                key_idxs.append(kr.id_column_idx)

            elif kr.is_edge_file:
                if kr.id_column_idx >= 0:
                    key_idxs.append(kr.id_column_idx)

                key_idxs.append(kr.node1_column_idx)
                key_idxs.append(kr.label_column_idx)
                key_idxs.append(kr.node2_column_idx)
            else:
                cleanup()
                raise KGTKException("Unknown KGTK file mode, please specify the sorting columns.")

        if verbose:
            print("sorting keys: %s" % " ".join([str(x) for x in key_idxs]), file=error_file, flush=True)


        lines: typing.MutableMapping[str, typing.List[str]] = dict()

        progress_startup()
        key: str
        row: typing.List[str]
        for row in kr:
            key = KgtkFormat.KEY_FIELD_SEPARATOR.join(row[idx] for idx in key_idxs)
            lines[key] = row
        if verbose:
            print("\nRead %d data lines." % len(lines), file=error_file, flush=True)

        kw = KgtkWriter.open(kr.column_names,
                             output_path,
                             mode=KgtkWriter.Mode[kr.mode.name],
                             verbose=verbose,
                             very_verbose=very_verbose)
        for key in sorted(lines.keys()):
            kw.write(lines[key])
        kw.close()
        kr.close()

    if pure_python:
        return python_sort()

    try:
        global header_read_fd
        global header_write_fd
        header_read_fd, header_write_fd = os.pipe()
        os.set_inheritable(header_write_fd, True)
        if verbose:
            print("header pipe: read_fd=%d write_fd=%d" % (header_read_fd, header_write_fd), file=error_file, flush=True)
        
        global sortopt_read_fd
        global sortopt_write_fd
        sortopt_read_fd, sortopt_write_fd = os.pipe()
        os.set_inheritable(sortopt_read_fd, True)
        if verbose:
            print("sort options pipe: read_fd=%d write_fd=%d" % (sortopt_read_fd, sortopt_write_fd), file=error_file, flush=True)

        locale_envar: str = "LC_ALL=%s" % locale if len(locale) > 0 else ""

        # Note: "read -u n", used below, is not supported by some shells.
        # bash and zsh support it.
        # ash, csh, dash, and tcsh do not.
        # The original standard Bourne shell, sh, does not.
        # ksh might do it, if the FD number is a single digit.
        cmd: str = "".join((
            "{ IFS= read -r header ; ", # Read the header line
            " { printf \"%s\\n\" \"$header\" >&" +  str(header_write_fd) + " ; } ; ", # Send the header to Python
            " printf \"%s\\n\" \"$header\" ; ", # Send the header to standard output (which may be redirected to a file, below).
            " IFS= read -u " + str(sortopt_read_fd) + " -r options ; ", # Read the sort command options from Python.
            " %s %s -t '\t' $options ; } " % (locale_envar, sort_command), # Sort the remaining input lines using the options read from Python.
        ))
        if str(output_path) != "-":
            # Do we want to compress the output?
            output_suffix: str = output_path.suffix.lower()
            if output_suffix in [".gz", ".z"]:
                if verbose:
                    print("gzip output file: %s" % repr(str(output_path)), file=error_file, flush=True)
                cmd += " | " + gzip_command + " -"

            elif output_suffix in [".bz2", ".bz"]:
                if verbose:
                    print("bzip2 output file: %s" % repr(str(output_path)), file=error_file, flush=True)
                cmd += " | " + bzip2_command + " -z"

            elif output_suffix in [".xz", ".lzma"]:
                if verbose:
                    print("xz output file: %s" % repr(str(output_path)), file=error_file, flush=True)
                cmd += " | " + xz_command + " -z -"

            # Feed the sorted output to the named file.  Otherwise, the sorted
            # output goes to standard output without passing through Python.
            cmd += " > " + repr(str(output_path))

        if verbose:
            print("sort command: %s" % cmd, file=error_file, flush=True)

        global cat_proc
        cat_proc = None
        global cmd_proc
        cmd_proc = None

        def cat_done(cmd, success, exit_code):
            # When the cat command finishes, monitor the progress of the sort command.
            if verbose:
                print("\nDone reading the input file", file=error_file, flush=True)
            if cmd_proc is None:
                return

            # Locate the sort command using pgrep
            buf = StringIO()
            try:
                sh_pgrep = sh.Command(pgrep_command)
                sh_pgrep("-g", cmd_proc.pgid, "--newest", sort_command, _out=buf)
                pgrep_output = buf.getvalue()
                if len(pgrep_output) == 0:
                    if verbose:
                        print("Unable to locate the sort command.", file=error_file, flush=True)
                    return
                sort_pid = int(pgrep_output)
            except Exception as e:
                if verbose:
                    print("Exception looking for sort command: %s" % str(e), file=error_file, flush=True)
                return
            finally:
                buf.close()

            if verbose:
                print("Monitoring the sort command (pid=%d)" % sort_pid, file=error_file, flush=True)
            progress_startup(pid=sort_pid)

        if str(input_path) == "-":
            # Read from standard input.
            #
            # Sh version 1.13 or greater is required for _pass_fds.
            sh_bash = sh.Command(bash_command)
            cmd_proc = sh_bash("-c", cmd, _in=sys.stdin, _out=sys.stdout, _err=sys.stderr,
                               _bg=True, _bg_exc=False, _internal_bufsize=1,
                               _pass_fds={header_write_fd, sortopt_read_fd})

            # It would be nice to monitor the sort command here.  Unfortunately, there
            # is a race condition that makes this difficult.  We could loop until the
            # sort command is created, then monitor it.

        else:
            # Feed the named file into the data processing pipeline,
            input_suffix: str = input_path.suffix.lower()
            if input_suffix in [".gz", ".z"]:
                if verbose:
                    print("gunzip input file: %s" % repr(str(input_path)), file=error_file, flush=True)
                sh_gzip = sh.Command(gzip_command)
                cat_proc = sh_gzip(input_path, "-dc",
                                   _in=sys.stdin, _piped=True, _err=sys.stderr,
                                   _bg=True, _bg_exc=False, _internal_bufsize=1,
                                   _done=cat_done)

                if verbose:
                    print("full command: %s -dc %s | %s" % (gzip_command, repr(str(input_path)), cmd), file=error_file, flush=True)

            elif input_suffix in [".bz2", ".bz"]:
                if verbose:
                    print("bunzip2 input file: %s" % repr(str(input_path)), file=error_file, flush=True)
                sh_bzip2 = sh.Command(bzip2_command)
                cat_proc = sh_bzip2(input_path, "-dc",
                                    _in=sys.stdin, _piped=True, _err=sys.stderr,
                                    _bg=True, _bg_exc=False, _internal_bufsize=1,
                                    _done=cat_done)

                if verbose:
                    print("full command: %s -dc %s | %s" % (bzip2_command, repr(str(input_path)), cmd), file=error_file, flush=True)

            elif input_suffix in [".xz", ".lzma"]:
                if verbose:
                    print("unxz input file: %s" % repr(str(input_path)), file=error_file, flush=True)
                sh_xz = sh.Command(xz_command)
                cat_proc = sh_xz(input_path, "-dc",
                                 _in=sys.stdin, _piped=True, _err=sys.stderr,
                                 _bg=True, _bg_exc=False, _internal_bufsize=1,
                                 _done=cat_done)
                if verbose:
                    print("full command: %s -dc %s | %s" % (xz_command, repr(str(input_path)), cmd), file=error_file, flush=True)

            else:
                if verbose:
                    print("input file: %s" % repr(str(input_path)), file=error_file, flush=True)
                cat_proc = sh.cat(input_path, _in=sys.stdin, _piped=True, _err=sys.stderr,
                                  _bg=True, _bg_exc=False, _internal_bufsize=1,
                                  _done=cat_done)
                if verbose:
                    print("full command: cat %s | %s" % (repr(str(input_path)), cmd), file=error_file, flush=True)


            # If enabled, monitor the progress of reading the input file.
            # Since we do not have access to the pid of the sort command,
            # we cannot monitor the progress of the merge phases.
            if verbose:
                print("Monitoring the cat command (pid=%d)." % cat_proc.pid, file=error_file, flush=True)
            progress_startup(pid=cat_proc.pid)

            # Sh version 1.13 or greater is required for _pass_fds.
            sh_bash = sh.Command(bash_command)
            cmd_proc = sh_bash(cat_proc, "-c", cmd, _out=sys.stdout, _err=sys.stderr,
                               _bg=True, _bg_exc=False, _internal_bufsize=1,
                               _pass_fds={header_write_fd, sortopt_read_fd})
            # Since we do not have access to the pid of the sort command,
            # we cannot monitor the progress of the merge phases.

        if verbose:
            print("Running the sort script (pid=%d)." % cmd_proc.pid, file=error_file, flush=True)

        if verbose:
            print("Reading the KGTK input file header line with KgtkReader", file=error_file, flush=True)
        kr: KgtkReader = KgtkReader.open(Path("<%d" % header_read_fd),
                                         options=reader_options,
                                         value_options = value_options,
                                         error_file=error_file,
                                         verbose=verbose,
                                         very_verbose=very_verbose,
                                         )
        if verbose:
            print("KGTK header: %s" % " ".join(kr.column_names), file=error_file, flush=True)

        sort_options: str = ""
        if reverse:
            sort_options += " --reverse"

        if extra is not None and len(extra) > 0:
            sort_options += " " + extra

        sort_idx: int
        if columns is not None and len(columns) > 0:
            # Process the list of column names, including splitting
            # comma-separated lists of column names.
            column_name: str
            for column_name in columns:
                column_name_2: str
                for column_name_2 in column_name.split(","):
                    column_name_2 = column_name_2.strip()
                    if len(column_name_2) == 0:
                        continue
                    if column_name_2.isdigit():
                        sort_idx = int(column_name_2)
                        if sort_idx > len(kr.column_names):
                            kr.close()
                            cleanup()
                            raise KGTKException("Invalid column number %d (max %d)." % (sort_idx, len(kr.column_names)))
                    else:
                        if column_name_2 not in kr.column_names:
                            kr.close()
                            cleanup()
                            raise KGTKException("Unknown column_name %s" % column_name_2)
                        sort_idx = kr.column_name_map[column_name_2] + 1
                    sort_options += " -k %d,%d" % (sort_idx, sort_idx)
        else:
            if kr.is_node_file:
                sort_idx = kr.id_column_idx + 1
                sort_options += " -k %d,%d" % (sort_idx, sort_idx)

            elif kr.is_edge_file:
                if kr.id_column_idx >= 0:
                    sort_idx = kr.id_column_idx + 1
                    sort_options += " -k %d,%d" % (sort_idx, sort_idx)

                sort_idx = kr.node1_column_idx + 1
                sort_options += " -k %d,%d" % (sort_idx, sort_idx)

                sort_idx = kr.label_column_idx + 1
                sort_options += " -k %d,%d" % (sort_idx, sort_idx)

                sort_idx = kr.node2_column_idx + 1
                sort_options += " -k %d,%d" % (sort_idx, sort_idx)
            else:
                cleanup()
                raise KGTKException("Unknown KGTK file mode, please specify the sorting columns.")

        if verbose:
            print("sort options: %s" % sort_options, file=error_file, flush=True)

        kr.close() # We are done with the KgtkReader now.

        # Send the sort options back to the data processing pipeline.
        with open(sortopt_write_fd, "w") as options_file:
            options_file.write(sort_options + "\n")

        if verbose:
            print("\nWaiting for the sort command to complete.\n", file=error_file, flush=True)
        cmd_proc.wait()

        if verbose:
            print("Cleanup.", file=error_file, flush=True)
        cleanup()

        return 0

    except Exception as e:
        # import traceback
        # traceback.print_tb(sys.exc_info()[2], 10)
        raise KGTKException('INTERNAL ERROR: ' + type(e).__module__ + '.' + str(e) + '\n')

