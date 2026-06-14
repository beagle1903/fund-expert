import timeit
import pandas as pd
from fundexpert.select.strategy import bucket_from_name

df = pd.DataFrame({"fon_adi_upper": ["İŞ PORTFÖY TEKNOLOJİ KARMA FON", "AK PORTFÖY HİSSE SENEDİ", "", "GARANTİ PARA PİYASASI"] * 1000})

def test_map():
    return df["fon_adi_upper"].map(bucket_from_name)

print("Map:", timeit.timeit(test_map, number=100))
