"""Top-N selection with a per-strategy cap, never silently relaxed."""

import pandas as pd


def pick_top(
    scored: pd.DataFrame,
    n: int,
    max_per_type: int,
) -> tuple[pd.DataFrame, str | None]:
    """Return (selected_rows, warning_or_None).

    Walks scored rows in descending score order, skipping any whose strategy
    bucket is already at the cap. Stops at N picks or when the pool is exhausted.
    """
    sorted_df = scored.sort_values("score", ascending=False)
    counts: dict[str, int] = {}
    selected_indices: list = []

    for idx, row in sorted_df.iterrows():
        if len(selected_indices) >= n:
            break
        bucket = row["strategy"]
        if counts.get(bucket, 0) >= max_per_type:
            continue
        selected_indices.append(idx)
        counts[bucket] = counts.get(bucket, 0) + 1

    out = sorted_df.loc[selected_indices].reset_index(drop=True)

    if len(out) < n:
        if len(out) == 0:
            warning = "Aday havuzu boş — portföy oluşturulamadı."
        else:
            warning = (
                f"Picked {len(out)} of requested {n} — "
                f"no further fund of a different strategy qualified."
            )
        return out, warning
    return out, None
