from fundexpert.utils.text import turkish_upper, turkish_lower

def test_turkish_upper_empty_and_none():
    assert turkish_upper("") == ""
    assert turkish_upper(None) is None

def test_turkish_lower_empty_and_none():
    assert turkish_lower("") == ""
    assert turkish_lower(None) is None
