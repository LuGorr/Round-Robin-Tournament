# CDMO
##
First, setup AMPL_LICENSE_UUID environment variable (for example in a local .env file) and then run source .env (to enter the local environment).

## Using Docker
First, execute
```sh
 docker build -t cdmo_chagoko .
```
to assemble the image for the project.

Then run
```sh
docker run --mount src="${pwd}"/res,target=/app/res,type=bind cdmo_chagoko
```
to start the Docker container with the mounted directories and run all models for predefined n (from 4 to 14 for CP and MIP, 4 to 12 for SMT) using all defined solvers.

## CP
List of all solvers: gecode, chuffed, coinbc, ortools.

List of all models:
* basic_solution – Basic domain constraints
* symmetry_breaks – Symmetry breaking, channelling constraints
* warm_start - Symmetry breaking, chanelling constraints, starts with a zero-initialized array
* optimization –Symmetry breaking, channelling constraints + minimizing the objective function

To run Docker container with the exact model and number of teams:
```sh
docker run --mount src="${pwd}"/res,target=/app/res,type=bind cdmo_chagoko CP/basic_solution.sh -n <your_n> -s CP/solver-configs/1-solve-<your_solver>.mpc
```

## SMT
List of all models:
* SMT_trivial – Basic domain constraints
* SMT – Trivial + symmetry breaking constraints
* SMT_tactic – Symmetry Breaking + using Tactics and Goal()
* SMT_optimize - Symmetry Breaking + minimizing the objective function

To run Docker container with the exact model and number of teams:
```sh
docker run --mount src="${pwd}"/res,target=/app/res,type=bind cdmo_chagoko python SMT/<your_model>.py <your_n>
```

## MIP
List of all solvers: cbc, cplex, gurobi, highs.

MIP models focus on different combinations of the following:
* Constraint on Deficient (1): Constraining the Deficient set of each period, defines one of team's appearing exactly once for each period
* Constraint on AscendingWeek1(2): Setting the teams appearing in the first week in ascending order throughout the periods
* Initialization of values for decision variables (3) : all x set to 0
* Constraint on Lexicographic order (4) of teams appearing home ascending throughout all the weeks, same for away

Decision approach models:
* dec_final_model: Best decision model, without (1), (2) and lexicographic order (4) implemented only on n/2 first weeks
* dec_lexAwayDiscending: without (1),(2), with (3) + (4) is descending for away
* dec_with_deficient_without_ascendingWeek1: with (1), without (2)
* dec_withDef_withWeek1: with (1), (2), (3) , (4)
* dec_final_without_initial_values: without (1), (2), (3) with (4)
* dec_trivial: Basic domain constraints

Optimization approach models:
* opt_withoutDef_withoutAscWeek1: without (1), (2), with (3), (4)
* opt_withoutDef_withAscWeek1:  without (1) with (2), (3), (4)
* opt_withDef_withoutAscWeek1:  without (2), with (1), (3), (4)
* opt_withDef_withAscWeek1:  with (1), (2), (3), (4)
* opt_without_without_initalHA: without (1), (2), with (3) + initializing the home and away variables, (4)
* opt_noInitialvalues: without (1), (2), (3), with (4)
* opt_noBound: without (1), (2), (3) with (4), and no lower bound for the objective function
* opt_trivial: Basic domain constraints

To run Docker container with the exact solver, model and number of teams:
```sh
docker run --mount src="${pwd}"/res,target=/app/res,type=bind cdmo_chagoko python MIP/MIP.py -n=<your_n> --model=<your_model> --solver=<your_solver>
```

Overleaf:
https://www.overleaf.com/1157611544qpkdbptwmvwn#d0f6c6
