import os
import subprocess
import time
import getpass

import pytest

import subscript.fmu_copy_revision.fmu_copy_revision as fcr

SCRIPTNAME = "fmu_copy_revision"

TOPLEVELS = ["r001", "r002", "20.1.1", "19.2.1", "32.1.1", "something", "users"]

# file structure under folders TOPLEVELS
FILESTRUCTURE = [
    "rms/model/workflow.log",
    "rms/input/faults/f1.dat",
    "rms/input/faults/f2.dat",
    "rms/input/faults/f3.dat",
    ".git/some.txt",
    "attic/any.file",
    "backup/whatever.txt",
    "somefolder/any.backup",
    "somefolder/anybackup99.txt",
    "somefolder/attic/any.txt",
]


@pytest.fixture(name="datatree", scope="session", autouse=True)
def fixture_datatree(tmp_path_factory):
    """Create a tmp folder structure for testing."""
    tmppath = tmp_path_factory.mktemp("data")
    for top in TOPLEVELS:
        (tmppath / top).mkdir(parents=True, exist_ok=True)
        for fil in FILESTRUCTURE:
            (tmppath / fil).parent.mkdir(parents=True, exist_ok=True)
            (tmppath / fil).touch()

    print("Temporary folder: ", tmppath)
    return tmppath


def test_version(capsys):
    """Testing exclude pattern 1."""
    with pytest.raises(SystemExit):
        fcr.main(["--version"])
    out, _ = capsys.readouterr()
    assert "subscript version" in out


def test_rsync_exclude1(datatree):
    """Testing exclude pattern 1."""
    os.chdir(datatree)
    fcr.main(["--source", "20.1.1"])
    assert (datatree / "rms/model/workflow.log").is_file()
    print("OK")


def test_construct_target(datatree):
    """Test the construct target routine."""

    os.chdir(datatree)
    today = time.strftime("%Y%m%d")
    user = getpass.getuser()
    expected = "users/" + user + "/20.1.1/20.1.1" + "_" + today

    target = fcr.construct_target("20.1.1")

    assert str(target) == expected
    assert target.absolute() == datatree / expected

    target = fcr.construct_target(str(datatree / "20.1.1"))
    assert target.absolute() == datatree / expected


def test_construct_target_shall_fail(datatree):
    """Test the construct target routine with non-existing folder."""
    os.chdir(datatree)

    with pytest.raises(ValueError) as verr:
        _ = fcr.construct_target("something_wrong")

    assert "Input folder does not exist" in str(verr)


@pytest.mark.integration
def test_integration():
    """Test that the endpoint is installed."""
    assert subprocess.check_output([SCRIPTNAME, "-h"])
