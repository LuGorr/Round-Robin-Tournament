
import pandas as pd
import numpy as np
from amplpy import AMPL, Environment,ampl_notebook, DataFrame
import matplotlib.pyplot as plt
import seaborn as sns
import time
import math
import json
ampl = ampl_notebook(modules=["highs", "cbc", "gurobi", "cplex"], license_uuid="license")


def solve_tournament(ampl, n_teams, solver='cplex', time_limit=300):

    ampl.option['solver'] = solver
    ampl.option[f'{solver}_options'] = (f'timelim={time_limit} threads=1')
    if solver=='cbc':
        ampl.option[f'{solver}_options'] = f'timelim={time_limit}'
    start_time = time.time()
    ampl.solve()
    solve_time = time.time() - start_time
    solve_result = ampl.get_value('solve_result')
    if solve_result == 'solved':
        return extract_solution(ampl,n_teams,solve_time)
    else:
        return None

def extract_solution(ampl, n_teams, solve_time):
    
    x = ampl.get_variable('x')
    y = ampl.get_variable('y')
    matches = []
    weeks = n_teams - 1
    periods = n_teams // 2

    for i in range(1, n_teams + 1):
        for j in range(1, n_teams + 1):
            if i != j:
                for m in range(1, n_teams * (n_teams - 1) // 2 + 1):
                    if x[i, j, m].value() > 0.5:  # Binary variable is 1
                        week = ((m - 1) % weeks) + 1
                        period = ((m - 1) // weeks) + 1
                        matches.append({
                            'Match': m,
                            'Week': week,
                            'Period': period,
                            'Home': i,
                            'Away': j
                        })
    df_matches = pd.DataFrame(matches).sort_values('Match')
    weekly_schedule = {}
    for week in range(1, weeks + 1):
        weekly_schedule[f'Week {week}'] = {}
        for period in range(1, periods + 1):
            match = df_matches[(df_matches['Week'] == week) & (df_matches['Period'] == period)]
            if not match.empty:
                home = match.iloc[0]['Home']
                away = match.iloc[0]['Away']
                weekly_schedule[f'Week {week}'][f'Period {period}'] = f"Team {home} vs Team {away}"
    return {'matches_df': df_matches,'weekly_schedule': weekly_schedule,'solve_time': solve_time,'n_teams': n_teams}
    

def reformat_solution(result_dict, model_name , solver):

    matches_df = result_dict['matches_df']
    solve_time = result_dict['solve_time']
    n_teams = result_dict['n_teams']
    time = math.floor(solve_time)
    
    if solve_time <= 300:
        optimal = True
    else:
        optimal = False
    
    # No objective function mentioned, so set to None
    obj = None
    
    # Convert matches_df to the required matrix format
    n_periods = n_teams // 2
    n_weeks = n_teams - 1
    
    # Initialize solution matrix
    sol = []
    
    for period in range(1, n_periods + 1):
        week_matches = []
        for week in range(1, n_weeks + 1):
            # Find the match for this week and period
            match_row = matches_df[(matches_df['Week'] == week) & (matches_df['Period'] == period)]
            if not match_row.empty:
                home_team = int(match_row['Home'].iloc[0])
                away_team = int(match_row['Away'].iloc[0])
                week_matches.append([home_team, away_team])
        sol.append(week_matches)
    
    return { model_name:{solver:{
        'time': time,
        'optimal': optimal,
        'obj': obj,
        'sol': sol}}}

def get_models(n_teams,solver):
    return {'dec_final_model':f"""
    param n := {n_teams}; 
    param weeks := n - 1;
    param periods := n div 2;
    param total_matches := n * (n - 1) div 2;
    set TEAMS := 1..n;
    set WEEKS := 1..weeks;
    set PERIODS := 1..periods;
    set MATCHES := 1..total_matches;
    param match_to_week{{m in MATCHES}} := ((m-1) mod weeks)+1;
    param match_to_period{{m in MATCHES}} := ((m-1) div weeks) + 1;
    param WEIGHT{{p in PERIODS}} := (card(PERIODS) + 1 - p) * n;
    var x{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}} binary;
    var y{{TEAMS, WEEKS, PERIODS}} binary;
    var h{{TEAMS,PERIODS,WEEKS}} binary; #aux
    var a{{TEAMS,PERIODS, WEEKS}} binary; #aux var
    minimize obj: 0;
    let {{i in TEAMS, j in TEAMS , m in MATCHES: i!=j}}x[i,j,m]:=0;
    subject to unique_pairings{{i in TEAMS, j in TEAMS: i < j}}:
        sum{{m in MATCHES}} (x[i,j,m] + x[j,i,m]) = 1;
    subject to match_structure{{m in MATCHES}}:
        sum{{i in TEAMS, j in TEAMS: i != j}} x[i,j,m] = 1;
    subject to link_x_y_home{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[i, match_to_week[m], match_to_period[m]]; 
    subject to link_x_h{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:   
        x[i,j,m] <= h[i,match_to_period[m], match_to_week[m]];
    subject to link_x_y_away{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[j,match_to_week[m],match_to_period[m]];
    subject to weekly_play{{i in TEAMS, w in WEEKS}}:
        sum{{p in PERIODS}} y[i,w,p] = 1;
    subject to link_x_a{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:
        x[i,j,m]<= a[j,match_to_period[m], match_to_week[m]];
    subject to period_capacity{{w in WEEKS, p in PERIODS}}:
        sum{{i in TEAMS}} y[i,w,p] = 2;
    subject to period_limits{{i in TEAMS, p in PERIODS}}:
        sum{{w in WEEKS}} y[i,w,p] <= 2;
    subject to fix_first_match:
        x[2,3,1] = 1;
    subject to lex_home_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * h[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * h[j,p,w+1];
    subject to lex_away_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * a[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * a[j,p,w+1];
    subject to symmetry_between_12:
        forall{{m in MATCHES}} x[2,1,m] <= x[1,2,m]; """, 
    'dec_lexAwayDiscending': f"""
    param n := {n_teams}; 
    param weeks := n - 1;
    param periods := n div 2;
    param total_matches := n * (n - 1) div 2;
    set TEAMS := 1..n;
    set WEEKS := 1..weeks;
    set PERIODS := 1..periods;
    set MATCHES := 1..total_matches;
    param match_to_week{{m in MATCHES}} := ((m-1) mod weeks)+1;
    param match_to_period{{m in MATCHES}} := ((m-1) div weeks) + 1;
    param WEIGHT{{p in PERIODS}} := (card(PERIODS) + 1 - p) * n;
    var x{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}} binary;
    var y{{TEAMS, WEEKS, PERIODS}} binary;
    var h{{TEAMS,PERIODS,WEEKS}} binary; #aux
    var a{{TEAMS,PERIODS, WEEKS}} binary; #aux var
    minimize obj: 0;
    let {{i in TEAMS, j in TEAMS , m in MATCHES: i!=j}}x[i,j,m]:=0;
    subject to unique_pairings{{i in TEAMS, j in TEAMS: i < j}}:
        sum{{m in MATCHES}} (x[i,j,m] + x[j,i,m]) = 1;
    subject to match_structure{{m in MATCHES}}:
        sum{{i in TEAMS, j in TEAMS: i != j}} x[i,j,m] = 1;
    subject to weekly_play{{i in TEAMS, w in WEEKS}}:
        sum{{p in PERIODS}} y[i,w,p] = 1;
    subject to link_x_y_home{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[i, match_to_week[m], match_to_period[m]]; 
    subject to link_x_h{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:   
        x[i,j,m] <= h[i,match_to_period[m], match_to_week[m]];
    subject to link_x_y_away{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[j,match_to_week[m],match_to_period[m]];
    subject to link_x_a{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:
        x[i,j,m]<= a[j,match_to_period[m], match_to_week[m]];
    subject to period_capacity{{w in WEEKS, p in PERIODS}}:
        sum{{i in TEAMS}} y[i,w,p] = 2;
    subject to period_limits{{i in TEAMS, p in PERIODS}}:
        sum{{w in WEEKS}} y[i,w,p] <= 2;
    subject to fix_first_match:
        x[2,3,1] = 1;
    subject to lex_home_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * h[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * h[j,p,w+1];
    subject to lex_away_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * a[i,p,w] >= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * a[j,p,w+1];
    subject to symmetry_between_12:
        forall{{m in MATCHES}} x[2,1,m] <= x[1,2,m]; """,
    'dec_with_deficient_without_ascendingWeek1': f"""
    param n := {n_teams};
    param weeks := n - 1;
    param periods := n div 2;
    param total_matches := n * (n - 1) div 2;
    set TEAMS := 1..n;
    set WEEKS := 1..weeks;
    set PERIODS := 1..periods;
    set MATCHES := 1..total_matches;
    param match_to_week{{m in MATCHES}} := ((m-1) mod weeks)+1;
    param match_to_period{{m in MATCHES}} := ((m-1) div weeks) + 1;
    param WEIGHT{{p in PERIODS}} := (card(PERIODS) + 1 - p) * n;
    var x{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}} binary;
    var y{{TEAMS, WEEKS, PERIODS}} binary;
    var h{{TEAMS,PERIODS,WEEKS}} binary;
    var a{{TEAMS,PERIODS, WEEKS}} binary;
    minimize obj: 0;
    let {{i in TEAMS, j in TEAMS , m in MATCHES: i!=j}}x[i,j,m]:=0;
    subject to unique_pairings{{i in TEAMS, j in TEAMS: i < j}}:
        sum{{m in MATCHES}} (x[i,j,m] + x[j,i,m]) = 1;
    subject to match_structure{{m in MATCHES}}:
        sum{{i in TEAMS, j in TEAMS: i != j}} x[i,j,m] = 1;
    subject to link_x_y_home{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[i, match_to_week[m], match_to_period[m]];
    subject to link_x_h{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:   
        x[i,j,m] <= h[i,match_to_period[m], match_to_week[m]];
    subject to link_x_y_away{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[j,match_to_week[m],match_to_period[m]];
    subject to link_x_a{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:
        x[i,j,m]<= a[j,match_to_period[m], match_to_week[m]];
    subject to weekly_play{{i in TEAMS, w in WEEKS}}:
        sum{{p in PERIODS}} y[i,w,p] = 1;
    subject to period_capacity{{w in WEEKS, p in PERIODS}}:
        sum{{i in TEAMS}} y[i,w,p] = 2;
    subject to period_limits{{i in TEAMS, p in PERIODS}}:
        sum{{w in WEEKS}} y[i,w,p] <= 2;
    subject to fix_first_match:
        x[2,3,1] = 1;
    subject to fix_period_deficient{{p in PERIODS}}:
        sum{{w in WEEKS}} y[p,w,p] = 1;
    subject to lex_home_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * h[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * h[j,p,w+1];
    subject to lex_away_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * a[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * a[j,p,w+1];
    subject to symmetry_between_12:
        forall{{m in MATCHES}} x[2,1,m] <= x[1,2,m]; """,
    'dec_withDef_withWeek1': f"""
    param n := {n_teams};  
    param weeks := n - 1;
    param periods := n div 2;
    param total_matches := n * (n - 1) div 2;
    set TEAMS := 1..n;
    set WEEKS := 1..weeks;
    set PERIODS := 1..periods;
    set MATCHES := 1..total_matches;
    param match_to_week{{m in MATCHES}} := ((m-1) mod weeks)+1;
    param match_to_period{{m in MATCHES}} := ((m-1) div weeks) + 1;
    param WEIGHT{{p in PERIODS}} := (card(PERIODS) + 1 - p) * n;
    var x{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}} binary;
    var y{{TEAMS, WEEKS, PERIODS}} binary;
    var h{{TEAMS,PERIODS,WEEKS}} binary;
    var a{{TEAMS,PERIODS, WEEKS}} binary;
    var h1{{TEAMS, PERIODS}} binary;
    minimize obj: 0;
    let {{i in TEAMS, j in TEAMS , m in MATCHES: i!=j}}x[i,j,m]:=0;
    subject to unique_pairings{{i in TEAMS, j in TEAMS: i < j}}:
        sum{{m in MATCHES}} (x[i,j,m] + x[j,i,m]) = 1;
    subject to match_structure{{m in MATCHES}}:
        sum{{i in TEAMS, j in TEAMS: i != j}} x[i,j,m] = 1;
    subject to link_x_y_home{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[i, match_to_week[m], match_to_period[m]];    
    subject to link_x_h{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:   
        x[i,j,m] <= h[i,match_to_period[m], match_to_week[m]];
    subject to link_x_y_away{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[j,match_to_week[m],match_to_period[m]];
    subject to weekly_play{{i in TEAMS, w in WEEKS}}:
        sum{{p in PERIODS}} y[i,w,p] = 1;
    subject to link_x_a{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:
        x[i,j,m]<= a[j,match_to_period[m], match_to_week[m]];
    subject to period_capacity{{w in WEEKS, p in PERIODS}}:
        sum{{i in TEAMS}} y[i,w,p] = 2;
    subject to period_limits{{i in TEAMS, p in PERIODS}}:
        sum{{w in WEEKS}} y[i,w,p] <= 2;
    subject to fix_first_match:
        x[2,3,1] = 1;
    subject to fix_period_deficient{{p in PERIODS}}:
        sum{{w in WEEKS}} y[p,w,p] = 1;
    subject to lex_home_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * h[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * h[j,p,w+1];
    subject to lex_away_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * a[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * a[j,p,w+1];
    subject to symmetry_between_12:
        forall{{m in MATCHES}} x[2,1,m] <= x[1,2,m];
    subject to link_home_vars{{i in TEAMS, p in PERIODS}}:
        h1[i,p] = sum{{j in TEAMS, m in MATCHES: j != i and match_to_week[m] = 1 and match_to_period[m] = p}} x[i,j,m];
    subject to one_home_per_period{{p in PERIODS}}:
        sum{{i in TEAMS}} h1[i,p] = 1;
    subject to home_team_ordering{{p in 1..(periods-1)}}:
        sum{{i in 1..n}} i * h1[i,p] <= sum{{i in 1..n}} i * h1[i,p+1];
    """,
    'dec_withoutDef_withWeek': f"""
    param n := {n_teams};
    param weeks := n - 1;
    param periods := n div 2;
    param total_matches := n * (n - 1) div 2;
    set TEAMS := 1..n;
    set WEEKS := 1..weeks;
    set PERIODS := 1..periods;
    set MATCHES := 1..total_matches;
    param match_to_week{{m in MATCHES}} := ((m-1) mod weeks)+1;
    param match_to_period{{m in MATCHES}} := ((m-1) div weeks) + 1;
    param WEIGHT{{p in PERIODS}} := (card(PERIODS) + 1 - p) * n;
    var x{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}} binary;
    var y{{TEAMS, WEEKS, PERIODS}} binary;
    var h{{TEAMS,PERIODS,WEEKS}} binary;
    var a{{TEAMS,PERIODS, WEEKS}} binary;
    var h1{{TEAMS, PERIODS}} binary;
    minimize obj: 0;
    let {{i in TEAMS, j in TEAMS , m in MATCHES: i!=j}}x[i,j,m]:=0;
    subject to unique_pairings{{i in TEAMS, j in TEAMS: i < j}}:
        sum{{m in MATCHES}} (x[i,j,m] + x[j,i,m]) = 1;
    subject to match_structure{{m in MATCHES}}:
        sum{{i in TEAMS, j in TEAMS: i != j}} x[i,j,m] = 1;
    subject to weekly_play{{i in TEAMS, w in WEEKS}}:
        sum{{p in PERIODS}} y[i,w,p] = 1;
    subject to link_x_y_home{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[i, match_to_week[m], match_to_period[m]];
    subject to link_x_h{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:   
        x[i,j,m] <= h[i,match_to_period[m], match_to_week[m]];
    subject to link_x_y_away{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[j,match_to_week[m],match_to_period[m]];
    subject to link_x_a{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:
        x[i,j,m]<= a[j,match_to_period[m], match_to_week[m]];
    subject to period_capacity{{w in WEEKS, p in PERIODS}}:
        sum{{i in TEAMS}} y[i,w,p] = 2;
    subject to period_limits{{i in TEAMS, p in PERIODS}}:
        sum{{w in WEEKS}} y[i,w,p] <= 2;
    subject to fix_first_match:
        x[2,3,1] = 1;
    subject to lex_home_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * h[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * h[j,p,w+1];
    subject to lex_away_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * a[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * a[j,p,w+1];
    subject to symmetry_between_12:
        forall{{m in MATCHES}} x[2,1,m] <= x[1,2,m];
    subject to link_home_vars{{i in TEAMS, p in PERIODS}}:
        h1[i,p] = sum{{j in TEAMS, m in MATCHES: j != i and match_to_week[m] = 1 and match_to_period[m] = p}} x[i,j,m];
    subject to one_home_per_period{{p in PERIODS}}:
        sum{{i in TEAMS}} h1[i,p] = 1;
    subject to home_team_ordering{{p in 1..(periods-1)}}:
        sum{{i in 1..n}} i * h1[i,p] <= sum{{i in 1..n}} i * h1[i,p+1]; """,
    'dec_final_model_without_initial_values' : f"""
    param n := {n_teams}; 
    param weeks := n - 1;
    param periods := n div 2;
    param total_matches := n * (n - 1) div 2;
    param match_to_week{{m in MATCHES}} := ((m-1) mod weeks)+1;
    param match_to_period{{m in MATCHES}} := ((m-1) div weeks) + 1;
    param WEIGHT{{p in PERIODS}} := (card(PERIODS) + 1 - p) * n;
    set TEAMS := 1..n;
    set WEEKS := 1..weeks;
    set PERIODS := 1..periods;
    set MATCHES := 1..total_matches;
    var x{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}} binary;
    var y{{TEAMS, WEEKS, PERIODS}} binary;
    var h{{TEAMS,PERIODS,WEEKS}} binary; #aux
    var a{{TEAMS,PERIODS, WEEKS}} binary; #aux var
    minimize obj: 0;
    subject to unique_pairings{{i in TEAMS, j in TEAMS: i < j}}:
        sum{{m in MATCHES}} (x[i,j,m] + x[j,i,m]) = 1;
    subject to match_structure{{m in MATCHES}}:
        sum{{i in TEAMS, j in TEAMS: i != j}} x[i,j,m] = 1;
    subject to weekly_play{{i in TEAMS, w in WEEKS}}:
        sum{{p in PERIODS}} y[i,w,p] = 1;
    subject to link_x_y_home{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[i, match_to_week[m], match_to_period[m]]; 
    subject to link_x_h{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:   
        x[i,j,m] <= h[i,match_to_period[m], match_to_week[m]];
    subject to link_x_y_away{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[j,match_to_week[m],match_to_period[m]];
    subject to link_x_a{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:
        x[i,j,m]<= a[j,match_to_period[m], match_to_week[m]];
    subject to period_capacity{{w in WEEKS, p in PERIODS}}:
        sum{{i in TEAMS}} y[i,w,p] = 2;
    subject to period_limits{{i in TEAMS, p in PERIODS}}:
        sum{{w in WEEKS}} y[i,w,p] <= 2;
    subject to fix_first_match:
        x[2,3,1] = 1;
    subject to lex_home_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * h[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * h[j,p,w+1];
    subject to lex_away_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * a[i,p,w] >= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * a[j,p,w+1];
    subject to symmetry_between_12:
        forall{{m in MATCHES}} x[2,1,m] <= x[1,2,m]; """, 
    'dec_trivial_model': f"""
    param n := {n_teams};
    param weeks := n - 1;
    param periods := n div 2;
    param total_matches := n * (n - 1) div 2;
    set TEAMS := 1..n;
    set WEEKS := 1..weeks;
    set PERIODS := 1..periods;
    set MATCHES := 1..total_matches;
    param match_to_week{{m in MATCHES}} := ((m-1) mod weeks)+1;
    param match_to_period{{m in MATCHES}} := ((m-1) div weeks) + 1;
    var x{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}} binary;
    var y{{TEAMS, WEEKS, PERIODS}} binary;
    minimize obj: 0;
    subject to unique_pairings{{i in TEAMS, j in TEAMS: i < j}}:
        sum{{m in MATCHES}} (x[i,j,m] + x[j,i,m]) = 1;
    subject to link_x_y_home{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[i, match_to_week[m], match_to_period[m]];
    subject to link_x_y_away{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[j,match_to_week[m],match_to_period[m]];
    subject to weekly_play{{i in TEAMS, w in WEEKS}}:
        sum{{p in PERIODS}} y[i,w,p] = 1;
    subject to period_limits{{i in TEAMS, p in PERIODS}}:
        sum{{w in WEEKS}} y[i,w,p] <= 2;""", 
    'dec_trivial_noorder':f"""
    param n := {n_teams};
    param weeks := n - 1;
    param periods := n div 2;
    param total_matches := n * (n - 1) div 2;
    set TEAMS := 1..n;
    set WEEKS := 1..weeks;
    set PERIODS := 1..periods;
    set MATCHES := 1..total_matches;
    param match_to_week{{m in MATCHES}} := ((m-1) mod weeks)+1;
    param match_to_period{{m in MATCHES}} := ((m-1) div weeks) + 1;
    var x{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}} binary;
    var y{{TEAMS, WEEKS, PERIODS}} binary;
    minimize obj: 0;
    subject to unique_pairings{{i in TEAMS, j in TEAMS: i < j}}:
        sum{{m in MATCHES}} (x[i,j,m] + x[j,i,m]) = 1;
    subject to weekly_play{{i in TEAMS, w in WEEKS}}:
        sum{{p in PERIODS}} y[i,w,p] = 1;
    subject to period_limits{{i in TEAMS, p in PERIODS}}:
        sum{{w in WEEKS}} y[i,w,p] <= 2;
    subject to link_x_y_home{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[i, match_to_week[m], match_to_period[m]];
    subject to link_x_y_away{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[j,match_to_week[m],match_to_period[m]];""",
    'opt_withoutDef_withoutAscWeek1': f"""
    param n := {n_teams};  # Number of teams (must be even)
    param weeks := n - 1;
    param periods := n div 2;
    param total_matches := n * (n - 1) div 2;
    set TEAMS := 1..n;
    set WEEKS := 1..weeks;
    set PERIODS := 1..periods;
    set MATCHES := 1..total_matches;
    param match_to_week{{m in MATCHES}} := ((m-1) mod weeks)+1;
    param match_to_period{{m in MATCHES}} := ((m-1) div weeks) + 1;
    param WEIGHT{{p in PERIODS}} := (card(PERIODS) + 1 - p) * n;
    var x{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}} binary;
    var y{{TEAMS, WEEKS, PERIODS}} binary;
    var h{{TEAMS,PERIODS,WEEKS}} binary;
    var a{{TEAMS,PERIODS, WEEKS}} binary;
    var obj_funky integer >= n;  
    subject to gamimeno:
        obj_funky = sum{{i in TEAMS}}abs(sum{{j in TEAMS, m in MATCHES: i!=j}}x[i,j,m]- sum{{j in TEAMS,m in MATCHES:i!=j}}x[j,i,m]);
    minimize objective_funky: obj_funky;
    let {{i in TEAMS, j in TEAMS , m in MATCHES: i!=j}}x[i,j,m]:=0;
    subject to unique_pairings{{i in TEAMS, j in TEAMS: i < j}}:
        sum{{m in MATCHES}} (x[i,j,m] + x[j,i,m]) = 1;
    subject to match_structure{{m in MATCHES}}:
        sum{{i in TEAMS, j in TEAMS: i != j}} x[i,j,m] = 1;
    subject to link_x_y_home{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[i, match_to_week[m], match_to_period[m]];
    subject to link_x_h{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:   
        x[i,j,m] <= h[i,match_to_period[m], match_to_week[m]];
    subject to link_x_y_away{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[j,match_to_week[m],match_to_period[m]];
    subject to weekly_play{{i in TEAMS, w in WEEKS}}:
        sum{{p in PERIODS}} y[i,w,p] = 1;
    subject to link_x_a{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:
        x[i,j,m]<= a[j,match_to_period[m], match_to_week[m]];
    subject to period_capacity{{w in WEEKS, p in PERIODS}}:
        sum{{i in TEAMS}} y[i,w,p] = 2;
    subject to period_limits{{i in TEAMS, p in PERIODS}}:
        sum{{w in WEEKS}} y[i,w,p] <= 2;
    subject to fix_first_match:
        x[2,3,1] = 1;
    subject to lex_home_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * h[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * h[j,p,w+1];
    subject to lex_away_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * a[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * a[j,p,w+1];
    subject to symmetry_between_12:
        forall{{m in MATCHES}} x[2,1,m] <= x[1,2,m];
    """,
    'opt_withDef_withoutAscWeek1': f"""
    param n := {n_teams};  # Number of teams (must be even)
    param weeks := n - 1;
    param periods := n div 2;
    param total_matches := n * (n - 1) div 2;
    set TEAMS := 1..n;
    set WEEKS := 1..weeks;
    set PERIODS := 1..periods;
    set MATCHES := 1..total_matches;
    param match_to_week{{m in MATCHES}} := ((m-1) mod weeks)+1;
    param match_to_period{{m in MATCHES}} := ((m-1) div weeks) + 1;
    param WEIGHT{{p in PERIODS}} := (card(PERIODS) + 1 - p) * n;
    var x{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}} binary;
    var y{{TEAMS, WEEKS, PERIODS}} binary;
    var h{{TEAMS,PERIODS,WEEKS}} binary;
    var a{{TEAMS,PERIODS, WEEKS}} binary;
    var obj_funky integer >= n;  
    subject to gamimeno:
        obj_funky = sum{{i in TEAMS}}abs(sum{{j in TEAMS, m in MATCHES: i!=j}}x[i,j,m]- sum{{j in TEAMS,m in MATCHES:i!=j}}x[j,i,m]);
    minimize objective_funky: obj_funky;
    let {{i in TEAMS, j in TEAMS , m in MATCHES: i!=j}}x[i,j,m]:=0;
    let {{i in TEAMS, p in PERIODS, w in WEEKS}}h[i,p,w]:=0;
    let {{i in TEAMS, p in PERIODS, w in WEEKS}}a[i,p,w]:=0;
    subject to unique_pairings{{i in TEAMS, j in TEAMS: i < j}}:
        sum{{m in MATCHES}} (x[i,j,m] + x[j,i,m]) = 1;
    subject to match_structure{{m in MATCHES}}:
        sum{{i in TEAMS, j in TEAMS: i != j}} x[i,j,m] = 1;
    subject to link_x_y_home{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[i, match_to_week[m], match_to_period[m]];
    subject to link_x_h{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:   
        x[i,j,m] <= h[i,match_to_period[m], match_to_week[m]];
    subject to link_x_y_away{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[j,match_to_week[m],match_to_period[m]];
    subject to weekly_play{{i in TEAMS, w in WEEKS}}:
        sum{{p in PERIODS}} y[i,w,p] = 1;
    subject to link_x_a{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:
        x[i,j,m]<= a[j,match_to_period[m], match_to_week[m]];
    subject to period_capacity{{w in WEEKS, p in PERIODS}}:
        sum{{i in TEAMS}} y[i,w,p] = 2;
    subject to period_limits{{i in TEAMS, p in PERIODS}}:
        sum{{w in WEEKS}} y[i,w,p] <= 2;
    subject to fix_first_match:
        x[2,3,1] = 1;
    subject to lex_home_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * h[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * h[j,p,w+1];
    subject to lex_away_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * a[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * a[j,p,w+1];
    subject to symmetry_between_12:
        forall{{m in MATCHES}} x[2,1,m] <= x[1,2,m];
    """,
    'opt_withDef_withAscWeek1': f"""
    param n := {n_teams};  # Number of teams (must be even)
    param weeks := n - 1;
    param periods := n div 2;
    param total_matches := n * (n - 1) div 2;
    set TEAMS := 1..n;
    set WEEKS := 1..weeks;
    set PERIODS := 1..periods;
    set MATCHES := 1..total_matches;
    param match_to_week{{m in MATCHES}} := ((m-1) mod weeks)+1;
    param match_to_period{{m in MATCHES}} := ((m-1) div weeks) + 1;
    param WEIGHT{{p in PERIODS}} := (card(PERIODS) + 1 - p) * n;
    var x{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}} binary;
    var y{{TEAMS, WEEKS, PERIODS}} binary;
    var h{{TEAMS,PERIODS,WEEKS}} binary;
    var a{{TEAMS,PERIODS, WEEKS}} binary;
    var obj_funky integer >= n;  
    subject to gamimeno:
        obj_funky = sum{{i in TEAMS}}abs(sum{{j in TEAMS, m in MATCHES: i!=j}}x[i,j,m]- sum{{j in TEAMS,m in MATCHES:i!=j}}x[j,i,m]);
    minimize objective_funky: obj_funky;
    let {{i in TEAMS, j in TEAMS , m in MATCHES: i!=j}}x[i,j,m]:=0;
    subject to unique_pairings{{i in TEAMS, j in TEAMS: i < j}}:
        sum{{m in MATCHES}} (x[i,j,m] + x[j,i,m]) = 1;
    subject to match_structure{{m in MATCHES}}:
        sum{{i in TEAMS, j in TEAMS: i != j}} x[i,j,m] = 1;
    subject to link_x_y_home{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[i, match_to_week[m], match_to_period[m]];
    subject to link_x_h{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:   
        x[i,j,m] <= h[i,match_to_period[m], match_to_week[m]];
    subject to link_x_y_away{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[j,match_to_week[m],match_to_period[m]];
    subject to weekly_play{{i in TEAMS, w in WEEKS}}:
        sum{{p in PERIODS}} y[i,w,p] = 1;
    subject to link_x_a{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:
        x[i,j,m]<= a[j,match_to_period[m], match_to_week[m]];
    subject to period_capacity{{w in WEEKS, p in PERIODS}}:
        sum{{i in TEAMS}} y[i,w,p] = 2;
    subject to period_limits{{i in TEAMS, p in PERIODS}}:
        sum{{w in WEEKS}} y[i,w,p] <= 2;
    subject to fix_first_match:
        x[2,3,1] = 1;
    subject to lex_home_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * h[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * h[j,p,w+1];
    subject to lex_away_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * a[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * a[j,p,w+1];
    subject to symmetry_between_12:
        forall{{m in MATCHES}} x[2,1,m] <= x[1,2,m];
    subject to link_home_vars{{i in TEAMS, p in PERIODS}}:
        h1[i,p] = sum{{j in TEAMS, m in MATCHES: j != i and match_to_week[m] = 1 and match_to_period[m] = p}} x[i,j,m];
    subject to one_home_per_period{{p in PERIODS}}:
        sum{{i in TEAMS}} h1[i,p] = 1;
    subject to home_team_ordering{{p in 1..(periods-1)}}:
        sum{{i in 1..n}} i * h1[i,p] <= sum{{i in 1..n}} i * h1[i,p+1]; """,
    'opt_withouDef_withAcWeek1': f"""
    param n := {n_teams};  # Number of teams (must be even)
    param weeks := n - 1;
    param periods := n div 2;
    param total_matches := n * (n - 1) div 2;
    set TEAMS := 1..n;
    set WEEKS := 1..weeks;
    set PERIODS := 1..periods;
    set MATCHES := 1..total_matches;
    param match_to_week{{m in MATCHES}} := ((m-1) mod weeks)+1;
    param match_to_period{{m in MATCHES}} := ((m-1) div weeks) + 1;
    param WEIGHT{{p in PERIODS}} := (card(PERIODS) + 1 - p) * n;
    var x{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}} binary;
    var y{{TEAMS, WEEKS, PERIODS}} binary;
    var h{{TEAMS,PERIODS,WEEKS}} binary;
    var a{{TEAMS,PERIODS, WEEKS}} binary;
    var obj_funky integer >= n;  
    subject to gamimeno:
        obj_funky = sum{{i in TEAMS}}abs(sum{{j in TEAMS, m in MATCHES: i!=j}}x[i,j,m]- sum{{j in TEAMS,m in MATCHES:i!=j}}x[j,i,m]);
    minimize objective_funky: obj_funky;
    let {{i in TEAMS, j in TEAMS , m in MATCHES: i!=j}}x[i,j,m]:=0;
    subject to unique_pairings{{i in TEAMS, j in TEAMS: i < j}}:
        sum{{m in MATCHES}} (x[i,j,m] + x[j,i,m]) = 1;
    subject to match_structure{{m in MATCHES}}:
        sum{{i in TEAMS, j in TEAMS: i != j}} x[i,j,m] = 1;
    subject to link_x_y_home{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[i, match_to_week[m], match_to_period[m]];
    subject to link_x_h{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:   
        x[i,j,m] <= h[i,match_to_period[m], match_to_week[m]];
    subject to link_x_y_away{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[j,match_to_week[m],match_to_period[m]];
    subject to weekly_play{{i in TEAMS, w in WEEKS}}:
        sum{{p in PERIODS}} y[i,w,p] = 1;
    subject to link_x_a{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:
        x[i,j,m]<= a[j,match_to_period[m], match_to_week[m]];
    subject to period_capacity{{w in WEEKS, p in PERIODS}}:
        sum{{i in TEAMS}} y[i,w,p] = 2;
    subject to period_limits{{i in TEAMS, p in PERIODS}}:
        sum{{w in WEEKS}} y[i,w,p] <= 2;
    subject to fix_first_match:
        x[2,3,1] = 1;
    subject to lex_home_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * h[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * h[j,p,w+1];
    subject to lex_away_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * a[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * a[j,p,w+1];
    subject to symmetry_between_12:
        forall{{m in MATCHES}} x[2,1,m] <= x[1,2,m]; 
    subject to link_home_vars{{i in TEAMS, p in PERIODS}}:
        h1[i,p] = sum{{j in TEAMS, m in MATCHES: j != i and match_to_week[m] = 1 and match_to_period[m] = p}} x[i,j,m];
    subject to one_home_per_period{{p in PERIODS}}:
        sum{{i in TEAMS}} h1[i,p] = 1;
    subject to home_team_ordering{{p in 1..(periods-1)}}:
        sum{{i in 1..n}} i * h1[i,p] <= sum{{i in 1..n}} i * h1[i,p+1]; """,
    'opt_without_without_initalHA':  f"""
    param n := {n_teams};
    param weeks := n - 1;
    param periods := n div 2;
    param total_matches := n * (n - 1) div 2;
    set TEAMS := 1..n;
    set WEEKS := 1..weeks;
    set PERIODS := 1..periods;
    set MATCHES := 1..total_matches;
    param match_to_week{{m in MATCHES}} := ((m-1) mod weeks)+1;
    param match_to_period{{m in MATCHES}} := ((m-1) div weeks) + 1;
    param WEIGHT{{p in PERIODS}} := (card(PERIODS) + 1 - p) * n;
    var x{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}} binary;
    var y{{TEAMS, WEEKS, PERIODS}} binary;
    var h{{TEAMS,PERIODS,WEEKS}} binary;
    var a{{TEAMS,PERIODS, WEEKS}} binary;
    var obj_funky integer >= n;  
    subject to gamimeno:
        obj_funky = sum{{i in TEAMS}}abs(sum{{j in TEAMS, m in MATCHES: i!=j}}x[i,j,m]- sum{{j in TEAMS,m in MATCHES:i!=j}}x[j,i,m]);
    minimize objective_funky: obj_funky;
    let {{i in TEAMS, j in TEAMS , m in MATCHES: i!=j}}x[i,j,m]:=0;
    let {{i in TEAMS, p in PERIODS, w in WEEKS}}h[i,p,w]:=0;
    let {{i in TEAMS, p in PERIODS, w in WEEKS}}a[i,p,w]:=0;
    subject to unique_pairings{{i in TEAMS, j in TEAMS: i < j}}:
        sum{{m in MATCHES}} (x[i,j,m] + x[j,i,m]) = 1;
    subject to match_structure{{m in MATCHES}}:
        sum{{i in TEAMS, j in TEAMS: i != j}} x[i,j,m] = 1;
    subject to link_x_y_home{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[i, match_to_week[m], match_to_period[m]];
    subject to link_x_h{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:   
        x[i,j,m] <= h[i,match_to_period[m], match_to_week[m]];
    subject to link_x_y_away{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[j,match_to_week[m],match_to_period[m]];
    subject to weekly_play{{i in TEAMS, w in WEEKS}}:
        sum{{p in PERIODS}} y[i,w,p] = 1;
    subject to link_x_a{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:
        x[i,j,m]<= a[j,match_to_period[m], match_to_week[m]];
    subject to period_capacity{{w in WEEKS, p in PERIODS}}:
        sum{{i in TEAMS}} y[i,w,p] = 2;
    subject to period_limits{{i in TEAMS, p in PERIODS}}:
        sum{{w in WEEKS}} y[i,w,p] <= 2;
    subject to fix_period_deficient{{p in PERIODS}}:
        sum{{w in WEEKS}} y[p,w,p] = 1;
    subject to fix_first_match:
        x[2,3,1] = 1;
    subject to lex_home_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * h[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * h[j,p,w+1];
    subject to lex_away_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * a[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * a[j,p,w+1];
    subject to symmetry_between_12:
        forall{{m in MATCHES}} x[2,1,m] <= x[1,2,m];
    """,
    'opt_noInitialvalues':f"""
    param n := {n_teams};  # Number of teams (must be even)
    param weeks := n - 1;
    param periods := n div 2;
    param total_matches := n * (n - 1) div 2;
    set TEAMS := 1..n;
    set WEEKS := 1..weeks;
    set PERIODS := 1..periods;
    set MATCHES := 1..total_matches;
    param match_to_week{{m in MATCHES}} := ((m-1) mod weeks)+1;
    param match_to_period{{m in MATCHES}} := ((m-1) div weeks) + 1;
    param WEIGHT{{p in PERIODS}} := (card(PERIODS) + 1 - p) * n;
    var x{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}} binary;
    var y{{TEAMS, WEEKS, PERIODS}} binary;
    var h{{TEAMS,PERIODS,WEEKS}} binary;
    var a{{TEAMS,PERIODS, WEEKS}} binary;
    var obj_funky integer >= n;  
    subject to gamimeno:
        obj_funky = sum{{i in TEAMS}}abs(sum{{j in TEAMS, m in MATCHES: i!=j}}x[i,j,m]- sum{{j in TEAMS,m in MATCHES:i!=j}}x[j,i,m]);
    minimize objective_funky: obj_funky;
    subject to unique_pairings{{i in TEAMS, j in TEAMS: i < j}}:
        sum{{m in MATCHES}} (x[i,j,m] + x[j,i,m]) = 1;
    subject to match_structure{{m in MATCHES}}:
        sum{{i in TEAMS, j in TEAMS: i != j}} x[i,j,m] = 1;
    subject to link_x_y_home{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[i, match_to_week[m], match_to_period[m]];
    subject to link_x_h{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:   
        x[i,j,m] <= h[i,match_to_period[m], match_to_week[m]];
    subject to link_x_y_away{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[j,match_to_week[m],match_to_period[m]];
    subject to weekly_play{{i in TEAMS, w in WEEKS}}:
        sum{{p in PERIODS}} y[i,w,p] = 1;
    subject to link_x_a{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:
        x[i,j,m]<= a[j,match_to_period[m], match_to_week[m]];
    subject to period_capacity{{w in WEEKS, p in PERIODS}}:
        sum{{i in TEAMS}} y[i,w,p] = 2;
    subject to period_limits{{i in TEAMS, p in PERIODS}}:
        sum{{w in WEEKS}} y[i,w,p] <= 2;
    subject to fix_first_match:
        x[2,3,1] = 1;
    subject to lex_home_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * h[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * h[j,p,w+1];
    subject to lex_away_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * a[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * a[j,p,w+1];
    subject to symmetry_between_12:
        forall{{m in MATCHES}} x[2,1,m] <= x[1,2,m]; """   ,
    'opt_noBound': f"""
    param n := {n_teams};  # Number of teams (must be even)
    param weeks := n - 1;
    param periods := n div 2;
    param total_matches := n * (n - 1) div 2;
    set TEAMS := 1..n;
    set WEEKS := 1..weeks;
    set PERIODS := 1..periods;
    set MATCHES := 1..total_matches;
    param match_to_week{{m in MATCHES}} := ((m-1) mod weeks)+1;
    param match_to_period{{m in MATCHES}} := ((m-1) div weeks) + 1;
    param WEIGHT{{p in PERIODS}} := (card(PERIODS) + 1 - p) * n;
    var x{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}} binary;
    var y{{TEAMS, WEEKS, PERIODS}} binary;
    var h{{TEAMS,PERIODS,WEEKS}} binary;
    var a{{TEAMS,PERIODS, WEEKS}} binary;
    minimize objective_funky:sum{{i in TEAMS}}abs(sum{{j in TEAMS, m in MATCHES: i!=j}}x[i,j,m]- sum{{j in TEAMS,m in MATCHES:i!=j}}x[j,i,m]);
    let {{i in TEAMS, j in TEAMS , m in MATCHES: i!=j}}x[i,j,m]:=0;
    subject to unique_pairings{{i in TEAMS, j in TEAMS: i < j}}:
        sum{{m in MATCHES}} (x[i,j,m] + x[j,i,m]) = 1;
    subject to match_structure{{m in MATCHES}}:
        sum{{i in TEAMS, j in TEAMS: i != j}} x[i,j,m] = 1;
    subject to link_x_y_home{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[i, match_to_week[m], match_to_period[m]];
    subject to link_x_h{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:   
        x[i,j,m] <= h[i,match_to_period[m], match_to_week[m]];
    subject to link_x_y_away{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[j,match_to_week[m],match_to_period[m]];
    subject to weekly_play{{i in TEAMS, w in WEEKS}}:
        sum{{p in PERIODS}} y[i,w,p] = 1;
    subject to link_x_a{{i in TEAMS, j in TEAMS, m in MATCHES: i !=j}}:
        x[i,j,m]<= a[j,match_to_period[m], match_to_week[m]];
    subject to period_capacity{{w in WEEKS, p in PERIODS}}:
        sum{{i in TEAMS}} y[i,w,p] = 2;
    subject to period_limits{{i in TEAMS, p in PERIODS}}:
        sum{{w in WEEKS}} y[i,w,p] <= 2;
    subject to fix_first_match:
        x[2,3,1] = 1;
    subject to lex_home_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * h[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * h[j,p,w+1];
    subject to lex_away_across_weeks{{w in 1..(weeks-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * a[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * a[j,p,w+1];
    subject to symmetry_between_12:
        forall{{m in MATCHES}} x[2,1,m] <= x[1,2,m]; """,
    'opt_trivial_ordered': f"""
    param n := {n_teams};
    param weeks := n - 1;
    param periods := n div 2;
    param total_matches := n * (n - 1) div 2;
    set TEAMS := 1..n;
    set WEEKS := 1..weeks;
    set PERIODS := 1..periods;
    set MATCHES := 1..total_matches;
    param match_to_week{{m in MATCHES}} := ((m-1) mod weeks)+1;
    param match_to_period{{m in MATCHES}} := ((m-1) div weeks) + 1;
    var x{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}} binary;
    var y{{TEAMS, WEEKS, PERIODS}} binary;
    minimize objective_funky:sum{{i in TEAMS}}abs(sum{{j in TEAMS, m in MATCHES: i!=j}}x[i,j,m]- sum{{j in TEAMS,m in MATCHES:i!=j}}x[j,i,m]);
    subject to unique_pairings{{i in TEAMS, j in TEAMS: i < j}}:
        sum{{m in MATCHES}} (x[i,j,m] + x[j,i,m]) = 1;
    subject to link_x_y_home{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[i, match_to_week[m], match_to_period[m]];
    subject to link_x_y_away{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[j,match_to_week[m],match_to_period[m]];
    subject to weekly_play{{i in TEAMS, w in WEEKS}}:
        sum{{p in PERIODS}} y[i,w,p] = 1;
    subject to period_limits{{i in TEAMS, p in PERIODS}}:
        sum{{w in WEEKS}} y[i,w,p] <= 2;""", 
    'opt_trivial_noorder':f"""
    param n := {n_teams};
    param weeks := n - 1;
    param periods := n div 2;
    param total_matches := n * (n - 1) div 2;
    set TEAMS := 1..n;
    set WEEKS := 1..weeks;
    set PERIODS := 1..periods;
    set MATCHES := 1..total_matches;
    param match_to_week{{m in MATCHES}} := ((m-1) mod weeks)+1;
    param match_to_period{{m in MATCHES}} := ((m-1) div weeks) + 1;
    var x{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}} binary;
    var y{{TEAMS, WEEKS, PERIODS}} binary;
    minimize objective_funky:sum{{i in TEAMS}}abs(sum{{j in TEAMS, m in MATCHES: i!=j}}x[i,j,m]- sum{{j in TEAMS,m in MATCHES:i!=j}}x[j,i,m]);
    subject to unique_pairings{{i in TEAMS, j in TEAMS: i < j}}:
        sum{{m in MATCHES}} (x[i,j,m] + x[j,i,m]) = 1;
    subject to weekly_play{{i in TEAMS, w in WEEKS}}:
        sum{{p in PERIODS}} y[i,w,p] = 1;
    subject to period_limits{{i in TEAMS, p in PERIODS}}:
        sum{{w in WEEKS}} y[i,w,p] <= 2;
    subject to link_x_y_home{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[i, match_to_week[m], match_to_period[m]];
    subject to link_x_y_away{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[j,match_to_week[m],match_to_period[m]];"""
    }

                


if __name__ == "__main__":
    for n in [4,6,8,10,12,14]: 
        for solver in ["cplex","gurobi","highs","cbc"]:
            list_of_modelNames = list(get_models(n,solver).keys())
            list_of_models =list(get_models(n,solver).values())
            for i in range(len(list_of_models)):
                model=list_of_models[i]
                model_name=list_of_modelNames[i]
                ampl.eval(model)
                list_of_models
                solution=solve_tournament(ampl,n,solver,time_limit=300)
                with open(f"../../res/MIP/{n}.json", "a") as file:
                    json.dump(reformat_solution(solution,model_name,solver), file, indent=4)
                ampl.reset()

            
#something about the final json format and ","


# Using solution properties within an enumerative search to solve a
#  sports league scheduling problem

    
        
