from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class RiskResult:
    risk_id: str
    risk_name: str
    risk_level: str
    confidence: str
    trigger_basis: List[str]
    description: str
    suggested_action: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkhourResult:
    task_tag: str
    suggested_hours: int
    confidence: str
    basis: List[str]
    note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ManpowerResult:
    total_persons: int
    confidence: str
    basis: List[str]
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReasoningOutput:
    requirement_id: str
    status: str
    risk_results: List[Dict[str, Any]]
    workhour_results: List[Dict[str, Any]]
    manpower_result: Dict[str, Any]
    confidence_summary: Dict[str, str]
    reasoning_trace: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)