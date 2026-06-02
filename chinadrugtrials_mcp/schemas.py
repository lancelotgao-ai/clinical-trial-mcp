"""Pydantic schemas and Enums for tool inputs and outputs."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class DrugType(str, Enum):
    ALL = ""
    TCM = "中药/天然药物"
    CHEMICAL = "化学药物"
    BIOLOGICAL = "生物制品"


class TrialStatus(str, Enum):
    ALL = ""
    ONGOING = "进行中"
    NOT_RECRUITING = "尚未招募"
    RECRUITING = "招募中"
    RECRUITMENT_COMPLETE = "招募完成"
    COMPLETED = "已完成"
    VOLUNTARILY_SUSPENDED = "主动暂停"
    VOLUNTARILY_TERMINATED = "主动终止"
    IEC_SUSPENDED = "IEC/IRB暂停"
    IEC_TERMINATED = "IEC/IRB终止"
    MANDATORY_SUSPENDED = "责令暂停"
    MANDATORY_TERMINATED = "责令终止"


class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"


# --- Tool Input Models ---

class SearchTrialsInput(BaseModel):
    """Input for searching clinical trials on the China Drug Trials platform."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    drugs_name: Optional[str] = Field(default=None, description="Drug name to search (e.g., 'PD-1', '阿托伐他汀钙片')")
    reg_no: Optional[str] = Field(default=None, description="Registration number (e.g., 'CTR20261395'). Exact or partial match.")
    indication: Optional[str] = Field(default=None, description="Indication/disease area (e.g., '肺癌', '糖尿病')")
    case_no: Optional[str] = Field(default=None, description="Protocol/trial case number")
    drugs_type: Optional[DrugType] = Field(default=DrugType.ALL, description="Drug type: empty=all, '中药/天然药物', '化学药物', '生物制品'")
    appliers: Optional[str] = Field(default=None, description="Sponsor/applicant company name (e.g., '恒瑞')")
    researchers: Optional[str] = Field(default=None, description="Principal investigator name")
    agencies: Optional[str] = Field(default=None, description="Clinical trial site/institution name")
    state: Optional[TrialStatus] = Field(default=TrialStatus.ALL, description="Trial status filter")
    communities: Optional[str] = Field(default=None, description="Ethics committee / IRB name")
    page: int = Field(default=1, description="Page number (1-based)", ge=1, le=100)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format: 'markdown' or 'json'")


class GetTrialDetailInput(BaseModel):
    """Input for getting detailed trial information."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    reg_no: str = Field(..., description="Trial registration number (e.g., 'CTR20261395')", min_length=1)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format: 'markdown' or 'json'")


class GetStatisticsInput(BaseModel):
    """Input for getting trial statistics."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format: 'markdown' or 'json'")
