
import pandas as pd
import numpy as np
from amplpy import AMPL, Environment,ampl_notebook, DataFrame
import time
import os
import math
import json
ampl = ampl_notebook(modules=["highs", "cbc", "gurobi", "cplex"], license_uuid="caf71c55-8ecf-4310-90e3-f0195364ecce")


import argparse





def solve_tournament(ampl, n_teams, solver='gurobi', time_limit=300):
    ampl.option['solver'] = solver
    if solver == 'cbc':
        ampl.option[f'{solver}_options'] = f'timelim={time_limit}'
    else:
        ampl.option[f'{solver}_options'] = f'timelim={time_limit} threads=1'

    start_time = time.time()
    ampl.solve()
    solve_time = time.time() - start_time
    solve_result = ampl.get_value('solve_result')
    return extract_solution(ampl, n_teams, solve_time, solve_result)

def extract_solution(ampl, n_teams, solve_time, solve_result):
    if solve_result == 'solved':
        x = ampl.get_variable('x')
        obj = ampl.get_objective('objective_funky').value()
        matches = []
        weeks = n_teams - 1
        periods = n_teams // 2

        for i in range(1, n_teams + 1):
            for j in range(1, n_teams + 1):
                if i != j:
                    for m in range(1, n_teams * (n_teams - 1) // 2 + 1):
                        if x[i, j, m].value() > 0.5:
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

        return {
            'matches_df': df_matches,
            'weekly_schedule': weekly_schedule,
            'solve_time': solve_time,
            'n_teams': n_teams,
            'obj': obj,
            'optimal':True
        }
    
    if solve_result== 'infeasible':
        return {
            'matches_df': pd.DataFrame({'A': []}),'solve_time': 0,'n_teams': n_teams,'obj': None, 'optimal':True }


    else:
        return {
            'matches_df': pd.DataFrame({'A': []}),'solve_time': solve_time,'n_teams': n_teams,'obj': 0, 'optimal' : False  }
    

    
def reformat_solution(result_dict, model_name , solver):

    matches_df = result_dict['matches_df']
    solve_time = result_dict['solve_time']
    n_teams = result_dict['n_teams']
    obj = result_dict['obj']
    optimal = result_dict['optimal']
    time = math.floor(solve_time)
    
    
    if obj!=n_teams:
        obj = 'None'
    
    if time>300:
        time=300
    

    n_periods = n_teams // 2
    n_weeks = n_teams - 1
    
    sol = []
    if matches_df.empty:
        return {f'{solver}_{model_name}':{
        'time': time,
        'optimal': optimal,
        'obj': obj,
        'sol': sol}}
    else:
        for period in range(1, n_periods + 1):
            week_matches = []
            for week in range(1, n_weeks + 1):
                match_row = matches_df[(matches_df['Week'] == week) & (matches_df['Period'] == period)]
                if not match_row.empty:
                    home_team = int(match_row['Home'].iloc[0])
                    away_team = int(match_row['Away'].iloc[0])
                    week_matches.append([home_team, away_team])
            sol.append(week_matches)
    
        return {f'{solver}_{model_name}':{
            'time': time,
            'optimal': optimal,
            'obj': obj,
            'sol': sol}}







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
    minimize objective_funky: 0;
    let {{i in TEAMS, j in TEAMS , m in MATCHES: i!=j}}x[i,j,m]:=0;
    let{{i in TEAMS, j in TEAMS:i<j}}x[i,j,(i - 1) * n - ((i - 1) * i) div 2 + (j - i)]:=1;
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
    subject to lex_home_across_weeks{{w in 1..(n/2-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * h[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * h[j,p,w+1];
    subject to lex_away_across_weeks{{w in 1..(n/2-1)}}:
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
    minimize objective_funky: 0;
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
    subject to lex_home_across_weeks{{w in 1..(weeks/2-1)}}:
       sum{{p in PERIODS, i in TEAMS}} WEIGHT[p] * i * h[i,p,w] <= sum{{p in PERIODS, j in TEAMS}} WEIGHT[p] * j * h[j,p,w+1];
    subject to lex_away_across_weeks{{w in 1..(weeks/2-1)}}:
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
    minimize objective_funky: 0;
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
    minimize objective_funky: 0;
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
    'dec_final_without_initial_values' : f"""
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
    minimize objective_funky: 0;
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
    'dec_trivial':f"""
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
    minimize objective_funky: 0;
    subject to unique_pairings{{i in TEAMS, j in TEAMS: i != j}}:
        sum{{m in MATCHES}} (x[i,j,m] + x[j,i,m]) = 1;
    subject to weekly_play{{i in TEAMS, w in WEEKS}}:
        sum{{p in PERIODS}} y[i,w,p] = 1;
    subject to period_limits{{i in TEAMS, p in PERIODS}}:
        sum{{w in WEEKS}} y[i,w,p] <= 2;
    subject to link_x_y_home{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[i, match_to_week[m], match_to_period[m]];
    subject to link_x_y_away{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[j,match_to_week[m],match_to_period[m]];
    subject to match_structure{{m in MATCHES}}:
        sum{{i in TEAMS, j in TEAMS: i != j}} x[i,j,m] = 1;    """,
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
    subject to objective_function_defintion:
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
    'opt_withoutDef_withAscWeek1': f"""
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
    var h1{{TEAMS, PERIODS}} binary;
    var obj_funky integer >= n;  
    subject to gamimeno:
        obj_funky = sum{{i in TEAMS}}abs(sum{{j in TEAMS, m in MATCHES: i!=j}}x[i,j,m]- sum{{j in TEAMS,m in MATCHES:i!=j}}x[j,i,m]);
    minimize objective_funky: obj_funky;
    let {{i in TEAMS, j in TEAMS , m in MATCHES: i!=j}}x[i,j,m]:=0;
    subject to unique_pairings{{i in TEAMS, j in TEAMS: i != j}}:
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
    subject to objective_function_defintion:
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
    var h1{{TEAMS, PERIODS}} binary;
    var obj_funky integer >= n;  
    subject to objective_function_defintion:
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
    var h1{{TEAMS, PERIODS}} binary;
    var obj_funky integer >= n;  
    subject to objective_function_defintion:
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
    subject to objective_function_defintion:
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
    subject to objective_function_defintion:
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
    'opt_trivial':f"""
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
    subject to unique_pairings{{i in TEAMS, j in TEAMS: i != j}}:
        sum{{m in MATCHES}} (x[i,j,m] + x[j,i,m]) = 1;
    subject to weekly_play{{i in TEAMS, w in WEEKS}}:
        sum{{p in PERIODS}} y[i,w,p] = 1;
    subject to period_limits{{i in TEAMS, p in PERIODS}}:
        sum{{w in WEEKS}} y[i,w,p] <= 2;
    subject to link_x_y_home{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[i, match_to_week[m], match_to_period[m]];
    subject to link_x_y_away{{i in TEAMS, j in TEAMS, m in MATCHES: i != j}}:
        x[i,j,m] <= y[j,match_to_week[m],match_to_period[m]];
    subject to match_structure{{m in MATCHES}}:
        sum{{i in TEAMS, j in TEAMS: i != j}} x[i,j,m] = 1;    
    """
        }



# if __name__ == "__main__":
#     for n in [4, 6, 8, 10, 12, 14]: 
#         for solver in ["cplex", "gurobi", "highs", "cbc"]:
#             models_dict = get_models(n, solver)
#             for model_name, model in models_dict.items():
#                 ampl.eval(model)
#                 solution = solve_tournament(ampl, n, solver, time_limit=300)
#                 reformatted = reformat_solution(solution, model_name, solver)

#                 # Prepare output path
#                 path = f"../../res/MIP/{n}.json"
#                 if os.path.exists(path):
#                     with open(path, "r") as file:
#                         results = json.load(file)
#                 else:
#                     results = {}

#                 # Update result
#                 results.update(reformatted)

#                 # Write updated JSON
#                 with open(path, "w") as file:
#                     json.dump(results, file, indent=4)

#                 ampl.reset()






def run_and_save(ampl, n, solver, model_name, model_code):
    ampl.eval(model_code)
    solution = solve_tournament(ampl, n, solver, time_limit=300)
    reformatted = reformat_solution(solution, model_name, solver)

    path = f"../../res/MIP/{n}.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            results = json.load(f)
    else:
        results = {}

    results.update(reformatted)
    with open(path, "w") as f:
        json.dump(results, f, indent=4)

    ampl.reset()

def run_all(ampl):
    for n in [4, 6, 8, 10, 12, 14,16]: 
        for solver in ["cplex", "gurobi", "highs", "cbc"]:
            models_dict = get_models(n, solver)
            for model_name, model_code in models_dict.items():
                print(f"Running: n={n}, solver={solver}, model={model_name}")
                run_and_save(ampl, n, solver, model_name, model_code)

def run_single(ampl, n, solver, model_name):
    models_dict = get_models(n, solver)
    if model_name not in models_dict:
        print(f"Model '{model_name}' not found for n={n} and solver={solver}")
        return
    model_code = models_dict[model_name]
    print(f"Running single: n={n}, solver={solver}, model={model_name}")
    run_and_save(ampl, n, solver, model_name, model_code)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MIP models on tournament instances.")
    parser.add_argument('-n', type=int, help="Number of teams (instance size)")
    parser.add_argument('--model', type=str, help="Model name")
    parser.add_argument('--solver', type=str, default="cplex", help="Solver to use")
    parser.add_argument('--all', action='store_true', help="Run all models on all instances")

    args = parser.parse_args()

    from amplpy import AMPL  
    ampl = AMPL()

    if args.all:
        run_all(ampl)
    elif args.n and args.model:
        run_single(ampl, args.n, args.solver, args.model)
    else:
        print("Please specify --all or -n with --model (and optionally --solver)")

