"""
Pydantic models used for request validation and response serialization.
Mirrors the MongoDB document shapes described in the SolSight design doc:

Panel
 ├── panel_id
 ├── location
 ├── installation_date
 ├── rated_power
 └── inspections
      ├── date
      ├── image
      ├── voltage
      ├── current
      ├── temperature
      ├── detected_defect
      ├── confidence
      └── health_score
"""
from datetime import date, datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------- Auth ----------
class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=6)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 bytes")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Panels ----------
class PanelCreate(BaseModel):
    panel_id: str = Field(..., min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    location: str = Field(..., min_length=1, max_length=120)
    installation_date: str = Field(..., description="YYYY-MM-DD")
    rated_power: float = Field(..., gt=0, le=1000, description="Rated power in watts")

    @field_validator("installation_date")
    @classmethod
    def valid_date(cls, v: str) -> str:
        try:
            d = date.fromisoformat(v)
        except ValueError:
            raise ValueError("installation_date must be YYYY-MM-DD")
        if d > date.today():
            raise ValueError("installation_date can't be in the future")
        return v


class PanelOut(PanelCreate):
    id: str
    latest_health_score: Optional[float] = None
    latest_status: Optional[str] = None
    last_inspected_at: Optional[datetime] = None
    created_at: datetime


# ---------- Inspections ----------
class OperationalData(BaseModel):
    voltage: float
    current: float
    temperature: float
    rated_power: Optional[float] = None


class DefectPrediction(BaseModel):
    label: str
    confidence: float
    all_probabilities: Dict[str, float]


class HealthPrediction(BaseModel):
    status: str  # Healthy | Warning | Critical
    health_score: float
    probabilities: Dict[str, float]


class DegradationPoint(BaseModel):
    day: int
    predicted_health: float


class InspectionResult(BaseModel):
    panel_id: str
    date: datetime
    voltage: float
    current: float
    temperature: float
    power_output: float
    expected_power: float
    performance_ratio: float
    power_loss_pct: float
    detected_defect: str
    confidence: float
    health_score: float
    status: str
    degradation_forecast: List[DegradationPoint]
    recommendation: str
    analysis_mode: Dict[str, str]


class InspectionOut(InspectionResult):
    id: str
    image_url: Optional[str] = None