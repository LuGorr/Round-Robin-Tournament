int: n;  % Number of teams (even)
int: weeks = n - 1;
int: periods = n div 2;

%Each match slot holds two teams: home and away
array[1..periods, 1..weeks] of var 1..n: home_team;
array[1..periods, 1..weeks] of var 1..n: away_team;
array[1..periods, 1..weeks] of array[1..2] of var 1..n: out;

constraint forall(w in 1..weeks, p in 1..periods)(
    out[p, w] = [home_team[p, w], away_team[p, w]]
);
%Each team plays with every other team once
%Count each unordered pair (i, j) where i != j
constraint forall(i in 1..n, j in i+1..n) (
    let {
        var int: total_matches = sum(w in 1..weeks, p in 1..periods)(
            (home_team[p, w] == i /\ away_team[p, w] == j) \/
            (home_team[p, w] == j /\ away_team[p, w] == i)
        )
    } in
        total_matches == 1
);

%Every team plays once per week
constraint forall(w in 1..weeks, t in 1..n)(
    sum(p in 1..periods)(
        (home_team[p, w] == t) + (away_team[p, w] == t)
    ) == 1
);

%No team appears more than 2 times in the same period across all weeks ---
constraint forall(p in 1..periods, t in 1..n)(
    sum(w in 1..weeks)(
        (home_team[p, w] == t) + (away_team[p, w] == t)
    ) <= 2
);

%No self matches
constraint forall(w in 1..weeks, p in 1..periods)(
    home_team[p, w] != away_team[p, w]
);

%Symmetry breaking (optional, helps solver)
constraint home_team[1,1] < away_team[1,1];

solve ::int_search([home_team[p, w] | w in 1..weeks, p in 1..periods] ++ [away_team[p, w] | w in 1..weeks, p in 1..periods],
        first_fail, indomain_split, complete)::restart_luby(100) satisfy;
output [showJSON([out])];

