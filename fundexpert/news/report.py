from typing import Any
import pandas as pd
from fundexpert.select.pick import pick_top

def compute_displaced_funds(
    scored_pre: pd.DataFrame,
    picked_codes: set[str],
    hits_by_code: dict[str, list],
    n: int,
    max_per_type: int,
    max_per_sector: int,
    penalty: float,
) -> list[dict[str, Any]]:
    """Compute funds that would have been picked without the news penalty but got pushed out."""
    if not hits_by_code:
        return []
        
    scored_pre = scored_pre.sort_values(["score", "fon_kodu"], ascending=[False, True])
    would_be, _ = pick_top(
        scored_pre, n=n, max_per_type=max_per_type, max_per_sector=max_per_sector, is_sorted=True
    )
    would_be_codes = set(would_be["fon_kodu"].astype(str))
    displaced_codes = would_be_codes - picked_codes
    
    displaced: list[dict[str, Any]] = []
    scored_pre_indexed = scored_pre.set_index(scored_pre["fon_kodu"].astype(str))
    
    for code in displaced_codes:
        row = scored_pre_indexed.loc[code]
        hits = hits_by_code.get(code, [])
        displaced.append({
            "fon_kodu": code,
            "fon_adi": str(row["fon_adi"]),
            "score_pre":  float(row["score"]),
            "score_post": float(row["score"]) - penalty if hits else float(row["score"]),
            "hits": [hit.to_render_dict() for hit in hits],
        })
    
    # Sort by pre-penalty score descending: the strongest fund we lost appears first.
    displaced.sort(key=lambda d: d["score_pre"], reverse=True)
    return displaced
