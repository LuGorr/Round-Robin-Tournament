include "globals.mzn";


int: n;
int: weeks = n - 1;
int: periods = n div 2;
array[1..weeks, 1..periods, 1..2] of var 1..n: schedule;
array[1..periods,1..weeks] of var 1..n: home_team;
array[1..periods,1..weeks] of var 1..n: away_team;
array[1..periods, 1..weeks] of array[1..2] of var 1..n: out;
array[1..n, 1..n] of var 0..((n*(n-1))div 2): matches::computed_domain;
array[1..weeks, 1..periods] of var 1..((n*(n-1))div 2): match_pair;

% Constraint 1
constraint forall(t in 1..n, w in 1..weeks)(
    count([schedule[w, p,1] | p in 1..periods] ++ 
    [schedule[w,p,2] | p in 1..periods], t) == 1
)::domain_propagation; 

% Constraint 3
constraint alldifferent([match_pair[w, p] | w in 1..weeks, p in 1..periods])::domain_propagation;

% Constraint 4
constraint forall(t in 1..n, p in 1..periods)(
    sum(w in 1..weeks)(
        bool2int(schedule[w,p,1] == t \/ schedule[w,p,2] == t)
    ) <= 2
)::domain_propagation;

% Constraint 5
constraint symmetry_breaking_constraint(
    forall(p in 1..periods)
        (sum(w in 2..weeks)
            (bool2int(schedule[w, p, 1] == p \/ schedule[w,p,2] == p))==1));

% Constraints 6
constraint symmetry_breaking_constraint(
    increasing([schedule[1,p,1] | p in 1..periods]))::domain_propagation;
constraint symmetry_breaking_constraint(
    decreasing([schedule[1,p,2] | p in 1..periods]))::domain_propagation;

% Constraint 7
constraint symmetry_breaking_constraint(schedule[1,1,1] == 1)::domain_propagation;

% Constraints 8
constraint symmetry_breaking_constraint(lex_chain_less(home_team))::domain_propagation;
constraint symmetry_breaking_constraint(lex_chain_greater(away_team))::domain_propagation;

% Constraint 9
constraint symmetry_breaking_constraint(sum(w in 1..weeks)
    (bool2int(schedule[w, 2, 1] == 1 \/ schedule[w,2,2] == 1))==1)::domain_propagation; 

% Channelling Constraints

% Constraint 10
constraint forall(i in 1..n, j in 1..n) (  
  (i>=j -> matches[i, j]==0) /\ ((j==2 /\ i == 1) -> matches[i,j]==1) /\ ((j>i /\ j > 1)-> matches[i,j]>matches[i,j-1])
  /\ ((i>1 /\ j==i+1) -> matches[i, j ]>matches[i-1, n])
)::defines_var(matches);

% Constraint 11
constraint
  forall(w in 1..weeks, p in 1..periods) (
  let{
      var int: j = max(schedule[w, p, 1], schedule[w, p, 2]);
      var int: i = min(schedule[w, p, 1], schedule[w, p, 2]);
    } in
        match_pair[w, p] == matches[i,j]
);

constraint forall(w in 1..weeks, p in 1..periods)(
    out[p, w] = [home_team[p, w], away_team[p, w]]
);

constraint forall(w in 1..weeks, p in 1..periods)(
    home_team[p,w] = schedule[w,p,1] /\
    away_team[p,w] = schedule[w,p,2]
);



solve ::int_search([schedule[w,p,s] | w in 1..weeks, p in 1..periods, s in 1..2],
        first_fail, indomain_split, complete)::restart_luby(100) satisfy;
output [showJSON([schedule[w,p,s] | w in 1..weeks, p in 1..periods, s in 1..2]), "$", showJSON([out])]
