import pandera.pandas as pa

MergedUniverseSchema = pa.DataFrameSchema({
    "fon_kodu": pa.Column(str, coerce=True),
    "fon_adi": pa.Column(str, nullable=True, coerce=True),
    "umbrella_type": pa.Column(str, nullable=True, coerce=True),
    "risk": pa.Column(float, nullable=True, coerce=True),
    "ret_1m": pa.Column(float, nullable=True, coerce=True),
    "ret_3m": pa.Column(float, nullable=True, coerce=True),
    "ret_6m": pa.Column(float, nullable=True, coerce=True),
    "ret_ytd": pa.Column(float, nullable=True, coerce=True),
    "ret_1y": pa.Column(float, nullable=True, coerce=True),
    "ret_3y": pa.Column(float, nullable=True, coerce=True),
    "ret_5y": pa.Column(float, nullable=True, coerce=True),
    "aum_first": pa.Column(float, nullable=True, coerce=True),
    "aum_last": pa.Column(float, nullable=True, coerce=True),
    "aum_change_pct": pa.Column(float, nullable=True, coerce=True),
    "units_first": pa.Column(float, nullable=True, coerce=True),
    "units_last": pa.Column(float, nullable=True, coerce=True),
    "units_change_pct": pa.Column(float, nullable=True, coerce=True),
    "applied_management_fee_pct": pa.Column(float, nullable=True, coerce=True),
    "bylaw_management_fee_pct": pa.Column(float, nullable=True, coerce=True),
    "universe": pa.Column(str, coerce=True),
})

ScoredCandidatesSchema = MergedUniverseSchema.add_columns({
    "R": pa.Column(float, coerce=True),
    "score": pa.Column(float, coerce=True),
    "strategy": pa.Column(str, coerce=True),
    "sector": pa.Column(str, coerce=True),
})

SelectedPortfolioSchema = ScoredCandidatesSchema.add_columns({
    "display_weight_pct": pa.Column(int, coerce=True),
})
