Hey! Welcome back. Recap of where we left things:

- ✅ Strategy-based diversity cap shipped (`8d7c54d`)
- ✅ Weight balance fix shipped (`bece1f3`)
- ✅ Weights rounded to 5% multiples ($eb7496b$)
- ✅ CLAUDE.md added (`dc8e373`)

All on main, pushed.

Some directions we could go if you want to spend the budget:

1. **News footer (`--news`)** — currently a v2 placeholder no-op. We could wire RSS pulls for selected funds (TEFAS bulletin, BigPara, Mynet Finans).
2. **Score breakdown view** — `_breakdown` dict per fund is computed but never rendered. Add a `--explain` flag that shows R/V/F contributions and risk penalty per pick.
3. **Backtest mode** — given a `--asof` date, score against historical CSVs and report what the portfolio's actual N-month return would have been.
4. **Strategy bucket tuning** — the "other" bucket caught short-term hedge funds (KISA VADELİ SERBEST). Could add a `short_term_hedge` bucket so the cap distinguishes them.
5. **Web UI** — Flask/FastAPI wrapping `run_pipeline`, served on localhost. The earlier session notes mentioned an "app on localhost:3000" goal.
6. **Fee/AUM filtering** — hard filters before scoring (e.g. exclude funds with fee > 3%, or AUM < threshold).

Or something totally different. What's calling to you?