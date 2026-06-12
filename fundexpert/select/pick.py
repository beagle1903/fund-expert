"""Top-N selection with per-strategy and per-sector caps, never silently relaxed."""

import pandas as pd


def pick_top(
    scored: pd.DataFrame,
    n: int,
    max_per_type: int,
    max_per_sector: int | None = None,
) -> tuple[pd.DataFrame, str | None]:
    """Return (selected_rows, warning_or_None).

    Walks scored rows in descending score order. Skips a candidate when:
    - its `strategy` bucket has hit `max_per_type`, or
    - its `sector` bucket has hit `max_per_sector` (sector "diversified" is
      exempt — most non-themed funds live there and shouldn't be capped).

    The sector cap is only applied when `max_per_sector` is provided AND the
    DataFrame has a `sector` column, so existing callers keep working unchanged.
    """
    sorted_df = scored.sort_values(["score", "fon_kodu"], ascending=[False, True])
    strat_counts: dict[str, int] = {}
    sector_counts: dict[str, int] = {}
    selected_indices: list = []

    apply_sector_cap = max_per_sector is not None and "sector" in sorted_df.columns

    for row in sorted_df.itertuples(index=True, name='Row'):
        idx = row.Index
        if len(selected_indices) >= n:
            break
        bucket = row.strategy
        if strat_counts.get(bucket, 0) >= max_per_type:
            continue
        if apply_sector_cap:
            sector = getattr(row, "sector")
            if sector != "diversified" and sector_counts.get(sector, 0) >= max_per_sector:
                continue
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        selected_indices.append(idx)
        strat_counts[bucket] = strat_counts.get(bucket, 0) + 1

    out = sorted_df.loc[selected_indices].reset_index(drop=True)

    if len(out) < n:
        if len(out) == 0:
            warning = "Aday havuzu boş — portföy oluşturulamadı."
        else:
            warning = (
                f"Picked {len(out)} of requested {n} — "
                f"no further fund of a different strategy/sector qualified."
            )
        return out, warning
    return out, None
