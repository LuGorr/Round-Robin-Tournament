#!/bin/bash

while getopts "n:s:" opt; do
  case $opt in
    n)
      n=$OPTARG
      ;;
    s)
      s=$OPTARG
      ;;
    *)
      echo "Opzione non valida"
      exit 1
      ;;
  esac
done
#json=$(minizinc --statistics --json-stream --solver-time-limit 300000 --param-file $s CP/optimization.mzn -D "n=$n")
json=$(minizinc --statistics --json-stream --param-file $s CP/optimization.mzn -D "n=$n")
echo $json > "CP/test.json"

echo "solveTime: $(jq ".statistics.solveTime" "CP/test.json" | grep -v "null")"
objectiveValue=$((echo $json | jq -r ".output.default | select(. != null)") | 
awk '{
dollar = index($0, "$")

if(dollar == 0){
next
}
obj = substr($0, dollar+2 )
bracket = index(obj, "]")
print substr(obj,0,bracket -1)
}')
echo "objectiveValue: $objectiveValue"


