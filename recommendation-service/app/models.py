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
    language_code: Optional[str] = None

    # Special beneficiary applicability signals.
    #
    # Examples:
    #   "divyangjan"
    #   "women"
    #   "youth"
    #
    # This is intentionally optional because the NQR dataset
    # may contain qualifications targeted at specific groups,
    # while most beneficiaries will have no special category.
    special_categories: List[str] = Field(
        default_factory=list
    )


class Qualification(BaseModel):
    qualification_id: str
    title: str

    description: Optional[str] = None
    sector: Optional[str] = None
    nsqf_level: Optional[float] = None
    qualification_type: Optional[str] = None

    proposed_occupation: List[str] = Field(
        default_factory=list
    )

    skills: List[str] = Field(
        default_factory=list
    )

    progression_pathway: Optional[str] = None
    status: Optional[str] = None

    is_instructor_or_trainer: bool = False

    specializations: List[str] = Field(
        default_factory=list
    )

    data_quality_flags: List[str] = Field(
        default_factory=list
    )