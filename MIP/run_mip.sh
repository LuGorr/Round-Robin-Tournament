#!/bin/bash

directory=$(pwd)

echo 'Starting running all MIP models'
python "$directory/MIP/MIP.py" --all
echo 'Finished running all MIP models'