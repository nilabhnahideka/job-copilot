"""The profile: everything a job application form usually asks, filled in once.

The fields come from what common application forms ask (Greenhouse, Lever,
Workday, Naukri and company career pages). Every field is optional, so the
profile can be saved half-finished; `missing_for_applying` lists what still
needs filling before the app can apply for you.

Money is in Indian rupees, in lakhs per annum (LPA): 6.5 means ₹6,50,000 a year.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

WorkMode = Literal["remote", "hybrid", "onsite"]
JobType = Literal["full_time", "internship", "contract", "part_time"]
ExperienceLevel = Literal["internship", "entry", "mid", "senior", "lead"]
YesNo = Literal["yes", "no"]
PreferNot = Literal["prefer_not_to_say"]

_Lpa = Field(default=None, ge=0, le=1000, description="Lakhs per annum")


class Personal(BaseModel):
    first_name: str = ""
    last_name: str = ""
    preferred_name: str = ""
    email: str = ""
    phone: str = Field("", description="With country code, e.g. +91 98765 43210")
    city: str = ""
    state: str = ""
    country: str = "India"
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""


class EducationEntry(BaseModel):
    degree: str = Field("", description="e.g. B.Tech, M.Sc, BCA")
    field_of_study: str = ""
    institution: str = ""
    start_year: int | None = Field(default=None, ge=1950, le=2100)
    end_year: int | None = Field(default=None, ge=1950, le=2100, description="Graduation year")
    grade: str = Field("", description="CGPA or percentage, as written on your marksheet")


class Education(BaseModel):
    entries: list[EducationEntry] = Field(default_factory=list)
    # Many Indian employers ask for school marks too.
    class_10_percentage: float | None = Field(default=None, ge=0, le=100)
    class_12_percentage: float | None = Field(default=None, ge=0, le=100)


class Work(BaseModel):
    total_experience_years: float | None = Field(default=None, ge=0, le=60)
    current_company: str = ""
    current_title: str = ""
    skills: list[str] = Field(default_factory=list, description="Your key skills, for searching")


class Preferences(BaseModel):
    """What jobs to look for. Used by job search."""

    titles: list[str] = Field(default_factory=list, description="e.g. GenAI Engineer, Backend Developer")
    locations: list[str] = Field(default_factory=list, description="Cities you'd work in")
    work_modes: list[WorkMode] = Field(default_factory=list)
    job_types: list[JobType] = Field(default_factory=list)
    experience_level: ExperienceLevel | None = None
    salary_min_lpa: float | None = _Lpa
    salary_max_lpa: float | None = _Lpa
    excluded_companies: list[str] = Field(default_factory=list, description="Never show jobs from these")


class Answers(BaseModel):
    """Standard questions that appear on most application forms."""

    notice_period_days: int | None = Field(default=None, ge=0, le=365)
    currently_serving_notice: YesNo | None = None
    last_working_day: date | None = None
    current_ctc_lpa: float | None = _Lpa
    expected_ctc_lpa: float | None = _Lpa
    willing_to_relocate: YesNo | None = None
    authorized_to_work_in_india: YesNo | None = None
    requires_visa_sponsorship: YesNo | None = Field(default=None, description="For jobs outside India")
    languages: list[str] = Field(default_factory=list, description="e.g. English, Hindi")


class Demographics(BaseModel):
    """Optional. Some forms ask; you can always answer 'prefer not to say'."""

    date_of_birth: date | None = None
    gender: Literal["female", "male", "non_binary"] | PreferNot | None = None
    disability: YesNo | PreferNot | None = None
    veteran: YesNo | PreferNot | None = Field(default=None, description="Mostly asked by US companies")


class ProfileData(BaseModel):
    personal: Personal = Field(default_factory=Personal)
    education: Education = Field(default_factory=Education)
    work: Work = Field(default_factory=Work)
    preferences: Preferences = Field(default_factory=Preferences)
    answers: Answers = Field(default_factory=Answers)
    demographics: Demographics = Field(default_factory=Demographics)

    @field_validator("preferences")
    @classmethod
    def _salary_range(cls, p: Preferences) -> Preferences:
        if (
            p.salary_min_lpa is not None
            and p.salary_max_lpa is not None
            and p.salary_min_lpa > p.salary_max_lpa
        ):
            raise ValueError("Minimum salary can't be more than maximum salary")
        return p


# (section, field, label) for everything needed before the app can apply for you.
REQUIRED_FOR_APPLYING: list[tuple[str, str, str]] = [
    ("personal", "first_name", "First name"),
    ("personal", "last_name", "Last name"),
    ("personal", "email", "Email"),
    ("personal", "phone", "Phone"),
    ("personal", "city", "City"),
    ("preferences", "titles", "Job titles you want"),
    ("preferences", "locations", "Locations"),
    ("answers", "notice_period_days", "Notice period"),
    ("answers", "expected_ctc_lpa", "Expected salary"),
]


def missing_for_applying(data: ProfileData, has_resume: bool) -> list[str]:
    missing = [] if has_resume else ["Resume"]
    for section, field, label in REQUIRED_FOR_APPLYING:
        value = getattr(getattr(data, section), field)
        if value is None or value == "" or value == []:
            missing.append(label)
    return missing
