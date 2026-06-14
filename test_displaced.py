import pandas as pd
from fundexpert.select.pick import pick_top
from fundexpert.news.report import compute_displaced_funds

scored_pre = pd.DataFrame([
    {"fon_kodu": "Z", "fon_adi": "Z Fund", "score": 0.99, "strategy": "S2", "sector": "A"},
    {"fon_kodu": "Y", "fon_adi": "Y Fund", "score": 0.90, "strategy": "S1", "sector": "A"},
    {"fon_kodu": "X", "fon_adi": "X Fund", "score": 0.80, "strategy": "S1", "sector": "B"},
    {"fon_kodu": "W", "fon_adi": "W Fund", "score": 0.70, "strategy": "S3", "sector": "C"},
])

class DummyHit:
    def to_render_dict(self): return {"title": "bad"}

hits_by_code = {"Z": [DummyHit()]}
scored_post = scored_pre.copy()
scored_post.loc[scored_post["fon_kodu"] == "Z", "score"] = 0.50

picked, _ = pick_top(scored_post, n=2, max_per_type=1, max_per_sector=1)
picked_codes = set(picked["fon_kodu"])
print("Picked:", picked_codes)

displaced = compute_displaced_funds(
    scored_pre, picked_codes, hits_by_code, n=2, max_per_type=1, max_per_sector=1, penalty=0.49
)
print("Displaced:")
for d in displaced:
    print(d)
