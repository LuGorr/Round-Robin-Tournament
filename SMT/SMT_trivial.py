import argparse
import json
import math
import time

from z3 import *

def create_output(result, runtime, model, home, away, weeks, periods, timeout=300):
    """
    Creates the output dictionary in the required JSON format.
    
    Args:
        result: Z3 solver result (sat, unsat, or unknown)
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
        output["obj"] = None
        
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
    
    return {
                "z3": output
    }

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
    
    s = Solver()
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

    # Solve and measure time
    result = s.check()
    end_time = time.time()
    runtime = end_time - start_time
    
    # Get model if solution found
    model = s.model() if result == sat else None
    
    # Create and return output
    return create_output(result, runtime, model, home, away, weeks, periods, timeout)


parser = argparse.ArgumentParser("Prob026: Sports Scheduling")
parser.add_argument("teams", help="An amount of teams to solve the problem for.", type=int)
args = parser.parse_args()

result = solve_round_robin(args.teams)

print(format_json_output(result))