import timeit
import pandas as pd
import numpy as np
import re

df = pd.DataFrame({"fon_adi": ["GARANTI PORTFOY OKS FON", "AK PORTFOY", "IS BANKASI OKS DEGISKEN", "YAPI KREDI"] * 1000})

def test_regex():
    return df["fon_adi"].str.contains(r"\bOKS\b", case=False, na=False, regex=True)

def test_compiled():
    pat = re.compile(r"\bOKS\b", re.IGNORECASE)
    return df["fon_adi"].apply(lambda x: bool(pat.search(x)))

def test_list_comp():
    pat = re.compile(r"\bOKS\b", re.IGNORECASE)
    return [bool(pat.search(x)) for x in df["fon_adi"]]

def test_string():
    return [" OKS " in f" {x} " for x in df["fon_adi"]]

print("Regex pandas:", timeit.timeit(test_regex, number=100))
print("Compiled apply:", timeit.timeit(test_compiled, number=100))
print("List comp:", timeit.timeit(test_list_comp, number=100))
print("String match:", timeit.timeit(test_string, number=100))
