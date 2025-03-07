import nox

nox.options.sessions = "black", "lint", "safety", "tests"
code_locations = "operationsgateway_api", "test", "noxfile.py", "util"


@nox.session(reuse_venv=True)
def black(session):
    # Use Poetry’s existing virtual environment
    session.env["POETRY_VIRTUALENVS_CREATE"] = "false"
    # The dependencies should already be installed,
    # but explicitly setting in case they're not
    session.run("poetry", "install", "--without", "simulated-data", external=True)
    args = session.posargs
    session.run("poetry", "run", "black", *code_locations, *args, external=True)


@nox.session(python=False)
def lint(session):
    args = session.posargs or code_locations
    session.env["POETRY_VIRTUALENVS_CREATE"] = "false"
    session.run("poetry", "install", "--without", "simulated-data", external=True)
    session.run("poetry", "run", "flake8", *args, external=True)


@nox.session(reuse_venv=True)
def safety(session):
    session.env["POETRY_VIRTUALENVS_CREATE"] = "false"
    session.run("poetry", "install", "--without", "simulated-data", external=True)
    # Can't fix 70790 because epac data sim uses it
    session.run(
        "poetry",
        "run",
        "safety",
        "check",
        "--full-report",
        "--ignore",
        "70790",
        external=True,
    )


@nox.session(python=False)
def tests(session):
    args = session.posargs
    session.env["POETRY_VIRTUALENVS_CREATE"] = "false"
    session.run("poetry", "install", "--without", "simulated-data", external=True)
    session.run("poetry", "run", "pytest", *args, external=True)
