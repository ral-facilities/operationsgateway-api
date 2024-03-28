# GitHub Actions

For our CI, we use GitHub Actions. There are multiple jobs which run the tests in multiple versions of Python (running an ingestion script beforehand to load data for the tests) and perform code formatting/linting on the codebase etc. The steps are fairly self-explanatory, but there are a few things worth noting that may not be immediately obvious.

## Ubuntu 20.04 & 22.04
The Python tests are across a variety of Python versions, some using Ubuntu 20.04 runners and others using Ubuntu 22.04. This is because the build dependencies for python-ldap (installed using `apt-get`) are specific to Python versions and the newer versions aren't available in Ubuntu 20.04. The solution to this is running tests across all desired Python versions and across both OSs, but disabling one of the operating systems from running on each version of Python. 22.04 is disabled on 3.8 & 3.9, 20.04 is disabled on 3.10 & 3.11.

## Extra Steps to Install mongoimport on 22.04 Runners
A consequence of using Ubuntu 22.04 is the loss of command line tools from MongoDB from the runners' default environment. This is important as our scripts for ingesting test data into the API use `mongoimport` to import data stored in JSON files. To workaround this, the CI contains a step that runs on 22.04 which executes a series of `apt` commands to install these tools. The [pull request](https://github.com/ral-facilities/operationsgateway-api/pull/97) that made these changes provide a couple of references to discussions on other GitHub repos.

## Minio as S3 Storage
The CI used to use Echo to store data for the tests. However, this was determined to be too slow, with the ingestion script taking multiple hours to complete, sometimes completing unsuccessfully. It appeared that some kind of rate limiting from GitHub Actions was taking place - when interacting with Echo, idling of ~60 seconds at a time would frequently occur.

To combat this issue, the CI now sets up a local instance of `minio` using a Docker container which the API connects to when it's launched in the ingestion script. Minio is a way of having S3 storage locally, mimicking AWS (and therefore Echo S3).
