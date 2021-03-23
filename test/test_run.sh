#!/usr/bin/env bash

# Script to run Shyft as a test user

CONFIG="test/test_data/dash_config.ini"
DATA_DIR="/home/alan/bin/PycharmProjects/shyft/test/test_data/run/dash/"

# Make a custom configuration file for this run based on the standard test configuration
if [ ! -f "$CONFIG" ]; then
  echo "test_run: Creating test configuration."
  pipenv run python shyft/run.py --debug -c test/test_data/test_config.ini mkconfig \
    --data_dir "$DATA_DIR" "$CONFIG" || exit 1

  # Copy user docs over to directory from which they will be served
  # TODO: Consider where these will actually reside in production
  echo "test_run: Copying user docs to test data directory."
  cp -r user_docs/ "$DATA_DIR"

fi

echo "test_run: Running Shyft."
pipenv run python shyft/run.py --debug -c "$CONFIG" run


