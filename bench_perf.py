from datetime import datetime
from fundexpert.pipeline import run_pipeline, PipelineConfig
from fundexpert.config import DEFAULT_MAX_PER_TYPE
from fundexpert.data.loader import load_candidates_for_universe
from pathlib import Path
import pandas as pd
import sys

def main():
    root = Path('data')
    df = load_candidates_for_universe('tefas', root)
    cfg = PipelineConfig(
        universe='tefas',
        risk_level='medium',
        horizon='medium',
        volume_priority='medium',
        fee_priority='medium',
        n=8,
        max_per_type=DEFAULT_MAX_PER_TYPE,
        now=datetime.now()
    )
    for _ in range(10): # run multiple times to magnify bottlenecks
        run_pipeline(df, cfg)

if __name__ == '__main__':
    main()
