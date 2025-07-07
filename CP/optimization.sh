#!/bin/bash

directory=$(pwd)

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
#json=$(minizinc --statistics --json-stream --solver-time-limit 300000 --param-file $s $directory/CP/optimization.mzn -D "n=$n")
json=$(minizinc --disable-warnings --statistics --json-stream --param-file $s --solver-time-limit 300000 $directory/CP/optimization.mzn -D "n=$n")


if [ "$(echo "$json" | jq -r 'select(.type == "status") | .status')" == "UNSATISFIABLE" ]; then
  formatted_sol="[]";
  optimal="true";
  if [ "$(echo $s | grep "coinbc")" != "" -o "$(echo $s | grep "ortools")" != "" ]; then
    solve=$(echo $json | jq -r ".statistics.solveTime"| grep -v "null" | head -n 1)
  else
    solve=$(echo $json | jq -r ".statistics.solveTime"| grep -v "null")
  fi
  objectiveValue="None"
elif [ "$(echo "$json" | jq -r 'select(.type == "status") | .status')" == "UNKNOWN" ]; then
  formatted_sol="[]";
  solve="300";
  optimal="false";
  objectiveValue='"None"'
else
  optimal="true"
  #formatted_sol=$(echo $json | jq   '.output.default | select(. != null)');
  #formatted_sol="${formatted_sol#\"}";
  #formatted_sol="${formatted_sol%\"}";
  if [ "$(echo $s | grep "coinbc")" != "" -o "$(echo $s | grep "ortools")" != "" ]; then
    solve=$(echo $json | jq -r ".statistics.solveTime"| grep -v "null" | head -n 1)
  else
    
    solve=$(echo $json | jq -r ".statistics.solveTime"| grep -v "null")
    
  fi

  formatted_sol=$(echo $json | jq -r ".output.default | select(. != null)" | awk '{
  bracket_open = index($0, "[") + 1
  dollar = index($0, "$") - 2
  print(substr($0, bracket_open, dollar-1))}')
  objectiveValue=$((echo $json | jq -r ".output.default | select(. != null)") | 
  awk '{
  dollar = index($0, "$")

  if(dollar == 0){
  next
  }
  obj = substr($0, dollar+2 )
  bracket = index(obj, "]")
  print substr(obj,0,bracket -1)
  }'); fi

file_path="$directory/res/CP/"$n".json"
solver="${s#solver-configs/}"
solver="${solver%.mpc}"
if [  -s $file_path ]; then 
truncate -s -2 $file_path; 
echo ",">> $file_path; else
echo "{">> $file_path;  fi
echo '    "optimal-'"$solver"-n-"$n\":{" >> $file_path
echo '        "time":'$(echo "scale=0; ("$solve")/1" | bc )','>> $file_path
echo '        "optimal":'$optimal','>> $file_path
echo '        "obj":'$objectiveValue','>> $file_path
echo '        "sol": '$formatted_sol>> $file_path
echo '    }'>> $file_path
echo '}'>> $file_path


