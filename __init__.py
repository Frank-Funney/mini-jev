#!/usr/bin/env python3
"""
MiniJEV - 超轻量级结构化决策引擎
版本: 1.0.0
"""

from mini_jev import MiniJEV, JevConfig, DecisionType, DecisionResult
from mini_jev import quick_decide, batch_quick_decide

__version__ = "1.0.0"
__all__ = [
    "MiniJEV",
    "JevConfig",
    "DecisionType",
    "DecisionResult",
    "quick_decide",
    "batch_quick_decide"
]
