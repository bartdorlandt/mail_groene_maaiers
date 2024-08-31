"""noxfile."""
import nox

nox.options.default_venv_backend = "uv"


@nox.session()
def tests(session):
    session.run("pytest")


@nox.session()
def lint(session):
    session.run("ruff", "check", ".")


@nox.session()
def typing(session):
    session.run("mypy", ".", "--enable-incomplete-feature=NewGenericSyntax", "--junit-xml", "mypy_report.xml")
