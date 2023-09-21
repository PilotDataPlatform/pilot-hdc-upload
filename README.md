# Upload Service

[![Python](https://img.shields.io/badge/python-3.7-brightgreen.svg)](https://www.python.org/)

The upload service is one of the component for PILOT project. The main responsibility is to handle the file upload(especially large file). The main machanism for uploading is to chunk up the large file(>5MB). It has three main api for pre-uploading, uploading chunks and combining the chunks. After combining the chunks, the api will upload the file to [Minio](https://min.io/) as the Object Storage.

# Getting Started

This is an example of how to run the upload service locally.

### Prerequisites

This project is using [Poetry](https://python-poetry.org/docs/#installation) to handle the dependencies.

    curl -sSL https://install.python-poetry.org | python3 -

### Installation & Quick Start

1. Clone the project.

       git clone https://github.com/PilotDataPlatform/upload.git

2. Install dependencies.

       poetry install

3. Install any OS level dependencies if needed.

       apt install <required_package>
       brew install <required_package>

5. Add environment variables into `.env` in case it's needed. Use `.env.schema` as a reference.

6. Run application.

       poetry run python run.py

### Startup using Docker

This project can also be started using [Docker](https://www.docker.com/get-started/).

1. To build and start the service within the Docker container, run:

       docker compose up

## Contribution

You can contribute the project in following ways:

* Report a bug.
* Suggest a feature.
* Open a pull request for fixing issues or adding functionality. Please consider
  using [pre-commit](https://pre-commit.com) in this case.
* For general guidelines on how to contribute to the project, please take a look at the [contribution guides](CONTRIBUTING.md).

## Acknowledgements
The development of the HealthDataCloud open source software was supported by the EBRAINS research infrastructure, funded from the European Union's Horizon 2020 Framework Programme for Research and Innovation under the Specific Grant Agreement No. 945539 (Human Brain Project SGA3) and H2020 Research and Innovation Action Grant Interactive Computing E-Infrastructure for the Human Brain Project ICEI 800858.
