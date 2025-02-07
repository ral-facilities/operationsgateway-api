# GitHub Actions

For our CI, we use GitHub Actions. The workflow runs the ingestion script beforehand to load data for the tests, and perform code formatting/linting on the codebase etc. The steps are fairly self-explanatory, but there are a few things worth noting that may not be immediately obvious.

## Extra Steps to Install mongoimport on 22.04 Runners
A consequence of using Ubuntu 22.04 is the loss of command line tools from MongoDB from the runners' default environment. This is important as our scripts for ingesting test data into the API use `mongoimport` to import data stored in JSON files. To workaround this, the CI contains a step that runs on 22.04 which executes a series of `apt` commands to install these tools. The [pull request](https://github.com/ral-facilities/operationsgateway-api/pull/97) that made these changes provide a couple of references to discussions on other GitHub repos.

## Minio as S3 Storage
The CI used to use Echo to store data for the tests. However, this was determined to be too slow, with the ingestion script taking multiple hours to complete, sometimes completing unsuccessfully. It appeared that some kind of rate limiting from GitHub Actions was taking place - when interacting with Echo, idling of ~60 seconds at a time would frequently occur.

To combat this issue, the CI now sets up a local instance of `minio` using a Docker container which the API connects to when it's launched in the ingestion script. Minio is a way of having S3 storage locally, mimicking AWS (and therefore Echo S3).

## Caching
To speed up the workflows, caching is used to store Python dependencies and load them into the virtual environments. This is done for both Pip and poetry - loading the `pip` cache helps speed up the installation of Poetry and Nox and the `poetry` cache helps with the project dependencies. The caching is done in a fairly standard way, but the cache key includes something that keys from other repos might not include, `env.pythonLocation`.