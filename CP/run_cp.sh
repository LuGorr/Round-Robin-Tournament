#!/bin/bash

directory=$(pwd)/CP

instance_dims=(4 6 8 10 12 14)
solvers=("gecode" "chuffed" "coinbc" "ortools")
for n in "${instance_dims[@]}"; do
    for solver in "${solvers[@]}"; do
        echo "$directory/basic_solution.sh -n $n -s "$directory/solver-configs/1-solve-$solver.mpc""
        echo "$("$directory"/basic_solution.sh -n $n -s "$directory/solver-configs/1-solve-$solver.mpc" | grep -v "WARNING:")"
        echo "$directory/symmetry_breaks.sh -n $n -s "$directory/solver-configs/1-solve-$solver.mpc""
        echo "$("$directory"/symmetry_breaks.sh -n $n -s "$directory/solver-configs/1-solve-$solver.mpc" | grep -v "WARNING:")"
        echo "$directory/warm_start.sh -n $n -s "$directory/solver-configs/1-solve-$solver.mpc""
        echo "$("$directory"/warm_start.sh -n $n -s "$directory/solver-configs/1-solve-$solver.mpc" | grep -v "WARNING:")"
        echo "$directory/optimization.sh -n $n -s "$directory/solver-configs/1-solve-$solver.mpc""
        echo "$("$directory"/optimization.sh -n $n -s "$directory/solver-configs/1-solve-$solver.mpc" | grep -v "WARNING:")"
    done
done