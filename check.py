import json
import os
import ast
#Get path (needs to be more general, maybe cli input)
path = os.getcwd() + "/CP/test.json"

#Open json
with open(path, 'r') as file:
    data = json.load(file)
#Loads the results in a matrix (needs to be more general, if the ouput of another method differs it doesn't work)
sols = ast.literal_eval(data["output"]["default"])
