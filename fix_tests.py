
import re

path = "tests/test_news_penalty.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# remove executor fixture
text = re.sub(r"import concurrent\.futures.*?yield exc\n\n\n", "from fundexpert.config import NewsConfig\n\n", text, flags=re.DOTALL)

# remove executor from test function arguments
text = re.sub(r", executor\):", "):", text)

# Function to rewrite the call
def rewrite_call(match):
    # original captured arguments string
    args_str = match.group(1)
    
    # We want to remove:
    # executor=executor, keywords=..., penalty=..., cache_dir=...
    # allowed_domains=..., excluded_domain_substrings=...
    # and construct a news_config object instead.
    
    df_match = re.search(r"^\s*([a-zA-Z0-9_]+),", args_str)
    top_k_match = re.search(r"top_k=([0-9]+)", args_str)
    api_key_match = re.search(r"api_key=([^,]+)", args_str)
    cache_dir_match = re.search(r"cache_dir=([^,]+)", args_str)
    
    df = df_match.group(1) if df_match else "scored"
    top_k = top_k_match.group(1) if top_k_match else "5"
    api_key = api_key_match.group(1) if api_key_match else "\"k\""
    cache_dir = cache_dir_match.group(1) if cache_dir_match else "cache_dir"
    
    config_args = f"keywords=(\"ceza\",), penalty=0.20, cache_dir={cache_dir}"
    if "allowed_domains" in args_str:
        config_args += ", allowed_domains=(\"dunya.com\", \"kap.org.tr\"), excluded_domain_substrings=(\"portfoy\",)"
        
    return f"apply_negative_news_penalty(\n        {df}, top_k={top_k}, api_key={api_key}, news_config=NewsConfig({config_args})\n    )"

# Regex to match the apply_negative_news_penalty call and its arguments up to the closing parenthesis
text = re.sub(r"apply_negative_news_penalty\((.*?)\)", rewrite_call, text, flags=re.DOTALL)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

