#!/bin/bash

directory=$(pwd)

for n in 6 8 10 12; do
    echo 'Starting n=' $n ' teams'
    python "$directory/SMT/SMT_tactic.py" $n > "$directory/res/SMT/$n.json"
    echo 'Finished n=' $n ' teams'
done