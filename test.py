def test():
    tr_map = str.maketrans("iı", "İI")
    res = "hisse senedi yatırımı".translate(tr_map).upper()
    with open("test.txt", "w", encoding="utf-8") as f:
        f.write(res)
test()
