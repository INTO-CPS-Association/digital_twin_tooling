# Digital Twin Tooling

This project aims to provide a structured approach to working with digital twins and support the analysis that one might want to carry out in this context.

The project provides a pipeline like approach for managing a combination of time series data flow and events.
The approach allows time series data to be processed and events to be generated. Events can then in turn be tied to new replications of pipelines.


# Build the project from source

from the repo root go do `backend/digital-twin-platform` and run the following commands:

* pipenv and python 3 is required

```bash
python3 -m venv venv
source ./venv/bin/activate
pip install -e .[dev,test]

# run tests
cd tests/digital_twin_tooling && 
  python -m unittest discover -v -s .

# build egg
python -m build

# upload release
twine upload dist/*
```

# Install the tool in an insulated environment

First select a new folder which does not have a virtual environment already.
The wheel package can be taken from the `dist` folder or from the artifact produced from the job on github.

```bash
mkdir /tmp/digital_twin_platform
cd /tmp/digital_twin_platform

# install whl
pipenv install dist/digital_twin_tooling-*-py3-none-any.whl

pipenv run python -m "digital_twin_tooling" --help

usage: digital_twin_platform [-h] -pipe PIPE [-project PROJECT] [-work WORK] [-reload RELOAD] [-show] [-pdf] [-e] [-t TIMEOUT]

optional arguments:
  -h, --help            show this help message and exit
  -pipe PIPE, --pipe-path PIPE
                        Path to a pipe .yml file
  -project PROJECT, --project-path PROJECT
                        Path to the project root containing the .env
  -work WORK, --working-path WORK
                        Optional path to a working directory
  -reload RELOAD, --reload-pipe RELOAD
                        If the pipeline should be reloaded instead of configured
  -show, --show         Show the pipeline
  -pdf, --visualize-as-pdf
                        View the pipeline in pdf format
  -e, --execute         Execute the pipeline
  -t TIMEOUT, --time-out TIMEOUT
                        Pipeline execution timeout

python -m "digital_twin_tooling" -pipe project_1_test/pipeline-standalone.yml -project project_1_test -show -e -t 5
```
