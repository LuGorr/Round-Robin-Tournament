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
    teams_per_week = [] 
    for i in range(len(home)):
        teams_per_week.append(sorted(home[i]+away[i]))
        for j in range(len(home[0])):
            key = f"{home[i][j]}, {away[i][j]}"
            occurrences[key] = occurrences.get(key, 0) + 1
    #Count occurrences of teams during a period
    period_occurrences = {}
    for j in range(len(home[0])):
        for i in range(len(home)):
            key1 = f"{j}, {home[i][j]}"
            key2 = f"{j}, {away[i][j]}"
            period_occurrences[key1] = period_occurrences.get(key1, 0) + 1
            period_occurrences[key2] = period_occurrences.get(key2, 0) + 1

    for i in range(len(home)):
        if teams_per_week[i] == list(range(len(home))):
            print(f"Not every team has played during week {i+1}")
            err = True
        for j in range(len(home[0])):
            key = f"{home[i][j]}, {away[i][j]}"
            key1 = f"{j}, {home[i][j]}"
            key2 = f"{j}, {away[i][j]}"
            #Check if a matchup has happened more than one time or if it never took place
            if(occurrences[key] > 1):
                print(f"More than a match between team {home[i][j]} and {away[i][j]}")
                err = True
            if(occurrences[key] < 1):
                print(f"No match between team {home[i][j]} and {away[i][j]}")
                err = True
            #Check if a team has played more than two times over the same period
            if((period_occurrences[key1] > 2) or (period_occurrences[key2] > 2)):
                print("At least a team has played more than two matches during the same period")
                err = True
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



for error in err:
    if error:
        print("Check terminated with errors!")
        exit

print("Check terminated successfully")