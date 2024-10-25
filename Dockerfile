FROM python:3.9-slim as base

# Set any environment variables
ENV PYTHONUNBUFFERED=1

# Install system dependencies needed for Poetry, and general running
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libssl-dev \
    libldap2-dev \
    libsasl2-dev \
    gcc \
    lsof \
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

# Generate SSH key pair and place them in the /app folder because the api need them
RUN ssh-keygen -t rsa -b 4096 -f /app/id_rsa -N "" && \
    chmod 600 /app/id_rsa && \
    chmod 644 /app/id_rsa.pub

FROM base AS production

# Install only production dependencies
RUN poetry config virtualenvs.create false && poetry install --no-dev --no-interaction --no-ansi --without simulated-data

# Copy the rest of the api application code to the container
COPY ./operationsgateway_api /app/operationsgateway_api

# Expose the port that FastAPI will run on
EXPOSE 8000

# Command for running the FastAPI app (without Poetry)
CMD ["uvicorn", "operationsgateway_api.src.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS add_test_data

RUN  poetry install --no-interaction --no-ansi  --without simulated-data

COPY . /app

ENV PYTHONPATH=/app

CMD ["poetry", "run", "python", "util/realistic_data/ingest_echo_data.py"]

FROM base AS test

RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --without simulated-data

COPY . /app

CMD ["pytest", "--disable-warnings", "--maxfail=1", "-v"]
