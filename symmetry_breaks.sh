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

json=$(minizinc --disable-warnings --statistics --json-stream --param-file $s --solver-time-limit 300000 CP/symmetry_breaks.mzn -D "n=$n")
if [ "$(echo "$json" | jq -r 'select(.type == "status") | .status')" == "UNSATISFIABLE" ]; then
  formatted_sol="[]";
  optimal="true";
  if [ "$(echo $s | grep "coinbc")" != "" ]; then
    solve=$(echo $json | jq -r ".statistics.solveTime"| grep -v "null" | head -n 1)
  else
    solve=$(echo $json | jq -r ".statistics.solveTime"| grep -v "null")
  fi
elif [ "$(echo "$json" | jq -r 'select(.type == "status") | .status')" == "UNKNOWN" ]; then
  formatted_sol="[]";
  solve="300";
  optimal="false";
else
  formatted_sol=$(echo $json | jq   '.output.default | select(. != null)' | awk '{
  first_bracket = index($0, "$") + 1
  tmp = substr($0, first_bracket)
  last_bracket = length(tmp)-1
  print substr(tmp, 0, last_bracket)
  }');
  optimal="true";
  if [ "$(echo $s | grep "coinbc")" != "" ]; then
    solve=$(echo $json | jq -r ".statistics.solveTime"| grep -v "null" | head -n 1)
  else
    solve=$(echo $json | jq -r ".statistics.solveTime"| grep -v "null")
  fi 
fi;
  

file_path="../../res/CP/"$n".json"


solver="${s#solver-configs/}"
solver="${solver%.mpc}"

if [  -s $file_path ]; then 
truncate -s -2 $file_path; 
echo ",">> $file_path; else
echo "{">> $file_path;  fi
echo '    "symmetry_breaks-'"$solver"-n-"$n\":{" >> $file_path
echo '        "time":'$(echo "scale=0; ("$solve")/1" | bc )','>> $file_path
echo '        "optimal":'$optimal','>> $file_path
echo '        "obj": "None",'>> $file_path
echo '        "sol": '$formatted_sol>> $file_path
echo '    }'>> $file_path
echo '}'>> $file_path