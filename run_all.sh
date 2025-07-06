instance_dims=(4 6 8 10 12 14)
solvers=("gecode" "chuffed" "coinbc" "ortools")
for n in "${instance_dims[@]}"; do
    for solver in "${solvers[@]}"; do
        echo "./basic_solution.sh -n $n -s "solver-configs/1-solve-"$solver".mpc""
        echo "$(./basic_solution.sh -n $n -s "solver-configs/1-solve-"$solver".mpc" | grep -v "WARNING:")"
        echo "./symmetry_breaks.sh -n $n -s "solver-configs/1-solve-"$solver".mpc""
        echo "$(./symmetry_breaks.sh -n $n -s "solver-configs/1-solve-"$solver".mpc" | grep -v "WARNING:")"
        echo "./warm_start.sh -n $n -s "solver-configs/1-solve-"$solver".mpc""
        echo "$(./warm_start.sh -n $n -s "solver-configs/1-solve-"$solver".mpc" | grep -v "WARNING:")"
        echo "./optimization.sh -n $n -s "solver-configs/1-solve-"$solver".mpc""
        echo "$(./optimization.sh -n $n -s "solver-configs/1-solve-"$solver".mpc" | grep -v "WARNING:")"
    done
done