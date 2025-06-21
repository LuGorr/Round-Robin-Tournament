#!/bin/bash

for n in 6 8 10 12; do
    python /SMT/SMT.py $n > /res/SMT/$n.json
done