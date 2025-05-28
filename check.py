'''
This program works by doing "minizinc --json-stream --param-file 
"solver-configs/10-solve-gecode.mpc" CP/multi_data_rep.mzn > CP/test.json" 
(pwd CDMO folder). 
The output in test.json won't be formatted properly (still to figure out) 
so you need to add 
"{"sols":[" at the start of file, 
a comma at the end of every line except last where you add "}".
'''
import json
import os
import ast
import copy

def check(home, away, err):
    #Count occurrences of matches between teams
    occurrences = {}
    for i in range(len(home)+1):
        for j in range(len(home)+1):
            if(j!= i):
                if (i>=j):
                    key = f"{i+1}, {j+1}"
                else:
                    key = f"{j+1}, {i+1}"
                occurrences[key] = 0
    
    teams_per_week = [] 
    for i in range(len(home)):
        teams_per_week.append(sorted(home[i]+away[i]))
        for j in range(len(home[0])):
            if (home[i][j]>=away[i][j]):
                key = f"{home[i][j]}, {away[i][j]}"
            else:
                key = f"{away[i][j]}, {home[i][j]}"
            occurrences[key] += 1

    #Count occurrences of teams during a period
    period_occurrences = {}
    for j in range(len(home[0])):
        for i in range(len(home)):
            key1 = f"{j}, {home[i][j]}"
            key2 = f"{j}, {away[i][j]}"
            period_occurrences[key1] = period_occurrences.get(key1, 0) + 1
            period_occurrences[key2] = period_occurrences.get(key2, 0) + 1
    err_period = False
    for i in range(len(home)):
        if teams_per_week[i] != list(range(1,len(home)+2)):
            print(f"Not every team has played during week {i+1}, {teams_per_week[i]}")
            err = True
        for j in range(len(home[0])):
            key1 = f"{j}, {home[i][j]}"
            key2 = f"{j}, {away[i][j]}"
            if err_period:
                break
            if((period_occurrences[key1] > 2) or (period_occurrences[key2] > 2)):
                print(f"At least a team has played more than two matches during the same period")
                err = True
                err_period = True
    for key, elem in occurrences.items():
        #Check if a matchup has happened more than one time or if it never took place
            if(elem > 1):
                print(f"More than a match between team {key[0]} and {key[3]}")
                err = True
            if(elem < 1):
                print(f"No match between team {key[0]} and {key[3]}")
                err = True
            #Check if a team has played more than two times over the same period
    return err
#Get path (needs to be more general, maybe cli input)
path = os.getcwd() + "/CP/test.json"

#Open json
with open(path, 'r') as file:
    data = json.load(file)
home = []
away = []
sols = []
#Loads the results (needs to be more general, if the ouput of another method differs it doesn't work)
for i, elem in enumerate(data["sols"]):
    sols.append(ast.literal_eval(elem["output"]["default"]))
    home.append(sols[i][0])
    away.append(sols[i][1])

err = []
for i in range(len(home)):
    err.append(check(home[i], away[i], False))


global_error = False
for i, error in enumerate(err):
    if error:
        print(f"Check n. {i+1} terminated with errors!")
        global_error = True

if not global_error:
    print("Check terminated successfully")