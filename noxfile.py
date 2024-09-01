"""noxfile."""

import nox

nox.options.default_venv_backend = "uv"


def run_with_uv(*args):
    """Prepend the command with 'uv run'."""
    return ("uv", "run") + args


@nox.session()
def tests(session: nox.Session) -> None:
    """Run the tests."""
    cmd = run_with_uv("pytest")
    session.run(*cmd)


@nox.session()
def lint(session: nox.Session) -> None:
    """Run the linter."""
    cmd = run_with_uv("ruff", "check", ".")
    session.run(*cmd)


@nox.session()
def typing(session: nox.Session) -> None:
    """Run the type checker."""
    cmd = run_with_uv(
        "mypy",
        ".",
        "--enable-incomplete-feature=NewGenericSyntax",
        "--junit-xml",
        "mypy_report.xml",
    )
    session.run(*cmd)
