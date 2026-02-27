import pandas as pd
import json

with open(str(Path.home()) + '/Documents/GitHub/research/code/analysis/results/deep_otm_puts.json', 'r') as f:
    results = json.load(f)

print(results.keys())
