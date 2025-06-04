include "alldifferent.mzn";
int: n = 10;  % Number of teams (even)
int: weeks = n - 1;
int: periods = n div 2;

%Each match slot holds two teams: home and away
array[1..weeks, 1..periods] of var 1..n: home_team;
array[1..weeks, 1..periods] of var 1..n: away_team;

%Upper triangular (diagonal set to 0) matrix containing match id
array[1..n, 1..n] of var 0..((n*(n-1))div 2): matches;

%Assignements fot matches matrix (set to 0 lower part, incremental values for the upper section)
constraint forall(i in 1..n, j in 1..n) (  
  (i>=j -> matches[i, j]==0) /\ ((j==2 /\ i == 1) -> matches[i,j]==1) /\ ((j>i /\ j > 1)-> matches[i,j]>matches[i,j-1])
  /\ ((i>1 /\ j==i+1) -> matches[i, j]>matches[i-1, n])
);

%Schedule expressed in match ids (channeling constraint between matches, match_pair and the schedule matrixes
array[1..weeks, 1..periods] of var 1..(n*n): match_pair;
constraint
  forall(w in 1..weeks, p in 1..periods) (
  let{
      var int: j = max(home_team[w, p], away_team[w, p]);
      var int: i = min(home_team[w, p], away_team[w, p]);
    } in
        match_pair[w, p] == matches[i,j]
  );

%In a single global constraint we specify that each team must play at least once against every other team and we remove same team matchups (i.e. 1 vs 1)
constraint alldifferent([match_pair[w, p] | w in 1..weeks, p in 1..periods]);

%Remove some team label permutations by fixing the first scheduled match
constraint home_team[1,1] == 1;
constraint away_team[1,1] == 5;

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


solve :: int_search(
    [home_team[w,p] | w in 1..weeks, p in 1..periods] ++
    [away_team[w,p] | w in 1..weeks, p in 1..periods],
    dom_w_deg,
    indomain_min
        ) :: restart_linear(1) satisfy;%Output in json format

%Output in json format
output [showJSON([home_team, away_team])];
