""" The module provides the command line interface to subtidy.
    It parses areguments, and does backup file management.
"""

import click
import os.path
import shutil
import sys
import traceback

from . import __version__
from . import subtidy_lib


# -----------------------------------------------------------------------------
#
def process_argument(filename, indent, spacing, width):
    """ This function process, as in reformats, the specified filename.
        Before formatting, it create a backup or backups.
    """
    try:
        backup = filename + ".~"

        print(filename)

        # Create an immediate bakup and upto 4 backup backups.
        #
        try:
            b1 = f"{filename}.1~"
            b2 = f"{filename}.2~"
            b3 = f"{filename}.3~"
            b4 = f"{filename}.4~"

            if os.path.isfile(backup):
                if os.path.isfile(b1):
                    if os.path.isfile(b2):
                        if os.path.isfile(b3):
                            os.rename(b3, b4)
                        os.rename(b2, b3)
                    os.rename(b1, b2)
                os.rename(backup, b1)
        except BaseException:
            pass

        # Create a backup file.
        # Note: we copy, as opposed to do moving original, file to create the back up
        # and there by create a new file; and then process from the backup file back
        # to the original file. In this way, filename remains the same file and gets
        # updated. This preserves attributes and, at least on Linux, the inode number
        # and any file-system hard links to the file are preserved.
        #
        shutil.copy(filename, backup)

        subtidy_lib.process_file(filename, indent=indent, spacing=spacing, width=width)
        return 0

    except Exception:
        traceback.print_exc()
        return 2


# -----------------------------------------------------------------------------
#
def print_version():
    vi = sys.version_info
    print(f"subtidy version: {__version__}  (python {vi.major}.{vi.minor}.{vi.micro})")


# -----------------------------------------------------------------------------
#
def main(filenames, indent=4, spacing=2, width=120):
    """ Ths main function organises the actual work.
        Call wehen subtidy used as a library
    """
    status = 0
    if len(filenames) == 0:
        try:
            subtidy_lib.process(sys.stdin, sys.stdout, indent=indent, spacing=spacing, width=width)
        except Exception:
            traceback.print_exc()
            status = 2
    else:
        print_version()
        for filename in filenames:
            s = process_argument(filename, indent=indent, spacing=spacing, width=width)
            status = max(status, s)
        print("complete")

    return status


# ------------------------------------------------------------------------------
# click stuff
# ------------------------------------------------------------------------------
#
def print_version_eager(ctx, param, value):
    """ Click parser helper function
    """
    if not value or ctx.resilient_parsing:
        return

    print_version()
    ctx.exit()


# Allow -h as well as --help
#
context_settings = dict(help_option_names=['--help', '-h'],
                        terminal_width=108,
                        max_content_width=112)


@click.command(context_settings=context_settings,
               epilog="""\b
 """)
@click.option('--version', '-V',
              is_flag=True,
              callback=print_version_eager,
              expose_value=False,
              is_eager=True,
              help="Show version and exit.")
@click.option('--indent', '-i',
              type=click.IntRange(1, 8),
              default=4,
              show_default=True,
              help="""Specifies indent (range 1 to 8).""")
@click.option('--spacing', '-s',
              type=click.IntRange(1, 8),
              default=2,
              show_default=True,
              help="""Specifies spacing (range 1 to 8).""")
@click.option('--width', '-w',
              type=click.IntRange(60, 800),
              default=120,
              show_default=True,
              help="""Specifies maximum output width (range 60 to 800).""")
@click.argument('filenames', nargs=-1)
def cli(indent, spacing, width, filenames):
    """
Copyright (c) 2022-2024  Andrew C. Starritt

subtidy performs layout formatting on one or more EPICS substitution files.
Prior to formating, a backup copy of each file is created with the name
'<filename>.~'.

When no files names are provided, subtidy reads from stdin and writes
to stdout.

Note: subtidy (currently) only handles substitution using the pattern
paradigm, e.g.:

\b
\x1b[37;1m# start
#
\b
file "db/xyz.template" {  # Comment
    pattern { X,      Y,      Z       }  # Comment
            { "AAAA", "BB",   "CC"    }  # Comment
            { "DD",   "EEEE", "FF"    }  # Comment
            { "GG",   "HH",   "IIJJJ" }  # Comment
}

# end\x1b[00m
    """

    status = main(filenames, indent, spacing, width)
    os._exit(status)


# -----------------------------------------------------------------------------
# Set env variables for click and python 3, does no harm for python 2
# Command line entry point for setup
#
def call_cli():
    os.environ["LANG"] = "en_US.utf8"
    os.environ["LC_ALL"] = "en_US.utf8"
    cli()

# end
