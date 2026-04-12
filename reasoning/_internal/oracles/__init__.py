"""
Oracle providers for probability generation.

Internal module - customers should not import from here directly.
Use UniversalPredictionEngine instead.
"""

from .interface import OracleProvider, OracleResult

__all__ = ["OracleProvider", "OracleResult"]
