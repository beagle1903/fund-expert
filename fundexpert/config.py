"""Tunable constants for fundexpert. One file changes calibrate everything."""

from pathlib import Path

# --- Scoring constants --------------------------------------------------------

# Low/Med/High user priorities map to scalar weights, then re-normalized in score.py
PRIORITY_WEIGHTS: dict[str, float] = {
    "low": 0.10,
    "medium": 0.30,
    "high": 0.60,
}

# λ multiplier for the SRRI risk penalty: penalty = λ · ((risk - 1)/6)²
# Keyed by user's *desired* risk level: "low" = wants safe funds, big penalty;
# "high" = wants risky funds, almost no penalty.
RISK_LEVEL_LAMBDAS: dict[str, float] = {
    "low": 0.60,
    "medium": 0.25,
    "high": 0.05,
}

# Horizon → return columns averaged for the primary return signal
HORIZON_BUCKETS: dict[str, tuple[str, ...]] = {
    "short":  ("ret_1m", "ret_3m"),
    "medium": ("ret_6m", "ret_ytd", "ret_1y"),
    "long":   ("ret_3y", "ret_5y"),
}

# --- Selection constants ------------------------------------------------------

DEFAULT_MAX_PER_TYPE: int = 2

# Per-sector cap. "diversified" sector (no sector keyword in name) is exempt.
DEFAULT_MAX_PER_SECTOR: int = 2

WEIGHT_EPSILON: float = 0.01  # shift used by select/weights.py to avoid zero weights
WEIGHT_STEP_PCT: int = 5

MAX_CSV_SIZE_BYTES: int = 50 * 1024 * 1024
# --- News pass (optional, opt-in via --news) ---------------------------------

# Env var holding the Tavily search API key. Never accept the key as a CLI arg
# (it would persist in shell history). Missing/empty → news pass is skipped
# with a stderr warning, picks fall back to pure quant ranking.
NEWS_API_KEY_ENV: str = "TAVILY_API_KEY"

# Top-K candidates by quant score get a Tavily query. Bounded as `multiplier · n`
# so query count stays small (e.g. n=5 → top 15 funds queried, not all ~1000).
NEWS_QUERY_TOP_K_MULTIPLIER: int = 3

# Tavily query parameters.
NEWS_MAX_AGE_DAYS: int = 30
NEWS_MAX_RESULTS_PER_FUND: int = 3
NEWS_QUERY_TIMEOUT_SECONDS: int = 10

# Negative-keyword OR-list interpolated into the Tavily query string.
# Conservative starter set — false positives are worse than misses here.
# See todos.md "News pass — possible enhancements" for broader options.
NEGATIVE_NEWS_KEYWORDS: tuple[str, ...] = (
    "soruşturma", "dolandırıcılık", "iflas", "dava",
    "ceza", "fesih", "suspansiyon", "kapatma", "şikayet",
)

# Fixed binary deduction from a fund's score when Tavily returns ≥1 hit.
NEGATIVE_NEWS_PENALTY: float = 0.20

# Trusted Turkish financial/business news outlets. Forwarded to Tavily as
# include_domains, restricting search server-side. Empty tuple → no
# restriction (broad search; not recommended — Spotify/Instagram/forum
# results were the main false-positive driver before this list existed).
NEWS_DOMAIN_ALLOWLIST: tuple[str, ...] = (
    # Regulators / authoritative
    "kap.org.tr",
    "spk.gov.tr",
    # Business specialists
    "dunya.com",
    "bloomberght.com",
    "ekonomim.com",
    "paraanaliz.com",
    "fortuneturkey.com",
    # Business sections of major dailies
    "bigpara.hurriyet.com.tr",
    "ntv.com.tr",
    "haberturk.com",
    "sozcu.com.tr",
    "cumhuriyet.com.tr",
    "t24.com.tr",
    # News agencies
    "aa.com.tr",
    "reuters.com",
)

# Hostname substrings (case-insensitive) that drop a hit client-side
# regardless of the allowlist. Issuer-owned domains (Turkish portföy
# companies all use *portfoy*.com.tr) won't publish negative news about
# their own funds, so any hit from them is structurally untrustworthy.
NEWS_EXCLUDED_DOMAIN_SUBSTRINGS: tuple[str, ...] = ("portfoy", "portföy")

# Disk cache for Tavily responses. Re-runs within TTL skip the network.
NEWS_CACHE_DIR: Path = Path.home() / ".fundexpert" / "news_cache"
NEWS_CACHE_TTL_SECONDS: int = 3600

# --- Paths -------------------------------------------------------------------

LAST_RUN_FILE: Path = Path.home() / ".fundexpert" / "last.json"

HISTORY_DIR: Path = Path.home() / ".fundexpert" / "runs"
