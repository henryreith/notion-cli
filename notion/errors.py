import sys
from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0
    AUTH = 1
    NOT_FOUND = 2
    VALIDATION = 3
    API = 4
    EXISTS = 5
    AMBIGUOUS = 6
    DRY_RUN = 7


class NotionCliError(Exception):
    """Base error for notion-agent-cli."""
    exit_code: ExitCode = ExitCode.API

    def __init__(self, message: str, data: dict | None = None):
        super().__init__(message)
        self.data = data or {}


class AuthError(NotionCliError):
    exit_code = ExitCode.AUTH


class NotFoundError(NotionCliError):
    exit_code = ExitCode.NOT_FOUND


class ValidationError(NotionCliError):
    exit_code = ExitCode.VALIDATION


class ApiError(NotionCliError):
    exit_code = ExitCode.API


class ExistsError(NotionCliError):
    exit_code = ExitCode.EXISTS


class AmbiguousError(NotionCliError):
    exit_code = ExitCode.AMBIGUOUS


class DryRunError(NotionCliError):
    exit_code = ExitCode.DRY_RUN


def handle_error(err: NotionCliError) -> None:
    """Print error as JSON to stderr and exit with appropriate code."""
    import json
    data = {"error": str(err), **err.data}
    print(json.dumps(data), file=sys.stderr)
    sys.exit(err.exit_code)
