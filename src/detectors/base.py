from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class DetectionResult:
    compromised: bool
    confidence: float   # 0.0 = model refused cleanly, 1.0 = attack fully succeeded
    reason: str


@runtime_checkable
class Detector(Protocol):
    async def detect(
        self,
        system_prompt: str,
        user_prompt: str,
        response: str,
    ) -> DetectionResult: ...
