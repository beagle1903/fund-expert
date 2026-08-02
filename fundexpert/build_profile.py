"""Validated storage for the profile consumed by the build-portfolio plugin."""

from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    ValidationError,
    field_validator,
    model_validator,
)

ProfileNumber = StrictInt | StrictFloat

DEFAULT_RISK_BANDS: dict[str, list[int]] = {
    "low": [1, 2, 3],
    "medium": [3, 4, 5],
    "medium_high": [4, 5, 6],
    "high": [5, 6, 7],
}

DEFAULT_BUILD_PROFILE: dict[str, Any] = {
    "schema_version": "1.0",
    "profile_id": "burhan-medium-high-60d",
    "universe": "tefas",
    "risk_tolerance": "medium_high",
    "allowed_risk_values": [4, 5, 6],
    "holding_period_days": 60,
    "fund_count": 6,
    "metric_weights": {
        "return": 1.0,
        "current_aum": 0.1,
        "aum_growth": 0.45,
        "units_growth": 0.6,
        "management_fee": 0.0,
    },
    "risk_penalty_weight": 0.1,
    "exclude_missing_risk": True,
    "exclude_qualified_investor_funds": True,
    "new_fund_policy": {
        "definition": "missing_1y_return",
        "growth_treatment": "neutral",
    },
    "growth_winsorization": {
        "lower_quantile": 0.05,
        "upper_quantile": 0.95,
    },
    "diversification": {
        "max_per_strategy": 2,
        "max_per_sector": 2,
    },
    "market_context": {
        "enabled": True,
        "lookback_days": 7,
        "selection_influence": "qualitative_overlay",
        "source_ids": ["garanti_bbva_yatirim"],
    },
    "audit": {
        "max_data_age_days": 3,
        "max_single_fund_weight_pct": 30,
        "target_weighted_risk_range": [4.0, 5.5],
    },
}


class BuildProfileError(RuntimeError):
    """Raised when the plugin profile cannot be loaded or saved safely."""


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MetricWeights(ContractModel):
    return_weight: ProfileNumber = Field(alias="return", ge=0)
    current_aum: ProfileNumber = Field(ge=0)
    aum_growth: ProfileNumber = Field(ge=0)
    units_growth: ProfileNumber = Field(ge=0)
    management_fee: ProfileNumber = Field(ge=0)

    @model_validator(mode="after")
    def validate_total(self) -> "MetricWeights":
        values = (
            self.return_weight,
            self.current_aum,
            self.aum_growth,
            self.units_growth,
            self.management_fee,
        )
        if any(not math.isfinite(float(value)) for value in values):
            raise ValueError("Metric weights must be finite.")
        if sum(float(value) for value in values) <= 0:
            raise ValueError("At least one metric weight must be greater than zero.")
        return self


class NewFundPolicy(ContractModel):
    definition: Literal["missing_1y_return", "missing_3m_return"]
    growth_treatment: Literal["neutral", "observed"]


class GrowthWinsorization(ContractModel):
    lower_quantile: ProfileNumber = Field(ge=0, le=1)
    upper_quantile: ProfileNumber = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_order(self) -> "GrowthWinsorization":
        if float(self.lower_quantile) >= float(self.upper_quantile):
            raise ValueError(
                "Growth winsorization must satisfy lower_quantile < upper_quantile."
            )
        return self


class Diversification(ContractModel):
    max_per_strategy: StrictInt = Field(ge=1, le=20)
    max_per_sector: StrictInt = Field(ge=1, le=20)


class MarketContext(ContractModel):
    enabled: StrictBool
    lookback_days: StrictInt = Field(ge=1, le=90)
    selection_influence: Literal["qualitative_overlay"]
    source_ids: list[StrictStr]

    @field_validator("source_ids")
    @classmethod
    def validate_sources(cls, sources: list[str]) -> list[str]:
        if any(not source for source in sources):
            raise ValueError("Market source IDs cannot be blank.")
        return sources


class AuditSettings(ContractModel):
    max_data_age_days: StrictInt = Field(ge=0, le=365)
    max_single_fund_weight_pct: ProfileNumber = Field(ge=0, le=100)
    target_weighted_risk_range: list[ProfileNumber]

    @field_validator("target_weighted_risk_range")
    @classmethod
    def validate_risk_range(
        cls,
        target_range: list[ProfileNumber],
    ) -> list[ProfileNumber]:
        if len(target_range) != 2:
            raise ValueError("Target weighted risk range needs two values.")
        low, high = (float(value) for value in target_range)
        if not 1 <= low <= high <= 7:
            raise ValueError(
                "Target weighted risk range must be ordered between 1 and 7."
            )
        return target_range


class BuildProfile(ContractModel):
    schema_version: Literal["1.0"]
    profile_id: StrictStr = Field(
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    universe: Literal["tefas", "befas"]
    risk_tolerance: Literal["low", "medium", "medium_high", "high"]
    allowed_risk_values: list[StrictInt]
    holding_period_days: StrictInt = Field(ge=1, le=3650)
    fund_count: StrictInt = Field(ge=1, le=20)
    metric_weights: MetricWeights
    risk_penalty_weight: ProfileNumber = Field(ge=0)
    exclude_missing_risk: StrictBool
    exclude_qualified_investor_funds: StrictBool
    new_fund_policy: NewFundPolicy
    growth_winsorization: GrowthWinsorization
    diversification: Diversification
    market_context: MarketContext
    audit: AuditSettings

    @field_validator("allowed_risk_values")
    @classmethod
    def validate_allowed_risk_values(cls, values: list[int]) -> list[int]:
        if not values or any(not 1 <= value <= 7 for value in values):
            raise ValueError("Allowed risk values must contain integers from 1 to 7.")
        if len(set(values)) != len(values):
            raise ValueError("Allowed risk values cannot contain duplicates.")
        return values

    @field_validator("risk_penalty_weight")
    @classmethod
    def validate_risk_penalty(cls, value: ProfileNumber) -> ProfileNumber:
        if not math.isfinite(float(value)):
            raise ValueError("Risk penalty weight must be finite.")
        return value

    @model_validator(mode="after")
    def validate_allocation_feasibility(self) -> "BuildProfile":
        max_weight = float(self.audit.max_single_fund_weight_pct)
        cap_units = int(math.floor(max_weight / 5.0))
        if cap_units * self.fund_count < 20:
            raise ValueError(
                "Fund count and maximum single-fund weight cannot form a 100% "
                "portfolio in 5% increments."
            )
        return self


class BuildProfileResponse(ContractModel):
    profile: BuildProfile
    profile_path: str
    source: Literal["saved", "default_template"]


def get_build_profile_path() -> Path:
    """Return the personal profile path used by the plugin runner."""

    configured = os.environ.get("FUND_EXPERT_STATE_DIR")
    state_dir = (
        Path(configured).expanduser()
        if configured
        else Path.home() / "Documents" / "Codex" / "Fund Expert"
    )
    return state_dir.resolve() / "profiles" / "default.json"


def _validate_profile(value: Any) -> BuildProfile:
    try:
        return BuildProfile.model_validate(value)
    except ValidationError as exc:
        raise BuildProfileError("Build-plugin profile is invalid.") from exc


def load_build_profile(
    path: Path | None = None,
) -> tuple[BuildProfile, Path, Literal["saved", "default_template"]]:
    """Load and validate the saved profile, or return the contract template."""

    profile_path = path or get_build_profile_path()
    if not profile_path.exists():
        return _validate_profile(DEFAULT_BUILD_PROFILE), profile_path, "default_template"
    try:
        value = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BuildProfileError("Build-plugin profile is unavailable or invalid.") from exc
    return _validate_profile(value), profile_path, "saved"


def save_build_profile(
    profile: BuildProfile | dict[str, Any],
    path: Path | None = None,
) -> tuple[BuildProfile, Path]:
    """Validate and atomically replace the saved plugin profile."""

    validated = _validate_profile(profile)
    profile_path = path or get_build_profile_path()
    temporary_path: Path | None = None
    try:
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=profile_path.parent,
            prefix=f".{profile_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            json.dump(
                validated.model_dump(by_alias=True, mode="json"),
                temporary,
                ensure_ascii=False,
                indent=2,
            )
            temporary.write("\n")
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, profile_path)
    except OSError as exc:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise BuildProfileError("Build-plugin profile could not be saved.") from exc
    return validated, profile_path
