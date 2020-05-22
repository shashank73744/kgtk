"""
Concatenate KGTK files.

TODO: Need KgtkWriterOptions
"""

from argparse import Namespace, SUPPRESS
from pathlib import Path
import sys
import typing

from kgtk.cli_argparse import KGTKArgumentParser
from kgtk.io.kgtkreader import KgtkReader, KgtkReaderOptions
from kgtk.io.kgtkwriter import KgtkWriter
from kgtk.join.kgtkcat import KgtkCat
from kgtk.value.kgtkvalueoptions import KgtkValueOptions

def parser():
    return {
        'help': 'Concatenate KGTK files.',
        'description': 'Concatenate two or more KGTK files, merging the columns appropriately. ' +
        'All files must be KGTK edge files or all files must be KGTK node files (unless overridden with --mode=NONE). ' +
        '\n\nAdditional options are shown in expert help.\nkgtk --expert cat --help'
    }


def add_arguments_extended(parser: KGTKArgumentParser, parsed_shared_args: Namespace):
    """
    Parse arguments
    Args:
        parser (argparse.ArgumentParser)
    """

    _expert: bool = parsed_shared_args._expert

    # This helper function makes it easy to suppress options from
    # The help message.  The options are still there, and initialize
    # what they need to initialize.
    def h(msg: str)->str:
        if _expert:
            return msg
        else:
            return SUPPRESS

    parser.add_argument(      "input_file_paths", help="The KGTK files to concatenate.", type=Path, nargs='+', default=[Path("-")])

    parser.add_argument("-o", "--output-file", dest="output_file_path", help="The KGTK file to write (default=%(default)s).", type=Path, default="-")

    KgtkReader.add_debug_arguments(parser, expert=_expert)
    KgtkReaderOptions.add_arguments(parser, mode_options=True, expert=_expert)
    KgtkValueOptions.add_arguments(parser, expert=_expert)

def run(input_file_paths: typing.List[Path],
        output_file_path: Path,

        errors_to_stdout: bool = False,
        errors_to_stderr: bool = True,
        show_options: bool = False,
        verbose: bool = False,
        very_verbose: bool = False,

        **kwargs # Whatever KgtkFileOptions and KgtkValueOptions want.
)->int:
    # import modules locally
    from kgtk.exceptions import KGTKException


    # Select where to send error messages, defaulting to stderr.
    error_file: typing.TextIO = sys.stdout if errors_to_stdout else sys.stderr

    # TODO: check that at most one input file is stdin?

    # Build the option structures.
    reader_options: KgtkReaderOptions = KgtkReaderOptions.from_dict(kwargs)
    value_options: KgtkValueOptions = KgtkValueOptions.from_dict(kwargs)

    # Show the final option structures for debugging and documentation.
    if show_options:
        print("input: %s" % " ".join((str(input_file_path) for input_file_path in input_file_paths)), file=error_file)
        print("--output-file=%s" % str(output_file_path), file=error_file)
        reader_options.show(out=error_file)
        value_options.show(out=error_file)
        print("=======", file=error_file, flush=True)

    try:
        kc: KgtkCat = KgtkCat(input_file_paths=input_file_paths,
                              output_path=output_file_path,
                              reader_options=reader_options,
                              value_options=value_options,
                              error_file=error_file,
                              verbose=verbose,
                              very_verbose=very_verbose
        )
        
        kc.process()

        return 0

    except SystemExit as e:
        raise KGTKException("Exit requested")
    except Exception as e:
        raise KGTKException(str(e))
