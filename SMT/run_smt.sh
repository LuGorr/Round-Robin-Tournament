#!/bin/bash

directory=$(pwd)

echo 'Starting running all SMT models'

for n in 4 6 8 10 12; do
    echo 'Starting for n=' $n ' teams'
    python "$directory/SMT/SMT_trivial.py" $n
    python "$directory/SMT/SMT.py" $n
    python "$directory/SMT/SMT_tactic.py" $n
    python "$directory/SMT/SMT_optimize.py" $n
    echo 'Finished for n=' $n ' teams'
done

echo 'Finished running all SMT models'