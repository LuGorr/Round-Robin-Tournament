include "globals.mzn";
/*
change ordering of constraint appearence
implement optimization version
*/

int: n;
int: weeks = n - 1;
int: periods = n div 2;
bool: simplified_mode;
array[1..(2*(n-1)*(n div 2))] of int: warm_start;
array[1..2] of ann: search_ann = [
    int_search([schedule[w,p,s] | w in 1..weeks, p in 1..periods, s in 1..2], first_fail, indomain_min, complete)
        ::restart_luby(100)::warm_start([schedule[w,p,s] | w in 1..weeks, p in 1..periods, s in 1..2], warm_start)::relax_and_reconstruct([schedule[w,p,s] | w in 1..weeks, p in 1..periods, s in 1..2], 50),
    int_search([schedule[w,p,s] | w in 1..weeks, p in 1..periods, s in 1..2],
        first_fail, indomain_split, complete)::restart_luby(100)]; 
array[1..weeks, 1..periods, 1..2] of var 1..n: schedule;
array[1..periods,1..weeks] of var 1..n: home_team;
array[1..periods,1..weeks] of var 1..n: away_team;
array[1..periods, 1..weeks] of array[1..2] of var 1..n: out;

constraint forall(w in 1..weeks, p in 1..periods)(
    out[p, w] = [home_team[p, w], away_team[p, w]]
);



constraint forall(w in 1..weeks, p in 1..periods)(
    home_team[p,w] = schedule[w,p,1] /\
    away_team[p,w] = schedule[w,p,2]
);

constraint forall(t in 1..n, w in 1..weeks)(
    count([schedule[w, p,1] | p in 1..periods] ++ 
    [schedule[w,p,2] | p in 1..periods], t) == 1
)::domain_propagation; 

constraint if not simplified_mode then
 forall(t in 1..n, p in 1..periods)(
    sum(w in 1..weeks)(
        bool2int(schedule[w,p,1] == t \/ schedule[w,p,2] == t)
    ) <= 2
)::domain_propagation endif;
constraint symmetry_breaking_constraint(
    forall(p in 1..periods)
        (sum(w in 2..weeks)
            (bool2int(schedule[w, p, 1] == p \/ schedule[w,p,2] == p))==1));

constraint symmetry_breaking_constraint(
    increasing([schedule[1,p,1] | p in 1..periods]))::domain_propagation;
constraint symmetry_breaking_constraint(
    decreasing([schedule[1,p,2] | p in 1..periods]))::domain_propagation;
 

/* constraint symmetry_breaking_constraint(schedule[1,1,1] = 1)::domain_propagation;
constraint symmetry_breaking_constraint(forall(p in 2..periods)(
    schedule[1,p,1] = schedule[1,p-1,1]+2
))::domain_propagation; */

/* 
constraint symmetry_breaking_constraint(schedule[1,1,2] = 6)::domain_propagation;
constraint symmetry_breaking_constraint(forall(p in 2..periods)(
    schedule[1,p,2] = schedule[1,p-1,2]-2 
))::domain_propagation; */


array[1..n, 1..n] of var 0..((n*(n-1))div 2): matches::computed_domain;

constraint forall(i in 1..n, j in 1..n) (  
  (i>=j -> matches[i, j]==0) /\ ((j==2 /\ i == 1) -> matches[i,j]==1) /\ ((j>i /\ j > 1)-> matches[i,j]>matches[i,j-1])
  /\ ((i>1 /\ j==i+1) -> matches[i, j ]>matches[i-1, n])
)::defines_var(matches);




array[1..weeks, 1..periods] of var 1..((n*(n-1))div 2): match_pair;
constraint
  forall(w in 1..weeks, p in 1..periods) (
  let{
      var int: j = max(schedule[w, p, 1], schedule[w, p, 2]);
      var int: i = min(schedule[w, p, 1], schedule[w, p, 2]);
    } in
        match_pair[w, p] == matches[i,j]
  );

constraint symmetry_breaking_constraint(
    alldifferent([match_pair[w, p] | w in 1..weeks, p in 1..periods]))::domain_propagation;
constraint symmetry_breaking_constraint(home_team[1,1] == 1)::domain_propagation;
constraint symmetry_breaking_constraint(away_team[periods, weeks] == 2)::domain_propagation; 

%constraint symmetry_breaking_constraint(lex_chain_less(match_pair));

constraint symmetry_breaking_constraint(lex_chain_less(home_team))::domain_propagation;
constraint symmetry_breaking_constraint(lex_chain_greater(away_team))::domain_propagation;

constraint symmetry_breaking_constraint(sum(w in 1..weeks)
    (bool2int(schedule[w, 2, 1] == 1 \/ schedule[w,2,2] == 1))==1)::domain_propagation; 
/* constraint symmetry_breaking_constraint(sum(w in 1..weeks)
    (bool2int(schedule[w, 2, 1] == 3 \/ schedule[w,2,2] == 3))==1)::domain_propagation; */
solve ::search_ann[bool2int(simplified_mode) + 1] satisfy;

output [showJSON([schedule[w,p,s] | w in 1..weeks, p in 1..periods, s in 1..2]), "$", showJSON([out])];

%constraint if simplified_mode then symmetry_breaking_constraint(forall(w in 1..weeks, p in 1..periods)(
%    schedule[w,p,1] < schedule[w,p,2]
%)) endif::domain_propagation;
%constraint  if simplified_mode then
%forall(t1 in 1..n, t2 in 1..n where t1 < t2)
%    (sum(w in 1..weeks, p in 1..periods)
%        (bool2int((schedule[w,p,1] == t1 /\ schedule[w,p,2] == t2))) == 1)
%constraint forall(t1 in 1..n, t2 in 1..n where t1 != t2)
%    (sum(w in 1..weeks, p in 1..periods)
%        (bool2int((schedule[w,p,1] == t1 /\ schedule[w,p,2] == t2)) \/ bool2int((schedule[w,p,1] == t2 /\ schedule[w,p,2] == t1))) == 1)::domain_propagation;

%constraint forall(t1 in 1..n, t2 in 1..n where t1 != t2)
    %schedule[w,p,1] == t1 /\ schedule[w,p,2] == t2 -> sum(w1 in weeks, p1 in periods)(count(schedule[w1,p1,1] == t2 /\ schedule[w1,p1,2] == t1, true)) == 0;


/* constraint symmetry_breaking_constraint(sum(w in 1..weeks)
    (bool2int(schedule[w, 1, 1] == 2 \/ schedule[w,1,2] == 2))==1)::domain_propagation;
constraint symmetry_breaking_constraint(sum(w in 1..weeks)
    (bool2int(schedule[w, 1, 1] == 4 \/ schedule[w,1,2] == 4))==1)::domain_propagation; */




%constraint forall(i in 2..n)(count([match_pair[i-1,p] | p in 1..periods],matches[1,i])==1);



/* constraint symmetry_breaking_constraint(schedule[1,1,1] == 2)::domain_propagation;
constraint symmetry_breaking_constraint(schedule[1,1,2] == 3)::domain_propagation; */

/* constraint forall(w in 1..weeks) (
    exists(p in 1..periods) (
        (schedule[w,p,1] == 1 /\ team1_opponents[w] = schedule[w,p,2]) \/
        (schedule[w,p,2] == 1 /\ team1_opponents[w] = schedule[w,p,1])
    )
)::domain_propagation;
array[1..weeks] of var 2..n: team1_opponents;
constraint symmetry_breaking_constraint(increasing(team1_opponents)); */


