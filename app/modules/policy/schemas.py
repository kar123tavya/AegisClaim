"""
AegisClaim AI - Policy Data Schemas
Pydantic models for insurance policy data.
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class PolicySection(str, Enum):
    COVERAGE = "coverage"
    EXCLUSIONS = "exclusions"
    LIMITS = "limits"
    DEFINITIONS = "definitions"
    WAITING_PERIOD = "waiting_period"
    COPAY = "copay"
    CLAIMS_PROCESS = "claims_process"
    PRE_AUTHORIZATION = "pre_authorization"
    NETWORK = "network"
    GENERAL = "general"
    SUB_LIMITS = "sub_limits"
    BENEFITS = "benefits"


class PolicyChunk(BaseModel):
    """A chunk of policy text with metadata."""
    text: str
    page_number: int = 0
    section: PolicySection = PolicySection.GENERAL
    section_title: str = ""
    chunk_id: str = ""
    relevance_score: float = 0.0


class PolicyMetadata(BaseModel):
    """Metadata extracted from a policy document."""
    policy_name: Optional[str] = None
    policy_number: Optional[str] = None
    insurer_name: Optional[str] = None
    plan_type: Optional[str] = None
    sum_insured: Optional[float] = None
    room_rent_limit: Optional[float] = None
    room_rent_limit_per_day: Optional[float] = None
    copay_percentage: Optional[float] = None
    deductible: Optional[float] = None
    waiting_period_months: Optional[int] = None
    pre_existing_waiting_years: Optional[int] = None
    coverage_start_date: Optional[str] = None
    coverage_end_date: Optional[str] = None
    total_pages: int = 0
    total_chunks: int = 0
    language: str = "eng"


class PolicyQueryResult(BaseModel):
    """Result of a semantic query against a policy."""
    query: str
    relevant_chunks: list[PolicyChunk] = Field(default_factory=list)
    answer: Optional[str] = None
    confidence: float = 0.0


class PolicyIndexStatus(BaseModel):
    """Status of the policy vector index."""
    is_indexed: bool = False
    policy_id: str = ""
    policy_name: str = ""
    total_chunks: int = 0
    embedding_model: str = ""
    index_path: str = ""
