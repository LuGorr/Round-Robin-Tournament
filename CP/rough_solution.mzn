int: n;  % Number of teams (even)
int: weeks = n - 1;
int: periods = n div 2;

%Each match slot holds two teams: home and away
array[1..weeks, 1..periods] of var 1..n: home_team;
array[1..weeks, 1..periods] of var 1..n: away_team;

%Each team plays with every other team once
%Count each unordered pair (i, j) where i != j
constraint forall(i in 1..n, j in i+1..n) (
    let {
        var int: total_matches = sum(w in 1..weeks, p in 1..periods)(
            (home_team[w, p] == i /\ away_team[w, p] == j) \/
            (home_team[w, p] == j /\ away_team[w, p] == i)
        )
    } in
        total_matches == 1
);

%Every team plays once per week
constraint forall(w in 1..weeks, t in 1..n)(
    sum(p in 1..periods)(
        (home_team[w, p] == t) + (away_team[w, p] == t)
    ) == 1
);

%No team appears more than 2 times in the same period across all weeks ---
constraint forall(p in 1..periods, t in 1..n)(
    sum(w in 1..weeks)(
        (home_team[w, p] == t) + (away_team[w, p] == t)
    ) <= 2
);

%No self matches
constraint forall(w in 1..weeks, p in 1..periods)(
    home_team[w, p] != away_team[w, p]
);

%Symmetry breaking (optional, helps solver)
constraint home_team[1,1] < away_team[1,1];

solve satisfy;


