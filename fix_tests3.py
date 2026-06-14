
path = "tests/test_news_penalty.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("keywords=(\"ceza\",)", "negative_news_keywords=(\"ceza\",)")
text = text.replace("penalty=0.20", "negative_news_penalty=0.20")
text = text.replace("allowed_domains=", "domain_allowlist=")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

