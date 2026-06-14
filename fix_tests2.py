
with open("tests/test_news_penalty.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip_next = False
skip_count = 0

for i, line in enumerate(lines):
    if skip_count > 0:
        skip_count -= 1
        continue
    if skip_next:
        skip_next = False
        continue
    
    # Replace executor fixture
    if "import concurrent.futures" in line:
        new_lines.append("from fundexpert.config import NewsConfig\n")
        continue
    if "@pytest.fixture" in line and i+1 < len(lines) and "def executor():" in lines[i+1]:
        skip_count = 4
        continue
        
    if "def test_" in line:
        line = line.replace(", executor", "")
        new_lines.append(line)
        continue
        
    if "apply_negative_news_penalty(" in line:
        new_lines.append(line)
        continue
        
    if "executor=executor" in line:
        df_var = line.strip().split(",")[0]
        top_k = line.split("top_k=")[1].split(",")[0]
        
        next_line = lines[i+1]
        api_key = next_line.split("api_key=")[1].split(",")[0]
        
        domains_str = ""
        if i+2 < len(lines) and "allowed_domains=" in lines[i+2]:
            domains_str = ", allowed_domains=(\"dunya.com\", \"kap.org.tr\"), excluded_domain_substrings=(\"portfoy\",)"
            skip_count = 3 # skip next_line, domains_line, excluded_line
        else:
            skip_count = 1 # skip next_line
            
        new_line = f"        {df_var}, top_k={top_k}, api_key={api_key}, news_config=NewsConfig(keywords=(\"ceza\",), penalty=0.20, cache_dir=cache_dir{domains_str}),\n"
        new_lines.append(new_line)
        continue
        
    new_lines.append(line)

with open("tests/test_news_penalty.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

