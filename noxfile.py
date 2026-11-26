import nox

nox.options.sessions = "black", "lint", "safety", "tests"
code_locations = "operationsgateway_api", "test", "noxfile.py", "util"


@nox.session(python=False)
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


@nox.session(python=False)
def safety(session):
    session.run("poetry", "sync", "--without", "simulated-data", external=True)
    session.run(
        "poetry",
        "run",
        "python",
        "-m",
        "pip",
        "install",
        "--upgrade",
        "pip>=26.2.2",
        external=True,
    )

    # Can't fix 70790 because epac data sim uses it
    # SFTY-20260902-58666 is in nltk, a transitive dependency of safety itself.
    ignored = ["70790", "SFTY-20260902-58666"]

    # Safety itself requires filelock >=3.16.1,<4.0, and all of these advisories are
    # only fixed in filelock 4.3.0, so they cannot be cleared while safety is
    # installed. filelock is a dev dependency, so it is never deployed
    ignored += [
        "SFTY-20261017-54654",
        "SFTY-20261017-57659",
        "SFTY-20261017-72390",
        "SFTY-20261020-11422",
        "SFTY-20261020-13394",
        "SFTY-20261020-18367",
        "SFTY-20261020-25530",
        "SFTY-20261020-34461",
        "SFTY-20261020-81101",
        "SFTY-20261020-91319",
        "SFTY-20261023-16869",
        "SFTY-20261023-24590",
        "SFTY-20261023-10299",
    ]

    ignore_args = [arg for id_ in ignored for arg in ("--ignore", id_)]
    session.run(
        "poetry",
        "run",
        "safety",
        "check",
        "--full-report",
        *ignore_args,
        external=True,
    )


@nox.session(python=False)
def tests(session):
    args = session.posargs
    session.env["POETRY_VIRTUALENVS_CREATE"] = "false"
    session.run("poetry", "install", "--without", "simulated-data", external=True)
    session.run("poetry", "run", "pytest", *args, external=True)


@nox.session(python=False)
def tests_epac(session):
    args = session.posargs
    session.env["POETRY_VIRTUALENVS_CREATE"] = "false"
    session.run("poetry", "install", "--without", "simulated-data", external=True)
    session.run(
        "poetry",
        "run",
        "pytest",
        "--config-file=test/pytest_epac.ini",
        *args,
        external=True,
    )


@nox.session(python=False)
def tests_gemini(session):
    args = session.posargs
    session.env["POETRY_VIRTUALENVS_CREATE"] = "false"
    session.run("poetry", "install", "--without", "simulated-data", external=True)
    session.run(
        "poetry",
        "run",
        "pytest",
        "--config-file=test/pytest_gemini.ini",
        *args,
        external=True,
    )
