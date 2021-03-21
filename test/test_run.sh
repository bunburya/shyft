#!/usr/bin/env bash

# Script to run Shyft as a test user

CONFIG="test/test_data/dash_config.ini"

# Make a custom configuration file for this run based on the standard test configuration
if [ ! -f "$CONFIG" ]; then
  pipenv run python shyft/run.py --debug -c test/test_data/test_config.ini mkconfig \
    --data_dir test/test_data/run/dash "$CONFIG" || exit 1
fi

pipenv run python shyft/run.py --debug -c "$CONFIG" run


