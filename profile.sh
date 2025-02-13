#!/bin/bash

# Adjust as needed
MEMORY_LIMIT_KB=$((1000 * 1024))
(
    ulimit -v "$MEMORY_LIMIT_KB"
    export IOTRANS_TEST_PROFILE=1
    pytest -k test_profile_spatial_files -s --pdb
)

# Exit with the status of the subshell
exit $?
