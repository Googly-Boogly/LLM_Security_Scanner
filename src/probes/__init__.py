"""Probe registry — returns all probes, optionally filtered by category."""
from __future__ import annotations

from src.probes.base import Category, Probe
from src.probes.injection import PROBES as INJECTION_PROBES
from src.probes.jailbreak import PROBES as JAILBREAK_PROBES
from src.probes.leakage import PROBES as LEAKAGE_PROBES
from src.probes.harmful import PROBES as HARMFUL_PROBES

_ALL_PROBES: list[Probe] = (
    INJECTION_PROBES + JAILBREAK_PROBES + LEAKAGE_PROBES + HARMFUL_PROBES
)


def get_probes(categories: list[Category] | None = None) -> list[Probe]:
    """Return probes, optionally filtered to the specified categories."""
    if categories is None:
        return list(_ALL_PROBES)
    cat_set = set(categories)
    return [p for p in _ALL_PROBES if p.category in cat_set]


__all__ = ["get_probes", "Category", "Probe"]
