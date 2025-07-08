#!/bin/bash

directory=$(pwd)

for n in 4 6 8 10 12; do
    echo 'Starting for n=' $n ' teams'
    python "$directory/SMT/SMT_trivial.py" $n > "$directory/res/SMT/trivial_$n.json"
    python "$directory/SMT/SMT.py" $n > "$directory/res/SMT/$n.json"
    python "$directory/SMT/SMT_tactic.py" $n > "$directory/res/SMT/tactic_$n.json"
    python "$directory/SMT/SMT_optimize.py" $n > "$directory/res/SMT/optimize_$n.json"
    echo 'Finished for n=' $n ' teams'
done