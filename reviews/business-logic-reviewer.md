# Business Logic Review Report: `fundexpert`

## Executive Summary
The core business logic of `fundexpert` is robust and well-designed. It utilizes a sound quantitative scoring model with min-max normalization, an elegant largest-remainder weight distribution algorithm, and strict diversity caps for both strategy and sector. 

However, the review has identified several flaws that affect portfolio construction and accuracy. The most critical issue is a statistical seasonality bias in the horizon scoring mechanism (P0), followed by survivorship bias in historical return evaluations (P1) and a missing regulatory filter for retail investors (P1).

## Detailed Findings

### [P0] `ret_ytd` Introduces Seasonality Bias into the "Medium" Horizon Score
- **Location:** `fundexpert/config.py` (`DEFAULT_SCORING_CONFIG.horizon_buckets`)
- **Issue:** The `medium` bucket averages `ret_6m`, `ret_ytd`, and `ret_1y`. Because `ret_ytd` (Year-to-Date) spans a variable timeframe depending on the current date (1 month in February vs. 11 months in December), the "medium" score will exhibit heavy seasonality. This shifts the quantitative weight of recent versus historical performance based solely on the calendar month.
- **Risk:** Inconsistent scoring results across the year.

### [P1] Unintended Survivorship Bias via `skipna=False` in Horizon Means
- **Location:** `fundexpert/scoring/horizon.py` (`apply_horizon`)
- **Issue:** Averaging return columns with `skipna=False` strictly drops any fund missing *even one* metric in the bucket. For the `long` horizon (`ret_3y`, `ret_5y`), this enforces a strict 5-year track record, automatically dropping strong thematic funds that are, for example, 4.5 years old. Given the rapid expansion of the Turkish fund market, this aggressively excludes high-performing modern funds.
- **Risk:** Exclusion of competitive funds; artificial limitation of the candidate pool.

### [P1] Missing "Serbest" (Hedge Fund) Exclusion
- **Location:** `fundexpert/data/merge.py` (`clean_candidates`)
- **Issue:** The pipeline correctly filters out "OKS" (auto-enrollment pension) funds but leaves "Serbest" (Free/Hedge) funds. In Turkey, Serbest funds legally require a "Nitelikli Yatırımcı" (Qualified Investor) status (>1M TRY in assets). Retail users running this tool will receive recommendations they cannot legally purchase through their broker.
- **Risk:** Poor user experience and recommending un-investable assets to standard retail users.

### [P2] Incomplete Taxonomy for Silver ("GÜMÜŞ") Funds
- **Location:** `fundexpert/rules.json`
- **Issue:** Silver funds (containing "GÜMÜŞ" in the name) are not mapped to `precious_metals` and will bypass the cap, falling into the generic `other` bucket (or `fund_of_funds` if they contain "FON SEPETİ"). 
- **Risk:** The portfolio could inadvertently become concentrated in precious metals if multiple gold and silver funds are picked independently.

### [P2] IDNA (Punycode) Bypass in News Domain Exclusions
- **Location:** `fundexpert/news/tavily.py` (`_is_excluded`)
- **Issue:** The client-side filter checks for `"portföy"` in the hostname. If an issuer domain actually uses the Turkish character (e.g., `akportföy.com.tr`), `urllib.parse` resolves its hostname to its punycode equivalent (`xn--akportfy-t4a.com.tr`). The substring check will fail to match `"portföy"`.
- **Risk:** Minor edge case where issuer-owned domains using non-ASCII characters might bypass the exclusion filter.

---

## Recommended Fixes

1. **Fix Seasonality Bias:** Update `config.py` to remove `ret_ytd` from the `medium` horizon bucket, sticking to fixed-window metrics like `("ret_6m", "ret_1y")`.
2. **Loosen Survivorship Restrictions:** Update `horizon.py` to use `df[cols].mean(axis=1, skipna=True)` while ensuring a minimum track record by verifying that at least the shortest period in the bucket exists (e.g., `if not df[cols[0]].isna()`).
3. **Filter Qualified-Investor Funds:** Add a regex filter to `clean_candidates` in `merge.py` to exclude funds with `\bSERBEST\b` in their name or umbrella type, mirroring the `OKS` exclusion. Alternatively, make this a configurable CLI flag.
4. **Update Strategy Caps:** Add `["GÜMÜŞ", "precious_metals"]` to `bucket_rules` in `rules.json`.
5. **Robust Exclusions:** Rely primarily on the ASCII `"portfoy"` substring in `NEWS_EXCLUDED_DOMAIN_SUBSTRINGS` (which is already implemented and covers 99% of instances) or decode punycode in `_is_excluded` before doing the substring check.
