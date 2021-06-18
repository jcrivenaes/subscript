#!/usr/bin/env python
#
# fmu_copy_revision, for fast and secure copy for fmu revisions
#

# Some variables are here named to conform to something else than PEP8
# pylint: disable=invalid-name

import os
import sys
from os.path import join
import argparse
import pathlib
import tempfile
import time
import subprocess
from typing import List


from subscript import __version__

DESCRIPTION = """This is a simple interactive script for copying a FMU revision folder
with options of:
    1. Selective copy, i.e. avoid data that can be regenerated
    2. Speed up copying by multiprocessing
    3. Retain dates and user permissions (simple cp command not good at that)
"""

EXCLUDE1 = """ """

EXCLUDE2 = """
backup
users
attic
*.git
*.svn
*~
"""

EXCLUDE3 = (
    EXCLUDE2
    + """
ert/output
ert/storage
ert/*/storage
input/seismic
model/*.log
rms/output/**
spotfire/**/*.csv
spotfire/**/*.dxp
share/results
share/templates
"""
)

SHELLSCRIPT = """\
#!/usr/bin/sh

# SETUP OPTIONS
export SRCDIR="$1"  # a relative path
export DESTDIR="$2"  # must be an absolute path!
export EXCLUDEFILE=$3

THREADS=$4


PWD=$(pwd)

start=`date +%s.%N`

# FIND ALL FILES AND PASS THEM TO MULTIPLE RSYNC PROCESSES
cd $SRCDIR

find . -type d | xargs -I% mkdir -p $DESTDIR/%
find -L . -type f | xargs -n1 -P$THREADS -I% \
   rsync -a --exclude-from=$EXCLUDEFILE % $DESTDIR/%

end=`date +%s.%N`

runtime=$( echo "$end - $start" | bc -l )

echo $runtime
cd $PWD

"""


def get_parser() -> argparse.ArgumentParser:
    """Setup parser."""

    usetext = "fmu_copy_revision <commandline> OR interactive"
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawTextHelpFormatter,
        usage=usetext,
    )

    parser.add_argument("--dryrun", action="store_true", help="Run dry run for testing")
    parser.add_argument("--all, -all, -a", action="store_true", help="List all folders")
    parser.add_argument("--source", dest="source", type=str, help="Add source folder")

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (subscript version " + __version__ + ")",
    )

    return parser


def do_parse_args(args):
    """Parse command line arguments"""

    if args is None:
        args = sys.argv[1:]

    parser = get_parser()

    args = parser.parse_args(args)

    return args


def check_folders():
    """Check if potential fmu folder are present."""

    current = pathlib.Path(".")
    folders = [fil for fil in current.iterdir() if fil.is_dir()]
    result = []
    for folder in folders:
        fname = folder.name
        if fname.startswith("r") or fname.startswith("2"):
            result.append(fname)

    inum = 0
    if result:
        result = sorted(result)
        for res in result:
            inum += 1
            print(f"{inum}:  {res}")

    return result


def menu1(folders):
    """Print an interactive menu to the user for which folder."""
    print("Choices:\n")

    inum = 0
    for res in folders:
        inum += 1
        print(f"{inum}:  {res}")

    try:
        select = int(input("Choose: "))
    except ValueError:
        print("Not a number")

    if select in range(1, len(folders) + 1):
        usefolder = folders[select - 1]
        print(f"Selection is valid, folder to use is {usefolder}")
    return usefolder


def menu2(folder):
    """Print an interactive menu to the user for target."""

    default = pathlib.Path(folder) / "user" / "folder"
    target = str(input(f"Choose (default is {default}): "))

    if not target:
        target = default
    else:
        target = pathlib.Path(target)

    print(f"Selected output target is {target}")
    return str(target.absolute())


def check_disk_space():
    """Checking diskspace if wanted."""
    print("Checking disk space... still dummy")


def show_possible_options_copy():
    """Show a menu for possuble options for copy/rsync."""

    print(
        """\

By default some file types and directories will be skipped. Here are some options:

1. Copy everything

2. Copy everything, except:
    * Files and folders containing 'backup' in name
    * Directories and files with name 'users'
    * Directories and files with name 'attic'
    * Directories and files with names '.git' or '.svn'
    * Files ending with ~

3. Copy everything, except:
    * Files and folders containing 'backup' and in name
    * Directories and files with name 'users'
    * Directories and files with name 'attic'
    * Directories and files with names '.git' or '.svn'
    * Files ending with ~
    * The following folders under ert/ (if they exist):
      - output
      - ert/*/storage, including ert/storage (for backw compat.)
    * The following folders or files under rms/ (if they exist):
      - input/seismic, model/*.log
    * The following files under rms/ (if they exist):
      - Files under output folders (folders will be kept!)
    * The following folders under spotfire/:
      - input/*.csv, input/*/.csv model/*.dxp, model/*/*.dxp
    * The following folders under share/:
      - results
      - templates

4. As option 3, but keeps more data:
    * Folder rms/output will be copied (~old behaviour)
    * Folders share/results and share/templates will be copied.

5. Only copy the <coviz> folder (if present), which shall be under
   rXXX/share/coviz:
    * Symbolic links will be kept, if possible

9. Make your own exclude pattern in a file. That file shall
   be put under <users/nnnn/.my_exclude> (where nnnn is your user name)
   In that file, simply input line by line like this:
   ert/output
   ert/plots
   rms/output/tmp
"""
    )

    default = "3"
    select = str(input(f"Choose (default is {default}): "))

    if not select:
        select = default

    select = int(select)

    return select


def define_exclude(option):
    """Define exclude pattern based on menu choice."""

    exclude = ""
    if option == 1:
        exclude = EXCLUDE1
    elif option == 2:
        exclude = EXCLUDE2
    elif option == 3:
        exclude = EXCLUDE3

    print(exclude)

    return exclude


def do_rsyncing(source, target, exclude):
    """Do the actual rsync job using shell."""

    print(f"Source is {source}")
    print(f"Target is {target}")
    print(f"Exclude is {exclude}")
    print(f"Script is {SHELLSCRIPT}")

    # write shellscript and exclude file to a temp folder
    tdir = tempfile.TemporaryDirectory()
    print(tdir.name)
    print(tdir)
    scriptname = join(tdir.name, "rsync.sh")
    excludename = join(tdir.name, "exclude.txt")

    with open(scriptname, "w") as stream:
        stream.write(SHELLSCRIPT)

    with open(excludename, "w") as stream:
        stream.write(exclude)

    nthreads = 6

    # execute
    command = ["sh", scriptname, source, target, excludename, str(nthreads)]
    print(" ".join(command))

    process = subprocess.run(command, check=True, shell=False, capture_output=True)

    print(process)
    print(process.returncode)
    print(process.stdout)
    # os.system(" ".join(command))


def main(args=None) -> None:
    """Entry point from command line."""

    args = do_parse_args(args)
    if not args.source:
        # interactive menues
        folders = check_folders()
        source = menu1(folders)
        target = menu2(source)
        check_disk_space()
        option = show_possible_options_copy()
    else:
        # command line only (some checks will be missing)
        print("Command line mode only")
        pass

    exclude = define_exclude(option)
    do_rsyncing(source, target, exclude)


if __name__ == "__main__":
    main(sys.argv)
