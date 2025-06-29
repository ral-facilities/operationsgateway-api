[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Build Status](https://github.com/ral-facilities/operationsgateway-api/workflows/CI/badge.svg?branch=main)](https://github.com/ral-facilities/operationsgateway-api/actions?query=workflow%3A%22CI%22)
[![Codecov](https://codecov.io/gh/ral-facilities/operationsgateway-api/branch/main/graph/badge.svg)](https://codecov.io/gh/ral-facilities/operationsgateway-api)


# OperationsGateway API
This API is built using [FastAPI](https://fastapi.tiangolo.com/) to work with [MongoDB](https://www.mongodb.com/) and ECHO S3. It allows CRUD access to the data stored as part of the OperationsGateway project for the EPAC facility.

A separate [repository](https://github.com/ral-facilities/operationsgateway-ansible) exists to manage the deployment on pre-production and production machines using the Ansible framework.

The following instructions will detail how to get a development instance up and running. They can run on a command line and are tailored for a new `rocky-9-nogui` virtual machine with SSH access.

## Prerequisites

1) Local development on Windows or Mac can be challenging because they lack the Linux libraries required by the API. Since the API is designed to run in a Python 3.11 environment on a Rocky 9 Linux machine, it’s best to use a Rocky 9 development VM to closely mirror the production setup.
2) You'll need a developer bucket in echo to use the test script to prefill echo, and a local database, with data.
3) One of the dependencies used in this API [(`epac-data-sim`)](https://github.com/CentralLaserFacility/EPAC-DataSim) is a private repository, so the appropriate permissions and SSH keys need to be set up. Guidance for setting up SSH keys for the Rocky 9 VM can be found [here](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent?platform=linux).


## Environment Setup

### Python

On the Rocky 9 machine, install development tools for Python:

```bash
sudo dnf install "@Development Tools" python3.11 python3.11-pip python3.11-setuptools python3.11-devel openldap-devel git
```

Clone the codebase

```bash
git clone https://github.com/ral-facilities/operationsgateway-api.git
```

### Poetry

[Poetry](https://python-poetry.org/) is used to manage the dependencies of this API.

```bash
# Install poetry
curl -sSL https://install.python-poetry.org | python3 -
# Change the directory to where the poetry .toml file is
cd operationsgateway-api
# Set poetry to use python 3.11
poetry env use python3.11
# Install the dependencies
poetry install
# If you don't need the simulated data, or don't have access to the epac repo...
poetry install --without simulated-data
```

### MongoDB:

Create the following file:

```bash
sudo vi /etc/yum.repos.d/mongodb-org-7.0.repo
```

Add:

```bash
[mongodb-org-7.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/9/mongodb-org/7.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://pgp.mongodb.com/server-7.0.asc
```

Then:

```bash
# Install MongoDB
sudo yum install mongodb-org
# Start it
sudo systemctl start mongod
# Enable it to start on boot
sudo systemctl enable mongod
```
### MongoDB Indexes:
The following Indexes are uses and need to be set up on local, dev & prod databases.

Using [mongosh](https://www.mongodb.com/docs/manual/reference/method/db.collection.createIndex/), select the database: `use opsgateway`

Then run the following command:

```
# Multiple users can have the same session name, but a user can't have two sessions with the same name.
db.sessions.createIndex(
  { username: 1, name: 1 },
  { unique: true }
);
```
## Authentication

The authentication system uses JSON Web Tokens (JWTs), which require a private and public key pair to encrypt and decrypt the tokens.

The keys can be generated by navigating to a directory and typing the command:

```bash
# When prompted for the location path, enter `id_rsa` to create the keys in the current directory rather than in your home directory.
# Press enter twice when prompted for the password so as not to set one.
ssh-keygen -b 2048 -t rsa
```

Then, edit the ```private_key_path``` and ```public_key_path``` settings in the ```auth``` section of the ```config.yml``` file to reflect the location where these keys have been created.

## API Configuration

In `operationsgateway_api/`, there are several example configuration files which need to be reviewed and renamed, removing the `.example` part of the filename.

- `config.yml.example`
- `logging.ini.example`
- `maintenance.json.example`
- `scheduled_maintenance.json.example`

## Test Data

A script has been created to set up the API with some test data and test users. This script also comes with a configuration file that needs to be reviewed and renamed at `util/realistic_data/config.yml.example`.

Once the appropriate configuration has been entered, run the script using Poetry:

```bash
poetry run python util/realistic_data/ingest_echo_data.py
```

More details about this script can be found in `docs/developer/test_data.md`

## Starting the API

```bash
poetry run python operationsgateway_api/src/main.py
```

Assuming the default configuration, the API will exist on 127.0.0.1:8000.

The port forwarding service on most IDEs will allow you to access the API on the remote VM through your local web browser. Then, you can visit `/docs` in a browser, which will give an OpenAPI interface detailing each of the endpoints.

Alternatively, you can use the Postman requests in this repo. This gives a more user-friendly way of interacting with the API. Certain environments and scripts have been set up in Postman to help with using the API. For example, before any call is made to the API, the `/login` call can be used to get and store a JWT, which will be used automatically in the `auth` header of following calls to the API.

## Testing

Like the [DataGateway API](https://github.com/ral-facilities/datagateway-api), this repository contains a [Nox](https://nox.thea.codes) file (`noxfile.py`), which exists at the root level of this repository.

To install Nox, use the following command:

```bash
python3.11 -m pip install --user --upgrade nox
```

To run a specific Nox session, use the following:

```bash
nox -s [SESSION NAME]
```

The following Nox sessions have been created:

- `black` - This uses Black to format Python code in a pre-defined style.
- `lint` - This uses [flake8](https://flake8.pycqa.org/en/latest/) with a number of additional plugins to lint the code to keep it Pythonic.
- `safety` - This uses [safety](https://github.com/pyupio/safety) to check the dependencies (pulled directly from Poetry) for any known vulnerabilities.
- `tests` - this uses [pytest](https://docs.pytest.org/en/stable/) to execute the automated tests in `test/`.

