"""Seed skill implementation for routed rustication."""

from __future__ import annotations


def build_component(params: dict, context: dict) -> dict:
    return {
        "component": "routed-rustication",
        "strategy": "segment-wise trapezoidal cutters with overlaps",
        "params": params,
        "context": context,
    }
