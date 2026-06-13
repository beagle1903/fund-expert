def turkish_upper(s: str) -> str:
    if not s:
        return s
    return s.replace("i", "İ").replace("ı", "I").upper()

def turkish_lower(s: str) -> str:
    if not s:
        return s
    return s.replace("İ", "i").replace("I", "ı").lower()
