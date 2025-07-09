import argparse
import json
import math
import time

from z3 import *
from pathlib import Path

def create_output(result, obj, runtime, model, home, away, weeks, periods, timeout=300):
    """
    Creates the output dictionary in the required JSON format.
    
    Args:
        result: Z3 solver result (sat, unsat, or unknown)
        obj: Objective value (if result is sat)
        runtime: Actual runtime in seconds
        model: Z3 model (if result is sat)
        home: Home team variables matrix
        away: Away team variables matrix
        weeks: Number of weeks
        periods: Number of periods
        timeout: Timeout threshold in seconds
    
    Returns:
        Dictionary with time, optimal, obj, and sol fields
    """
    output = {
        "time": None,
        "optimal": None,
        "obj": None,
        "sol": None
    }
    
    if result == sat:
        # Solution found
        output["time"] = math.floor(runtime)
        output["optimal"] = True
        output["obj"] = obj.as_long()
        
        # Extract solution in required format: periods × weeks
        schedule = []
        for p in range(periods):
            period_games = []
            for w in range(weeks):
                home_team = model[home[w][p]].as_long() + 1
                away_team = model[away[w][p]].as_long() + 1
                period_games.append([home_team, away_team])
            schedule.append(period_games)
        
        output["sol"] = schedule
        
    else:
        # No solution found or timeout
        if runtime >= timeout:
            output["time"] = 300
        else:
            output["time"] = math.floor(runtime)
        if result == unsat:
            output["optimal"] = True
        else:
            output["optimal"] = False

        output["obj"] = None
        output["sol"] = []
    
    return output

def format_json_output(output):
    """
    Formats the output JSON with sol field on a single line.
    """
    if output.get("sol") is None:
        return json.dumps(output, indent=2)
    
    # Create a copy without sol field
    output_without_sol = {k: v for k, v in output.items() if k != "sol"}
    
    # Get compact sol representation
    sol_compact = json.dumps(output["sol"], separators=(',', ':'))
    
    # Format the JSON without sol field
    json_without_sol = json.dumps(output_without_sol, indent=2)
    
    # Insert sol field before the closing brace
    lines = json_without_sol.split('\n')
    # Remove the last line (closing brace)
    lines = lines[:-1]
    # Add comma to the last field if it doesn't have one
    if lines[-1].strip() and not lines[-1].strip().endswith(','):
        lines[-1] = lines[-1] + ','
    # Add sol field
    lines.append(f'  "sol": {sol_compact}')
    # Add closing brace
    lines.append('}')
    
    return '\n'.join(lines)

def solve_round_robin(n):
    if n % 2 != 0:
        raise ValueError("Number of teams must be even")
    
    start_time = time.time()
    timeout = 300  # 300 seconds timeout
    
    weeks = n - 1
    periods = n // 2
    
    # Variables: home[w][p] and away[w][p] represent team assignments
    home = [[Int(f"home_{w}_{p}") for p in range(periods)] for w in range(weeks)]
    away = [[Int(f"away_{w}_{p}") for p in range(periods)] for w in range(weeks)]
    
    s = Optimize()
    s.set("timeout", timeout * 1000)  # Z3 timeout in milliseconds
    
    # Domain constraints
    for w in range(weeks):
        for p in range(periods):
            s.add(And(home[w][p] >= 0, home[w][p] < n))
            s.add(And(away[w][p] >= 0, away[w][p] < n))
            s.add(home[w][p] != away[w][p])
    
    # Each team plays once per week
    for w in range(weeks):
        teams_in_week = []
        for p in range(periods):
            teams_in_week.extend([home[w][p], away[w][p]])
        s.add(Distinct(teams_in_week))
    
    # Every team plays with every other team exactly once
    for t1 in range(n):
        for t2 in range(t1 + 1, n):
            games = []
            for w in range(weeks):
                for p in range(periods):
                    game1 = And(home[w][p] == t1, away[w][p] == t2)
                    game2 = And(home[w][p] == t2, away[w][p] == t1)
                    games.extend([game1, game2])
            s.add(PbEq([(g, 1) for g in games], 1))
    
    # Each team plays at most twice in the same period
    for t in range(n):
        for p in range(periods):
            appearances = []
            for w in range(weeks):
                home_app = home[w][p] == t
                away_app = away[w][p] == t
                appearances.extend([home_app, away_app])
            s.add(PbLe([(app, 1) for app in appearances], 2))
    
    # SYMMETRY BREAKING CONSTRAINTS
    
    # 1. Fix team 0's first game.
    # Eliminates team relabeling symmetry.
    s.add(home[0][0] == 0)
    s.add(away[0][0] == 1)
    '''
    # 2. Order periods in first week by home team.
    # Home teams must be in ascending order across periods. E.g.:
    # If periods are [(0,1), (2,3), (4,5)], home teams are ordered: 0 < 2 < 4.
    # Eliminates period reordering symmetry within first week.
    for p in range(periods - 1):
        s.add(home[0][p] < home[0][p + 1])
    
    # 3. Team 0 appears in period 0 more often than other periods.
    # Eliminates symmetry between periods by establishing preference order.
    for p in range(1, periods):
        count_p0 = Sum([If(Or(home[w][0] == 0, away[w][0] == 0), 1, 0) for w in range(weeks)])
        count_p = Sum([If(Or(home[w][p] == 0, away[w][p] == 0), 1, 0) for w in range(weeks)])
        # Constraint: Team 0 appears in period 0 at least as often as any other period
        s.add(count_p0 >= count_p)

    # 4. Lexicographic ordering on weeks:
    # Week w ≤ Week w+1 when viewed as sequences.
    # Eliminates week reordering symmetry.
    for w in range(weeks - 1):
        week_diff = []
        for p in range(periods):
            home_diff = home[w][p] - home[w + 1][p]
            away_diff = away[w][p] - away[w + 1][p]
            week_diff.extend([home_diff, away_diff])
        
        # Ensure lexicographic order
        lex_constraints = []
        for i in range(len(week_diff)):
            # All differences up to position i are zero
            prefix_equal = And([week_diff[j] == 0 for j in range(i)])
            # Difference at position i is negative
            current_less = week_diff[i] < 0
            lex_constraints.append(And(prefix_equal, current_less))
        s.add(Or(lex_constraints + [And([d == 0 for d in week_diff])]))
    '''
    # 5. Break symmetry between equivalent teams
    # Teams 1 and 2 ordering in their first appearance
    # Prefer team 1 as home when playing against team 2.
    # Eliminates home/away symmetry for team pairs.
    for w in range(weeks):
        for p in range(periods):
            # True when teams 1 and 2 play each other
            game_with_12 = Or(
                And(home[w][p] == 1, away[w][p] == 2),
                And(home[w][p] == 2, away[w][p] == 1)
            )
            # If teams 1 and 2 play, prefer lower-numbered team (1) as home
            prefer_1_home = Implies(game_with_12, home[w][p] <= away[w][p])
            s.add(prefer_1_home)

    diff = Int("diff")

    # Sum total home and away games
    for team in range(n):
        total_home = Sum([If(home[w][p] == team, 1, 0) for w in range(weeks) for p in range(periods)])
        total_away = Sum([If(away[w][p] == team, 1, 0) for w in range(weeks) for p in range(periods)])
        s.add(diff >= Abs(total_home - total_away))

    s.add(diff >= 1)
    objective = s.minimize(diff)
    # Solve and measure time
    result = s.check()
    end_time = time.time()
    runtime = end_time - start_time
    
    # Get model if solution found
    model = s.model() if result == sat else None
    obj = objective.value() if result == sat else None
    
    # Create and return output
    return create_output(result, obj, runtime, model, home, away, weeks, periods, timeout)

def update_results_file(n, result, method_name="z3_optimize"):
    """
    Updates or creates the results file for a given n.
    
    Args:
        n: Number of teams
        result: Result dictionary from solve function
        method_name: Name of the method (e.g., "z3_tactics", "z3_basic")
    """
    file_path = f"{Path.cwd()}/res/SMT/{n}.json"
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Check if file exists and load existing data
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            # If file is corrupted or can't be read, start fresh
            data = {}
    else:
        data = {}
    
    # Add new result
    data[method_name] = result
    
    # Write back to file
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Results updated in {file_path}")

parser = argparse.ArgumentParser("Prob026: Sports Scheduling")
parser.add_argument("teams", help="An amount of teams to solve the problem for.", type=int)
args = parser.parse_args()

result = solve_round_robin(args.teams)

update_results_file(args.teams, result)
print(format_json_output(result))