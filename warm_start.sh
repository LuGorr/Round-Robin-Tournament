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
if [ ! -s "gen_matrix.out" ]; then
  g++ gen_matrix.c -o gen_matrix.out
fi
matrix=$(./gen_matrix.out $n)
touch data.dzn
echo "n=$n;simplified_mode=true;warm_start=$matrix;" > data.dzn 
sol=$(minizinc --disable-warnings --statistics --json-stream --param-file $s  --solver-time-limit 300000 CP/warm_start.mzn data.dzn)
if [ "$(echo "$sol" | jq -r 'select(.type == "status") | .status')" == "UNSATISFIABLE" ]; then
  formatted_sol="[]";
  optimal="true";
  if [ "$(echo $s | grep "coinbc")" != "" -o "$(echo $s | grep "ortools")" != "" ]; then
    solve=$(echo $sol | jq -r ".statistics.solveTime"| grep -v "null" | head -n 1)
  else
    solve=$(echo $sol | jq -r ".statistics.solveTime"| grep -v "null")
  fi
  
elif [ "$(echo "$sol" | jq -r 'select(.type == "status") | .status')" == "UNKNOWN" ]; then
  formatted_sol="[]";
  solve="300";
  optimal="false";
else
  if [ "$(echo $s | grep "coinbc")" != "" -o "$(echo $s | grep "ortools")" != "" ]; then
    presolve=$(echo $sol | jq ".statistics.solveTime" | grep -v "null" | head -n 1);
  else
    presolve=$(echo $sol | jq ".statistics.solveTime" | grep -v "null");
  fi
  warm_start=$(echo $sol | jq -r ".output.default | select(. != null)" | perl -pe 'if (m/^\[(.*?)\](\$|$)/) { my $c=$1; $c=~s/\[//g; $c=~s/\]//g; $_="[" . $c . "]"; } else { $_=""; }');
  optimal="false";
  echo "n=$n;simplified_mode=false;warm_start=$warm_start;" > data.dzn ;
  remaining=$(echo 300000-$presolve | bc -l);
  json=$(minizinc --disable-warnings --statistics --json-stream --param-file $s --solver-time-limit $remaining CP/warm_start.mzn data.dzn);

#echo $json > "CP/test.json"
  formatted_sol=$((echo $json | jq  '.output.default | select(. != null)') | awk '{
  first_bracket = index($0, "$") + 1
  tmp = substr($0, first_bracket)
  last_bracket = length(tmp)-1
  print substr(tmp, 0, last_bracket)
  }');
  if [ "$(echo $s | grep "coinbc")" != "" -o "$(echo $s | grep "ortools")" != "" ]; then
    solve=$(echo $json | jq -r ".statistics.solveTime"| grep -v "null" | head -n 1)
  else
    solve=$(echo $json | jq -r ".statistics.solveTime"| grep -v "null")
  fi 
fi
file_path="../../res/CP/"$n".json"

solver="${s#solver-configs/}"
solver="${solver%.mpc}"

if [ -s $file_path ]; then 
truncate -s -2 $file_path; 
echo ",">> $file_path; else
echo "{">> $file_path;  fi
echo '    "warm-start-'"$solver"-n-"$n\":{" >> $file_path
echo '        "time":'$(echo "scale=0; ("$solve")/1" | bc )','>> $file_path
echo '        "optimal":'$optimal','>> $file_path
echo '        "obj": "None",'>> $file_path
echo '        "sol": '$formatted_sol>> $file_path
echo '    }'>> $file_path
echo '}'>> $file_path
rm data.dzn

