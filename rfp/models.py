from datetime import date
from math import isclose

from pydantic import BaseModel, ConfigDict, Field


class Criterion(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, str_strip_whitespace=True)
    criterion_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=2000)
    weight: float = Field(ge=0, le=100)
    max_score: float = Field(gt=0, le=1000)
    is_active: bool = True


class Supplier(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)
    supplier_name: str = Field(min_length=1, max_length=120)
    submission_date: date
    experience_rating: float = Field(ge=0, le=10)


class CriterionResult(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    criterion_id: int
    score: float = Field(ge=0)
    max_score: float = Field(gt=0)
    justification: str
    evidence: str
    evidence_page: int | None = None
    evidence_verified: bool = False
    warnings: list[str] = Field(default_factory=list)


class Evaluation(BaseModel):
    supplier_name: str
    criteria: list[CriterionResult]
    risks: list[str] = Field(default_factory=list)
    overall_summary: str
    warnings: list[str] = Field(default_factory=list)


def active_criteria(criteria: list[Criterion]) -> list[Criterion]:
    active = [c for c in criteria if c.is_active]
    if not active or not any(c.weight > 0 for c in active):
        raise ValueError("Activate at least one criterion with a positive weight.")
    if len({c.criterion_id for c in criteria}) != len(criteria):
        raise ValueError("Criterion IDs must be unique.")
    if not isclose(sum(c.weight for c in active), 100.0, abs_tol=1e-8):
        raise ValueError("Active criterion weights must total exactly 100%.")
    return sorted(active, key=lambda c: c.criterion_id)
