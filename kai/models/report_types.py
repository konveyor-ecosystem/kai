# generated by datamodel-codegen:
#   filename:  report_types.yaml
#   timestamp: 2024-07-18T07:28:17+00:00

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, RootModel


class Category(Enum):
    potential = "potential"
    optional = "optional"
    mandatory = "mandatory"


class Incident(BaseModel):
    uri: str
    message: str
    codeSnip: str = ""
    lineNumber: int = -1
    variables: Dict[str, Any] = {}


class Link(BaseModel):
    url: str
    title: str = ""


class Violation(BaseModel):
    description: str = ""
    category: Category = "potential"
    labels: List[str] = []
    incidents: List[Incident] = []
    links: List[Link] = []
    extras: Optional[str] = None
    effort: Optional[int] = None


class RuleSet(BaseModel):
    name: Optional[str] = None
    description: str = ""
    tags: Optional[List[str]] = None
    violations: Dict[str, Violation] = {}
    errors: Optional[Dict[str, str]] = None
    unmatched: Optional[List[str]] = None
    skipped: Optional[List[str]] = None


class AnalysisReport(RootModel[List[RuleSet]]):
    root: List[RuleSet] = Field(..., title="AnalysisReport")
