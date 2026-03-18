"""Scanner — orchestrates running probes against the target LLM."""
from __future__ import annotations

import asyncio
import time
from typing import Optional

from src.detectors.llm_judge import LLMJudgeDetector
from src.llm_client import LLMClient
from src.probes.base import Probe, ProbeResult


class Scanner:
    """
    Runs a list of probes against a target LLM concurrently.

    Probes with detector=None (jailbreak/harmful) are evaluated by LLMJudgeDetector,
    which is constructed once using the judge_client and injected at scan time.
    """

    def __init__(
        self,
        target: LLMClient,
        judge: LLMClient,
        default_system_prompt: str = "",
        concurrency: int = 5,
    ) -> None:
        self._target = target
        self._judge_detector = LLMJudgeDetector(judge_client=judge)
        self._default_system_prompt = default_system_prompt
        self._concurrency = concurrency

    async def run(self, probes: list[Probe]) -> list[ProbeResult]:
        sem = asyncio.Semaphore(self._concurrency)
        tasks = [self._run_probe(probe, sem) for probe in probes]
        results = await asyncio.gather(*tasks)
        return list(results)

    async def _run_probe(self, probe: Probe, sem: asyncio.Semaphore) -> ProbeResult:
        async with sem:
            system_prompt = (
                probe.system_prompt
                if probe.override_system_prompt
                else self._default_system_prompt
            )
            detector = probe.detector if probe.detector is not None else self._judge_detector

            start = time.monotonic()
            try:
                response = await self._target.call(
                    system_prompt=system_prompt,
                    user_prompt=probe.user_prompt,
                )
                detection = await detector.detect(
                    system_prompt=system_prompt,
                    user_prompt=probe.user_prompt,
                    response=response,
                )
                duration_ms = (time.monotonic() - start) * 1000
                return ProbeResult(
                    probe=probe,
                    response=response,
                    compromised=detection.compromised,
                    confidence=detection.confidence,
                    reason=detection.reason,
                    duration_ms=duration_ms,
                )
            except Exception as exc:
                duration_ms = (time.monotonic() - start) * 1000
                return ProbeResult(
                    probe=probe,
                    response="",
                    compromised=False,
                    confidence=0.0,
                    reason="Probe error",
                    error=str(exc),
                    duration_ms=duration_ms,
                )
