import tempfile
import pathlib
import time
import shutil
import pytest

from subscript.fmu_copy_revision import fmu_copy_revision

TOPLEVELS = ["r001", "r002", "20.1.1", "19.2.1", "32.1.1", "something"]

# file structure under folders TOPLEVELS
FILESTRUCTURE = [
    "rms/model/workflow.log",
    "rms/input/faults/f1.dat",
    "rms/input/faults/f2.dat",
    "rms/input/faults/f3.dat",
    ".git/some.txt",
    "attic/any.file" "backup/whatever.txt",
    "somefolder/any.backup" "somefolder/anybackup99.txt" "somefolder/attic/any.txt",
]

TMPDIR = pathlib.Path(tempfile.mkdtemp())

print(f"\nTMP FOLDER is {TMPDIR}\n")


@pytest.fixture(name="create_revision", scope="session", autouse=True)
def fixture_create_revison():
    """Create a tmp folder structure for testing."""
    for top in TOPLEVELS:
        (TMPDIR / top).mkdir(parents=True, exist_ok=True)
        for fil in FILESTRUCTURE:
            (TMPDIR / fil).parent.mkdir(parents=True, exist_ok=True)
            (TMPDIR / fil).touch()

    yield
    print("Tear down!")
    print("Remove TMPDIR in 5 seconds...")  # can take ctrl-C and check files
    time.sleep(5)
    shutil.rmtree(TMPDIR)


def test_help():
    """Testing exclude pattern 1."""
    fmu_copy_revision.main(--help)
    print("OK")


def test_rsync_exclude1():
    """Testing exclude pattern 1."""
    assert (TMPDIR / "rms/model/workflow.log").is_file()
    print("OK")
