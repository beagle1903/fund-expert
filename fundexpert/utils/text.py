"""Turkish text normalisation helpers."""

def turkish_upper(s: str) -> str:
    """Uppercase a string, mapping i/ı properly."""
    return s.replace("i", "İ").replace("ı", "I").upper()

def turkish_lower(s: str) -> str:
    """Lowercase a string, mapping İ/I properly."""
    return s.replace("I", "ı").replace("İ", "i").lower()
