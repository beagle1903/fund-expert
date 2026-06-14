import pandas as pd
import time
import string

# Create a sample dataframe
data = ["ATA PORTFÖY ÇOKLU VARLIK DEĞİŞKEN FON" + str(i) + "i ı" for i in range(1500)]
s = pd.Series(data)

t0 = time.time()
for _ in range(100):
    res1 = (
        s
        .fillna("")
        .str.replace("i", "İ", regex=False)
        .str.replace("ı", "I", regex=False)
        .str.upper()
    )
t1 = time.time()

t2 = time.time()
trans_table = str.maketrans({"i": "İ", "ı": "I"})
for _ in range(100):
    res2 = s.fillna("").map(lambda x: x.translate(trans_table).upper())
t3 = time.time()

print(f"Pandas .str methods: {t1 - t0:.4f} sec")
print(f"Map with translate: {t3 - t2:.4f} sec")
print(f"Equal? {(res1 == res2).all()}")
