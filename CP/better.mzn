include "globals.mzn";

%Parameters & variables
int: n;
int: weeks = n - 1;
int: periods = n div 2;
array[1..weeks, 1..periods, 1..2] of var 1..n: schedule;
array[1..weeks, 1..periods] of var 1..n: home_team;
array[1..weeks, 1..periods] of var 1..n: away_team;
array[1..n, 1..n] of var 0..((n*(n-1))div 2): matches;
array[1..weeks, 1..periods] of var 1..((n*(n-1))div 2): match_pair;

%Structural constraints
constraint forall(t in 1..n, w in 1..weeks)(
    count([schedule[w, p,1] | p in 1..periods] ++ [schedule[w,p,2] | p in 1..periods], t) == 1
)::domain_propagation;

constraint forall(t1 in 1..n, t2 in 1..n where t1 < t2)(
    sum(w in 1..weeks, p in 1..periods)(
        bool2int(schedule[w,p,1] == t1 /\ schedule[w,p,2] == t2)
    ) == 1
)::domain_propagation;

constraint forall(t in 1..n, p in 1..periods)(
    sum(w in 1..weeks)(
        bool2int(schedule[w,p,1] == t \/ schedule[w,p,2] == t)
    ) <= 2
)::domain_propagation;

constraint alldifferent([match_pair[w, p] | w in 1..weeks, p in 1..periods])::domain_propagation;

%Channelling constraints
constraint
  forall(w in 1..weeks, p in 1..periods) (
  let{
      var int: j = max(home_team[w, p], away_team[w, p]);
      var int: i = min(home_team[w, p], away_team[w, p]);
    } in
        match_pair[w, p] == matches[i,j]
  );

constraint forall(w in 1..weeks, p in 1..periods)(
    home_team[w,p] = schedule[w,p,1] /\
    away_team[w,p] = schedule[w,p,2]
);

constraint forall(i in 1..n, j in 1..n) (  
  (i>=j -> matches[i, j]==0) /\ ((j==2 /\ i == 1) -> matches[i,j]==1) /\ ((j>i /\ j > 1)-> matches[i,j]>matches[i,j-1])
  /\ ((i>1 /\ j==i+1) -> matches[i, j ]>matches[i-1, n])
)::defines_var(matches);


%Symmetry breaking constraints
constraint symmetry_breaking_constraint(increasing([home_team[1,p] | p in 1..periods]))::domain_propagation;

constraint symmetry_breaking_constraint(forall(w in 1..weeks, p in 1..periods)(
    schedule[w,p,1] < schedule[w,p,2]
))::domain_propagation;

constraint symmetry_breaking_constraint(schedule[1,1,1] == 1)::domain_propagation;

constraint symmetry_breaking_constraint(schedule[1,1,2] == 2)::domain_propagation;

constraint symmetry_breaking_constraint(home_team[1,1] == 1)::domain_propagation;

constraint symmetry_breaking_constraint(away_team[1,1] == 2)::domain_propagation;

constraint symmetry_breaking_constraint(increasing([schedule[1,p,1] | p in 1..periods]
))::domain_propagation;

constraint symmetry_breaking_constraint(lex_chain_less(home_team))::domain_propagation;

constraint symmetry_breaking_constraint(lex_chain_less(away_team))::domain_propagation;

%Redundant constraints
constraint implied_constraint(forall(w in 1..weeks, t in 1..n)(
    sum(p in 1..periods)(
        (home_team[w, p] == t) + (away_team[w, p] == t)
    ) == 1)
)::domain_propagation;

constraint implied_constraint(forall(p in 1..periods, t in 1..n)(
    sum(w in 1..weeks)(
        (home_team[w, p] == t) + (away_team[w, p] == t)
    ) <= 2)
)::domain_propagation;

%Search
solve :: int_search([schedule[w,p,s] | w in 1..weeks, p in 1..periods, s in 1..2],
               first_fail, indomain_min, complete)
satisfy;


output [showJSON([home_team, away_team])];
