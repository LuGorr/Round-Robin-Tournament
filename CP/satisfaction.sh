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
matrix=$($director/CP/gen_matrix $n)
touch $directory/CP/data.dzn
echo "n=$n;simplified_mode=true;warm_start=$matrix;" > $directory/data.dzn 
sol=$(minizinc --statistics --json-stream --param-file $s $f $directory/CP/betterv2.mzn $directory/CP/data.dzn)
echo $sol
echo "preSolveTime: $(echo $sol | jq ".statistics.solveTime" | grep -v "null")"
warm_start=$(echo $sol | jq -r ".output.default | select(. != null)" | perl -pe 'if (m/^\[(.*?)\](\$|$)/) { my $c=$1; $c=~s/\[//g; $c=~s/\]//g; $_="[" . $c . "]"; } else { $_=""; }')

echo "n=$n;simplified_mode=false;warm_start=$warm_start;" > $directory/CP/data.dzn 
json=$(minizinc --statistics --json-stream --param-file $s $f $directory/CP/betterv2.mzn $directory/CP/data.dzn)

echo $json > "$directory/CP/test.json"
formatted_sol=$((echo $json | jq  ".output.default") | awk '{
    first_bracket = index($0, "[")
    if (first_bracket == 0) {
        next
    }
    rest_of_line = substr($0, first_bracket + 1)
    second_bracket_relative = index(rest_of_line, "[")
    if (second_bracket_relative == 0) {
        next
    }
    second_bracket_absolute = first_bracket + second_bracket_relative
    print substr($0, second_bracket_absolute)
}')
echo $(jq ".output.default = \"$formatted_sol" "$directory/CP/test.json") > "$directory/CP/test.json"
echo "solveTime: $(jq ".statistics.solveTime" "$directory/CP/test.json" | grep -v "null")"
rm $directory/CP/data.dzn

