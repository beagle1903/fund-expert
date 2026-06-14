import pandas as pd

def turkish_upper(text: str) -> str:
    """Uppercase a string using Turkish rules (i -> İ, ı -> I)."""
    if not text:
        return text if text is None else ""
    return str(text).translate(str.maketrans("iı", "İI")).upper()

def turkish_lower(text: str) -> str:
    if not text:
        return text if text is None else ""
    return str(text).translate(str.maketrans("İI", "iı")).lower()

def turkish_upper_series(series: pd.Series) -> pd.Series:
    """Vectorized Turkish uppercase normalization for a Pandas Series."""
    # Using list comprehension per Performance Reviewer for reduced intermediate string allocations
    tr_map = str.maketrans("iı", "İI")
    return pd.Series([
        str(name).translate(tr_map).upper() if pd.notna(name) else ""
        for name in series
    ], index=series.index)
