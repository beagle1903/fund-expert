import os
from datetime import datetime
from typing import Any
import numpy as np
import pandas as pd

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from fundexpert.config import DATA_ROOT, DEFAULT_MAX_PER_SECTOR, DEFAULT_MAX_PER_TYPE
from fundexpert.data.loader import load_candidates_for_universe
from fundexpert.pipeline import PipelineConfig, run_pipeline

app = FastAPI(title="Fundexpert API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    universe: str
    risk_level: str = "medium"
    horizon: str = "medium"
    volume_priority: str = "medium"
    fee_priority: str = "medium"
    momentum_priority: str = "medium"
    n: int = 8
    max_per_type: int = DEFAULT_MAX_PER_TYPE
    max_per_sector: int = DEFAULT_MAX_PER_SECTOR
    news_enabled: bool = False

_cache = {}

def get_latest_mtime(universe: str) -> float:
    folder = DATA_ROOT / universe
    mtimes = []
    for file in ["getiri.csv", "buyukluk.csv", "yonetim ucreti.csv"]:
        path = folder / file
        if path.exists():
            mtimes.append(path.stat().st_mtime)
    return max(mtimes) if mtimes else 0.0

def get_cached_candidates(universe: str) -> pd.DataFrame:
    if universe not in ("tefas", "befas"):
        raise ValueError("Invalid universe")
        
    current_mtime = get_latest_mtime(universe)
    
    if universe in _cache:
        cached_data = _cache[universe]
        if current_mtime <= cached_data["mtime"]:
            return cached_data["df"]
            
    try:
        df = load_candidates_for_universe(universe, DATA_ROOT)
        _cache[universe] = {"df": df, "mtime": current_mtime}
        return df
    except Exception as e:
        raise RuntimeError(f"Could not load data for {universe}: {e}")

@app.post("/api/generate")
def generate_portfolio(req: GenerateRequest) -> dict[str, Any]:
    try:
        candidates = get_cached_candidates(req.universe)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    config = PipelineConfig(
        universe=req.universe,
        risk_level=req.risk_level,
        horizon=req.horizon,
        volume_priority=req.volume_priority,
        fee_priority=req.fee_priority,
        momentum_priority=req.momentum_priority,
        n=req.n,
        max_per_type=req.max_per_type,
        max_per_sector=req.max_per_sector,
        now=datetime.now(),
        news_enabled=req.news_enabled,
        news_api_key=os.environ.get("TAVILY_API_KEY") if req.news_enabled else None
    )
    
    try:
        res = run_pipeline(candidates, config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Convert DataFrame to list of dicts, replacing NaN/NaT with None for JSON
    weighted_df = res.weighted.replace({np.nan: None})
    weighted_records = weighted_df.to_dict(orient="records")
    
    return {
        "weighted": weighted_records,
        "header": res.header,
        "hits_for_render": res.hits_for_render,
        "news_meta": res.news_meta
    }
