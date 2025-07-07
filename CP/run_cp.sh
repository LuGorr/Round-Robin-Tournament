#!/bin/bash

directory=$(pwd)

instance_dims=(4 6 8 10 12 14)
solvers=("gecode" "chuffed" "coinbc" "ortools")
for n in "${instance_dims[@]}"; do
    for solver in "${solvers[@]}"; do
        echo "$directory/CP/basic_solution.sh -n $n -s "$directory/solver-configs/1-solve-$solver.mpc""
        echo "$("$directory"/CP/basic_solution.sh -n $n -s "$directory/solver-configs/1-solve-$solver.mpc" | grep -v "WARNING:")"
        echo "$directory/CP/symmetry_breaks.sh -n $n -s "$directory/solver-configs/1-solve-$solver.mpc""
        echo "$("$directory"/CP/symmetry_breaks.sh -n $n -s "$directory/solver-configs/1-solve-$solver.mpc" | grep -v "WARNING:")"
        echo "$directory/CP/warm_start.sh -n $n -s "$directory/solver-configs/1-solve-$solver.mpc""
        echo "$("$directory"/CP/warm_start.sh -n $n -s "$directory/solver-configs/1-solve-$solver.mpc" | grep -v "WARNING:")"
        echo "$directory/CP/optimization.sh -n $n -s "$directory/solver-configs/1-solve-$solver.mpc""
        echo "$("$directory"/CP/optimization.sh -n $n -s "$directory/solver-configs/1-solve-$solver.mpc" | grep -v "WARNING:")"
    done
done