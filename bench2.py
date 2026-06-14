import pandas as pd
import time
import json
from pathlib import Path
from fundexpert.select.strategy import bucket_from_name

with open("fundexpert/rules.json", encoding="utf-8") as f:
    rules = json.load(f)["bucket_rules"]

data = ["ATA PORTFÖY ÇOKLU VARLIK DEĞİŞKEN FON " + str(i) for i in range(1500)]
s = pd.Series(data)

t0 = time.time()
for _ in range(100):
    res1 = s.map(bucket_from_name)
t1 = time.time()

print(f"Map bucket_from_name: {t1 - t0:.4f} sec")
