"""
Reorder KGTK file columns (while copying)

TODO: Need KgtkWriterOptions
"""

from argparse import Namespace, SUPPRESS
import typing

from kgtk.cli_argparse import KGTKArgumentParser, KGTKFiles

def parser():
    return {
        'help': 'Perform calculations on KGTK file columns.',
        'description': 'This command performs calculations on one or more columns in a KGTK file. ' +
        '\nIf no input filename is provided, the default is to read standard input. ' +
        '\n\nAdditional options are shown in expert help.\nkgtk --expert rename_columns --help'
    }


AVERAGE_OP: str = "average"
COPY_OP: str = "copy"
JOIN_OP: str = "join"
PERCENTAGE_OP: str = "percentage"
SET_OP: str = "set"
SUM_OP: str = "sum"

OPERATIONS: typing.List[str] = [ AVERAGE_OP,
                                 COPY_OP,
                                 JOIN_OP,
                                 PERCENTAGE_OP,
                                 SET_OP,
                                 SUM_OP,
                                ]

def add_arguments_extended(parser: KGTKArgumentParser, parsed_shared_args: Namespace):
    """
    Parse arguments
    Args:
        parser (argparse.ArgumentParser)
    """
    # import modules locally
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

    parser.add_input_file()
    parser.add_output_file()

    parser.add_argument(      "--output-format", dest="output_format", help=h("The file format (default=kgtk)"), type=str)

    parser.add_argument('-c', "--columns", dest="column_names", nargs='*',
                        metavar="COLUMN_NAME",
                        help="The list of source column names, optionally containing '..' for column ranges " +
                        "and '...' for column names not explicitly mentioned.")
    parser.add_argument(      "--into", dest="into_column_names",
                              help="The name of the column to receive the result of the calculation.",
                              required=True, nargs="+")
    parser.add_argument(      "--do", dest="operation", help="The name of the operation.", required=True,
                              choices=OPERATIONS)

    parser.add_argument(      "--values", dest="values", nargs='*',
                        metavar="VALUES",
                        help="An optional list of values")

    parser.add_argument(      "--format", dest="format_string", help="The format string for the calculation.")

    KgtkReader.add_debug_arguments(parser, expert=_expert)
    KgtkReaderOptions.add_arguments(parser, mode_options=True, expert=_expert)
    KgtkValueOptions.add_arguments(parser, expert=_expert)

def run(input_file: KGTKFiles,
        output_file: KGTKFiles,
        output_format: typing.Optional[str],

        column_names: typing.Optional[typing.List[str]],
        into_column_names: typing.List[str],
        operation: str,
        values: typing.Optional[typing.List[str]],
        format_string: typing.Optional[str],

        errors_to_stdout: bool = False,
        errors_to_stderr: bool = True,
        show_options: bool = False,
        verbose: bool = False,
        very_verbose: bool = False,

        **kwargs # Whatever KgtkFileOptions and KgtkValueOptions want.
)->int:
    # import modules locally
    from pathlib import Path
    import sys
    
    from kgtk.exceptions import KGTKException
    from kgtk.io.kgtkreader import KgtkReader, KgtkReaderOptions
    from kgtk.io.kgtkwriter import KgtkWriter
    from kgtk.value.kgtkvalueoptions import KgtkValueOptions

    input_kgtk_file: Path = KGTKArgumentParser.get_input_file(input_file)
    output_kgtk_file: Path = KGTKArgumentParser.get_output_file(output_file)

    # Select where to send error messages, defaulting to stderr.
    error_file: typing.TextIO = sys.stdout if errors_to_stdout else sys.stderr

    # Build the option structures.
    reader_options: KgtkReaderOptions = KgtkReaderOptions.from_dict(kwargs)
    value_options: KgtkValueOptions = KgtkValueOptions.from_dict(kwargs)

    # Show the final option structures for debugging and documentation.
    if show_options:
        print("--input-file=%s" % str(input_kgtk_file), file=error_file, flush=True)
        print("--output-file=%s" % str(output_kgtk_file), file=error_file, flush=True)
        if output_format is not None:
            print("--output-format=%s" % output_format, file=error_file, flush=True)
        if column_names is not None:
            print("--columns %s" % " ".join(column_names), file=error_file, flush=True)
        if into_column_names is not None:
            print("--into %s" % " ".join(into_column_names), file=error_file, flush=True)
        print("--operation=%s" % str(operation), file=error_file, flush=True)
        if values is not None:
            print("--values %s" % " ".join(values), file=error_file, flush=True)
        if format_string is not None:
            print("--format=%s" % format_string, file=error_file, flush=True)

        reader_options.show(out=error_file)
        value_options.show(out=error_file)
        print("=======", file=error_file, flush=True)

    try:

        if verbose:
            print("Opening the input file %s" % str(input_kgtk_file), file=error_file, flush=True)
        kr = KgtkReader.open(input_kgtk_file,
                             options=reader_options,
                             value_options = value_options,
                             error_file=error_file,
                             verbose=verbose,
                             very_verbose=very_verbose,
        )

        remaining_names: typing.List[str] = kr.column_names.copy()
        selected_names: typing.List[str] = [ ]
        save_selected_names: typing.Optional[typing.List[str]] = None

        ellipses: str = "..." # All unmentioned columns
        ranger: str = ".." # All columns between two columns.

        idx: int

        if column_names is None:
            column_names = [ ]

        saw_ranger: bool = False
        column_name: str
        for column_name in column_names:
            if column_name == ellipses:
                if save_selected_names is not None:
                    raise KGTKException("Elipses may appear only once")

                if saw_ranger:
                    raise KGTKException("Elipses may not appear directly after a range operator ('..').")

                save_selected_names = selected_names
                selected_names = [ ]
                continue

            if column_name == ranger:
                if len(selected_names) == 0:
                    raise KGTKException("The column range operator ('..') may not appear without a preceeding column name.")
                saw_ranger = True
                continue

            if column_name not in kr.column_names:
                raise KGTKException("Unknown column name '%s'." % column_name)
            if column_name not in remaining_names:
                raise KGTKException("Column name '%s' was duplicated in the list." % column_name)

            if saw_ranger:
                saw_ranger = False
                prior_column_name: str = selected_names[-1]
                prior_column_idx: int = kr.column_name_map[prior_column_name]
                column_name_idx: int = kr.column_name_map[column_name]
                start_idx: int
                end_idx: int
                idx_inc: int
                if column_name_idx > prior_column_idx:
                    start_idx = prior_column_idx + 1
                    end_idx = column_name_idx - 1
                    idx_inc = 1
                else:
                    start_idx = prior_column_idx - 1
                    end_idx = column_name_idx + 1
                    idx_inc = -1

                idx = start_idx
                while idx <= end_idx:
                    idx_column_name: str = kr.column_names[idx]
                    if idx_column_name not in remaining_names:
                        raise KGTKException("Column name '%s' (%s .. %s) was duplicated in the list." % (column_name, prior_column_name, column_name))
                   
                    selected_names.append(idx_column_name)
                    remaining_names.remove(idx_column_name)
                    idx += idx_inc

            selected_names.append(column_name)
            remaining_names.remove(column_name)

        if saw_ranger:
            raise KGTKException("The column ranger operator ('..') may not end the list of column names.")

        if len(remaining_names) > 0 and save_selected_names is None:
            if verbose:
                print("Omitting the following columns: %s" % " ".join(remaining_names), file=error_file, flush=True)
        if save_selected_names is not None:
            if len(remaining_names) > 0:
                save_selected_names.extend(remaining_names)
            if len(selected_names) > 0:
                save_selected_names.extend(selected_names)
            selected_names = save_selected_names

        sources: typing.List[int] = [ ]
        name: str
        for name in selected_names:
            sources.append(kr.column_name_map[name])

        new_column_count: int = 0
        into_column_idxs: typing.List[int] = [ ]
        into_column_idx: int
        output_column_names: typing.List[str] = kr.column_names.copy()
        into_column_name: str
        for idx, into_column_name in enumerate(into_column_names):
            if into_column_name in kr.column_name_map:
                into_column_idx = kr.column_name_map[into_column_name]
                into_column_idxs.append(into_column_idx)
                if verbose:
                    print("Putting result %d of the calculation into old column %d (%s)." % (idx + 1, into_column_idx, into_column_name), file=error_file, flush=True)
            else:
                new_column_count += 1
                into_column_idx = len(output_column_names)
                into_column_idxs.append(into_column_idx)
                output_column_names.append(into_column_name)
                if verbose:
                    print("Putting result %d of the calculation into new column %d (%s)." % (idx + 1, into_column_idx, into_column_name), file=error_file, flush=True)

        if verbose:
            print("Opening the output file %s" % str(output_kgtk_file), file=error_file, flush=True)
        kw: KgtkWriter = KgtkWriter.open(output_column_names,
                                         output_kgtk_file,
                                         require_all_columns=True,
                                         prohibit_extra_columns=True,
                                         fill_missing_columns=False,
                                         gzip_in_parallel=False,
                                         mode=KgtkWriter.Mode[kr.mode.name],
                                         output_format=output_format,
                                         verbose=verbose,
                                         very_verbose=very_verbose,
        )

        if values is None:
            values = [ ]

        if operation == AVERAGE_OP:
            if len(sources) == 0:
                raise KGTKException("Average needs at least one source, got %d" % len(sources))
            if len(into_column_idxs) != 1:
                raise KGTKException("Average needs 1 destination columns, got %d" % len(into_column_idxs))

        elif operation == COPY_OP:
            if len(sources) == 0:
                raise KGTKException("Copy needs at least one source, got %d" % len(sources))
            if len(selected_names) != len(into_column_idxs):
                raise KGTKException("Copy needs the same number of input columns and into columns, got %d and %d" % (len(selected_names), len(into_column_idxs)))

        elif operation == JOIN_OP:
            if len(sources) == 0:
                raise KGTKException("Join needs at least one source, got %d" % len(sources))
            if len(into_column_idxs) != 1:
                raise KGTKException("Join needs 1 destination columns, got %d" % len(into_column_idxs))
            if len(values) != 1:
                raise KGTKException("Join needs 1 value, got %d" % len(values))

        elif operation == PERCENTAGE_OP:
            if len(into_column_idxs) != 1:
                raise KGTKException("Percent needs 1 destination columns, got %d" % len(into_column_idxs))
            if len(selected_names) != 2:
                raise KGTKException("Percent needs 2 input columns, got %d" % len(selected_names))

        elif operation == SET_OP:
            if len(sources) != 0:
                raise KGTKException("Set needs no sources, got %d" % len(sources))
            if len(into_column_idxs) == 0:
                raise KGTKException("Set needs at least one destination column, got %d" % len(into_column_idxs))
            if len(values) == 0:
                raise KGTKException("Set needs at least one value, got %d" % len(values))
            if len(into_column_idxs) != len(values):
                raise KGTKException("Set needs the same number of destination columns and values, got %d and %d" % (len(into_column_idxs), len(values)))

        elif operation == SUM_OP:
            if len(sources) == 0:
                raise KGTKException("Sum needs at least one source, got %d" % len(sources))
            if len(into_column_idxs) != 1:
                raise KGTKException("Sum needs 1 destination columns, got %d" % len(into_column_idxs))

        fs: str = format_string if format_string is not None else "%5.2f"
        item: str
        
        into_column_idx = into_column_idxs[0] # for convenience

        input_data_lines: int = 0
        row: typing.List[str]
        for row in kr:
            input_data_lines += 1

            output_row: typing.List[str] = row.copy()
            for idx in range(new_column_count):
                output_row.append("") # Easiest way to add a new column.

            if operation == AVERAGE_OP:
                atotal: float = 0
                acount: int = 0
                for idx in sources:
                    item = row[idx]
                    if len(item) > 0:
                        atotal += float(item)
                        acount += 1
                output_row[into_column_idx] = (fs % (atotal / float(acount))) if acount > 0 else ""                

            elif operation == COPY_OP:
                for idx in range(len(sources)):
                    output_row[into_column_idxs[idx]] = row[sources[idx]]

            elif operation == JOIN_OP:
                output_row[into_column_idx] = values[0].join((row[sources[idx]] for idx in range(len(sources))))

            elif operation == PERCENTAGE_OP:
                output_row[into_column_idx] = fs % (float(row[sources[0]]) * 100 / float(row[sources[1]]))

            elif operation == SET_OP:
                for idx in range(len(values)):
                    output_row[into_column_idxs[idx]] = values[idx]

            elif operation == SUM_OP:
                total: float = 0
                for idx in sources:
                    item = row[idx]
                    if len(item) > 0:
                        total += float(item)
                output_row[into_column_idx] = fs % total
                

            kw.write(output_row)

        # Flush the output file so far:
        kw.flush()

        if verbose:
            print("Read %d data lines from file %s" % (input_data_lines, input_kgtk_file), file=error_file, flush=True)

        kw.close()

        return 0

    except SystemExit as e:
        raise KGTKException("Exit requested")
    except Exception as e:
        raise KGTKException(str(e))

