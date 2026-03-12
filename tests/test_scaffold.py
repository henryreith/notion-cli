"""Scaffold tests — verify structure and imports work."""
import subprocess
import sys


def test_notion_version_import():
    from notion import __version__
    assert __version__ == "0.1.0"


def test_cli_importable():
    from notion.cli import cli
    assert cli is not None


def test_errors_importable():
    from notion.errors import ExitCode, AuthError, NotFoundError, ValidationError, ApiError
    assert ExitCode.SUCCESS == 0
    assert ExitCode.AUTH == 1
    assert ExitCode.NOT_FOUND == 2
    assert ExitCode.VALIDATION == 3
    assert ExitCode.API == 4
    assert ExitCode.EXISTS == 5
    assert ExitCode.AMBIGUOUS == 6
    assert ExitCode.DRY_RUN == 7


def test_cli_help(tmp_path):
    """notion --help exits 0 and shows all subgroups."""
    result = subprocess.run(
        [sys.executable, "-m", "notion", "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    output = result.stdout
    assert "auth" in output
    assert "db" in output
    assert "page" in output
    assert "block" in output
    assert "comment" in output
    assert "search" in output
    assert "user" in output


def test_cli_version():
    result = subprocess.run(
        [sys.executable, "-m", "notion", "--version"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "0.1.0" in result.stdout
