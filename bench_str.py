import timeit
import pandas as pd

df = pd.DataFrame({"fon_adi": ["İş Portföy Teknoloji Karma Fon", "Ak Portföy Hisse Senedi", None, "Garanti Para Piyasası"] * 1000})

def test_pandas_chain():
    tr_map = str.maketrans("iı", "İI")
    return df["fon_adi"].fillna("").str.translate(tr_map).str.upper()

def test_list_comp():
    tr_map = str.maketrans("iı", "İI")
    # need to return a series to match output type
    return pd.Series([
        str(name).translate(tr_map).upper() if pd.notna(name) else ""
        for name in df["fon_adi"]
    ], index=df.index)

print("Pandas chain:", timeit.timeit(test_pandas_chain, number=100))
print("List comp:", timeit.timeit(test_list_comp, number=100))
