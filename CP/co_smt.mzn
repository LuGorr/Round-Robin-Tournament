include "alldifferent.mzn";
include "increasing.mzn";
include "lex_greater.mzn";
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
  /\ ((i>1 /\ j==i+1) -> matches[i, j ]>matches[i-1, n])
);

/*
Home teams must be in ascending order across periods. E.g.:
If periods are [(0,1), (2,3), (4,5)], home teams are ordered: 0 < 2 < 4.
Eliminates period reordering symmetry within first week.
*/
constraint increasing([home_team[1,p] | p in 1..periods]);

/*
Team 0 appears in period 0 more often than other periods.
Eliminates symmetry between periods by establishing preference order.
*/
var int: count_p0 = sum(w in 1..weeks)(bool2int(home_team[w,1]==0));
var int: count_p = sum(w in 1..weeks, p in 2..periods)(bool2int(home_team[w,p]==0));
constraint count_p0 >= count_p;

/*
Lexicographic ordering on weeks:
Week w ≤ Week w+1 when viewed as sequences.
Eliminates week reordering symmetry.

IM DOING SOMETHING WRONG; IT GIVES UNSAT AAAAAAAAAH

constraint forall(w in 1..weeks-1) (
    lex_greater([home_team[w, p] | p in 1..periods], [home_team[w+1, p] | p in 1..periods])
);

constraint forall(w in 1..weeks-1) (
    lex_greater([away_team[w, p] | p in 1..periods], [away_team[w+1, p] | p in 1..periods])
);
*/

/*
Break symmetry between equivalent teams
Teams 1 and 2 ordering in their first appearance
Prefer team 1 as home when playing against team 2.
Eliminates home/away symmetry for team pairs.
*/
constraint forall(w in 1..weeks, p in 1..periods) (
    (home_team[w, p] == 1 /\ away_team[w, p] == 2) -> 
    (home_team[w, p] < away_team[w, p])
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
output [showJSON([home_team, away_team])];
