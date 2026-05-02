"""Top-N selection with a per-umbrella-type cap, never silently relaxed."""

import pandas as pd


def pick_top(
    scored: pd.DataFrame,
    n: int,
    max_per_type: int,
) -> tuple[pd.DataFrame, str | None]:
    """Return (selected_rows, warning_or_None).

    Walks scored rows in descending score order, skipping any whose umbrella_type
    is already at the cap. Stops at N picks or when the pool is exhausted.
    """
    sorted_df = scored.sort_values("score", ascending=False)
    counts: dict[str, int] = {}
    selected_indices: list = []

    for idx, row in sorted_df.iterrows():
        if len(selected_indices) >= n:
            break
        utype = row["umbrella_type"]
        if counts.get(utype, 0) >= max_per_type:
            continue
        selected_indices.append(idx)
        counts[utype] = counts.get(utype, 0) + 1

    out = sorted_df.loc[selected_indices].reset_index(drop=True)

    if len(out) < n:
        if len(out) == 0:
            warning = "Aday havuzu boş — portföy oluşturulamadı."
        else:
            warning = (
                f"Picked {len(out)} of requested {n} — "
                f"no further fund of a different umbrella type qualified."
            )
        return out, warning
    return out, None
