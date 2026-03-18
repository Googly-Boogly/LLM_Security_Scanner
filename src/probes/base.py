from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.detectors.base import Detector


class Category(str, Enum):
    INJECTION = "injection"
    JAILBREAK = "jailbreak"
    LEAKAGE = "leakage"
    HARMFUL = "harmful"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


SEVERITY_WEIGHTS: dict[Severity, float] = {
    Severity.CRITICAL: 3.0,
    Severity.HIGH: 2.0,
    Severity.MEDIUM: 1.0,
    Severity.LOW: 0.5,
}


@dataclass
class Probe:
    name: str
    category: Category
    description: str
    severity: Severity
    system_prompt: str
    user_prompt: str
    # If True, probe.system_prompt is used verbatim regardless of CLI --system-prompt.
    # Injection probes need a controlled victim system prompt to test against.
    override_system_prompt: bool = False
    # Keyword-based probes set this at definition time.
    # Probes that need LLM-as-judge leave this None; Scanner injects judge detector.
    detector: Optional[Detector] = field(default=None, compare=False, repr=False)


@dataclass
class ProbeResult:
    probe: Probe
    response: str
    compromised: bool
    confidence: float   # 0.0 = definitely safe, 1.0 = definitely compromised
    reason: str
    error: Optional[str] = None
    duration_ms: float = 0.0
