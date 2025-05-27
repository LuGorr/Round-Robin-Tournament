import json
import os
import ast
path = os.getcwd() + "/CP/test.json"

with open(path, 'r') as file:
    data = json.load(file)
sols = ast.literal_eval(data["output"]["default"])
