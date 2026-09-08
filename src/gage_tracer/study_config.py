"""Shared domain rules for the MSA workflows.

This module contains policy and study-design constants only. Parsers,
calculations, and presentation layers depend on these rules rather than
repeating magic numbers in separate modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class CrossedGageRRDesign:
    """Fixed crossed Gage R&R design used by this application."""

    parts: int = 10
    operators: int = 3
    trials_per_part: int = 3

    @property
    def report_blocks(self) -> int:
        return self.parts * self.operators * self.trials_per_part


GRR_DESIGN = CrossedGageRRDesign()
TYPE1_CAPABILITY_THRESHOLD = 1.33
GRR_ACCEPTABLE_PERCENT = 10.0
GRR_MARGINAL_PERCENT = 30.0
GRR_MINIMUM_NDC = 5

GageRRVerdict = Literal["PASS", "MARGINAL", "FAIL"]


def classify_gage_rr(total_grr_percent: float, ndc: int) -> GageRRVerdict:
    """Classify a crossed Gage R&R result using the application policy."""
    if total_grr_percent < GRR_ACCEPTABLE_PERCENT and ndc >= GRR_MINIMUM_NDC:
        return "PASS"
    if total_grr_percent <= GRR_MARGINAL_PERCENT and ndc >= GRR_MINIMUM_NDC:
        return "MARGINAL"
    return "FAIL"
