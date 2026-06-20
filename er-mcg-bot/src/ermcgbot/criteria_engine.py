"""Transparent, configuration-driven admission-criteria engine.

IMPORTANT — READ THIS:
    The rules in `criteria/demo_criteria.json` are DEMONSTRATION criteria
    written for this prototype. They are NOT MCG / Milliman Care Guidelines
    content, and they are NOT a validated clinical decision-support tool.
    MCG content is proprietary and licensed.

    In a production deployment, this engine is REPLACED by (or used only as a
    thin adapter to) the licensed MCG Cite / Indicia API. The interface here
    is intentionally small so that swap is straightforward:

        engine = CriteriaEngine.from_file(path)   # demo
        engine = MCGApiEngine(api_key=...)         # production (not included)

Either way, the output is the same `ScreeningResult`, and a human (the
admitting physician) always makes the final decision.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List

from .models import MatchedCriterion, Patient, ScreeningResult

# Supported comparison operators for a single condition.
_OPERATORS: Dict[str, Callable[[Any, Any], bool]] = {
    ">=": lambda a, b: a is not None and a >= b,
    ">": lambda a, b: a is not None and a > b,
    "<=": lambda a, b: a is not None and a <= b,
    "<": lambda a, b: a is not None and a < b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "in": lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
    "exists": lambda a, b: (a is not None) == bool(b),
}


def _describe(condition: Dict[str, Any]) -> str:
    return f"{condition['field']} {condition['op']} {condition.get('value')}"


def _evaluate_condition(patient: Patient, condition: Dict[str, Any]) -> bool:
    op = condition["op"]
    if op not in _OPERATORS:
        raise ValueError(f"Unknown operator: {op!r}")
    actual = patient.get(condition["field"])
    return _OPERATORS[op](actual, condition.get("value"))


class CriteriaEngine:
    """Evaluates patients against a list of rulesets loaded from config."""

    def __init__(self, rulesets: List[Dict[str, Any]]):
        self.rulesets = rulesets

    @classmethod
    def from_file(cls, path: str) -> "CriteriaEngine":
        with open(path, "r", encoding="utf-8") as fh:
            config = json.load(fh)
        return cls(config["rulesets"])

    def _match_ruleset(self, patient: Patient, ruleset: Dict[str, Any]):
        """Return a MatchedCriterion if the ruleset fires, else None.

        A ruleset fires when ALL of its `all_of` conditions are true AND at
        least one of its `any_of` conditions is true (each group is optional).
        """
        matched_desc: List[str] = []

        all_of = ruleset.get("all_of", [])
        for cond in all_of:
            if not _evaluate_condition(patient, cond):
                return None
            matched_desc.append(_describe(cond))

        any_of = ruleset.get("any_of", [])
        if any_of:
            any_hits = [c for c in any_of if _evaluate_condition(patient, c)]
            if not any_hits:
                return None
            matched_desc.extend(_describe(c) for c in any_hits)

        # A ruleset with neither group never fires (guards against empty rules).
        if not all_of and not any_of:
            return None

        return MatchedCriterion(
            criterion_id=ruleset["id"],
            label=ruleset["label"],
            description=ruleset.get("description", ""),
            recommended_status=ruleset.get("recommended_status", "Inpatient"),
            service=ruleset.get("service", "Hospitalist"),
            matched_conditions=matched_desc,
        )

    def screen(self, patient: Patient) -> ScreeningResult:
        matches = []
        for ruleset in self.rulesets:
            match = self._match_ruleset(patient, ruleset)
            if match is not None:
                matches.append(match)
        return ScreeningResult(patient=patient, matches=matches)

    def screen_all(self, patients: List[Patient]) -> List[ScreeningResult]:
        return [self.screen(p) for p in patients]
