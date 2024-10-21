# Base Stage: Shared base for both prod / dev and testing
FROM python:3.9-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Install system dependencies needed for Poetry, and general development
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libssl-dev \
    libldap2-dev \
    libsasl2-dev \
    gcc \
    libffi-dev \
    openssh-client \
    && apt-get clean

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to the PATH
ENV PATH="/root/.local/bin:$PATH"

# Set the working directory in the container
WORKDIR /app

# Copy the pyproject.toml and poetry.lock files to the container
COPY pyproject.toml poetry.lock* /app/

# Generate SSH key pair and place them in the /app folder
RUN ssh-keygen -t rsa -b 4096 -f /app/id_rsa -N "" && \
    chmod 600 /app/id_rsa && \
    chmod 644 /app/id_rsa.pub

# Production Stage: Uses the base and installs production dependencies
FROM base AS prod

# Install only production dependencies
RUN poetry config virtualenvs.create false && poetry install --no-dev --no-interaction --no-ansi

# Copy the rest of the api code to the container
COPY ./operationsgateway_api /app/operationsgateway_api

# Expose the port that FastAPI will run on
EXPOSE 8000

# Command for running the FastAPI app without Poetry
CMD ["uvicorn", "operationsgateway_api.src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Test Stage: Uses the base stage to add nox and testing dependencies
FROM base AS test

# Install Nox for running tests
RUN pip install nox

# Forward SSH key during the build to allow access to private repos
# Ensure that SSH keys are properly set up on your machine
RUN mkdir -p /root/.ssh && chmod 0700 /root/.ssh

# Add the known hosts to avoid SSH prompt
RUN ssh-keyscan github.com >> /root/.ssh/known_hosts

# Install development and testing dependencies
RUN --mount=type=ssh poetry install --no-interaction --no-ansi

# Copy the rest of the application code to the container
COPY . /app

# Run the tests with Nox
CMD ["poetry", "run", "nox", "-s", "tests"]
