from typing import List, Optional

from pydantic import BaseModel, Field


class Mobility(BaseModel):
    max_distance_km: Optional[float] = None


class BeneficiaryProfile(BaseModel):
    education: Optional[str] = None
    occupation: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    mobility: Mobility = Field(default_factory=Mobility)
    employment_preference: Optional[str] = None