"""
Input Validator

Validates raw data before processing to prevent garbage-in-garbage-out.

Checks:
1. Schema validation (required fields present)
2. Data type validation
3. Value range validation
4. Data quality checks
5. Staleness validation
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationLevel(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class ValidationResult:
    """Result of input validation"""

    level: ValidationLevel
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class InputValidationReport:
    """Complete validation report for input data"""

    passed: bool
    level: ValidationLevel
    validation_results: List[ValidationResult]
    data_age_days: Optional[int] = None
    data_quality_score: float = 0.0
    summary: str = ""

    @property
    def warnings(self) -> List[ValidationResult]:
        return [r for r in self.validation_results if r.level == ValidationLevel.WARN]

    @property
    def failures(self) -> List[ValidationResult]:
        return [r for r in self.validation_results if r.level == ValidationLevel.FAIL]


class InputValidator:
    """
    Validates input data before processing.

    Prevents garbage-in-garbage-out by:
    - Checking required fields exist
    - Validating data types and ranges
    - Detecting placeholder/gibberish data
    - Checking data freshness
    """

    MIN_FIELDS = 3
    MIN_DATA_SIZE = 100  # chars
    MAX_GIBBERISH_RATIO = 0.5

    STALENESS_CEILINGS = {
        0: 1.0,  # Fresh data: no penalty
        1: 0.95,  # 1 day old: max 95% confidence
        3: 0.85,  # 3 days: max 85%
        7: 0.75,  # 1 week: max 75%
        14: 0.65,  # 2 weeks: max 65%
        30: 0.50,  # 1 month: max 50%
    }

    PLACEHOLDER_PATTERNS = [
        "xxx",
        "xxx",
        "test",
        "example",
        "sample",
        "placeholder",
        "todo",
        "tbd",
        "na",
        "n/a",
        "fill in",
        "coming soon",
        "insert",
    ]

    def validate(
        self, raw_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> InputValidationReport:
        """
        Validate input data.

        Args:
            raw_data: Customer's input data
            context: Optional context with data_age_days, etc.

        Returns:
            InputValidationReport with pass/warn/fail level
        """
        context = context or {}
        results: List[ValidationResult] = []

        # Run all validation checks
        results.extend(self._check_required_structure(raw_data))
        results.extend(self._check_data_quality(raw_data))
        results.extend(self._check_data_types(raw_data))
        results.extend(self._check_value_ranges(raw_data))
        results.extend(self._check_staleness(context))

        # Calculate overall level
        failures = [r for r in results if r.level == ValidationLevel.FAIL]
        warnings = [r for r in results if r.level == ValidationLevel.WARN]

        if failures:
            level = ValidationLevel.FAIL
            passed = False
            summary = f"Failed {len(failures)} validation checks"
        elif warnings:
            level = ValidationLevel.WARN
            passed = True
            summary = f"Passed with {len(warnings)} warnings"
        else:
            level = ValidationLevel.PASS
            passed = True
            summary = "All validation checks passed"

        # Calculate data quality score
        quality_score = self._calculate_quality_score(raw_data, context)

        # Get data age
        data_age = context.get("data_age_days")

        report = InputValidationReport(
            passed=passed,
            level=level,
            validation_results=results,
            data_age_days=data_age,
            data_quality_score=quality_score,
            summary=summary,
        )

        logger.info(f"Validation: {level.value} - {summary}")
        for r in results:
            if r.level != ValidationLevel.PASS:
                logger.warning(f"  {r.level.value.upper()}: {r.message}")

        return report

    def _check_required_structure(self, raw_data: Dict) -> List[ValidationResult]:
        """Check data has required structural elements"""
        results = []

        # Must be a dict
        if not isinstance(raw_data, dict):
            return [
                ValidationResult(
                    level=ValidationLevel.FAIL,
                    message="raw_data must be a dictionary",
                    details={"type": type(raw_data).__name__},
                )
            ]

        # Must have minimum fields
        if len(raw_data) < self.MIN_FIELDS:
            results.append(
                ValidationResult(
                    level=ValidationLevel.FAIL,
                    message=f"Too few data fields: got {len(raw_data)}, need at least {self.MIN_FIELDS}",
                    details={"field_count": len(raw_data), "required": self.MIN_FIELDS},
                )
            )

        # Must not be all empty/null
        non_null_fields = [k for k, v in raw_data.items() if v is not None and v != ""]
        if len(non_null_fields) < self.MIN_FIELDS:
            results.append(
                ValidationResult(
                    level=ValidationLevel.FAIL,
                    message=f"Too few non-empty fields: got {len(non_null_fields)}, need at least {self.MIN_FIELDS}",
                    details={"non_null_count": len(non_null_fields)},
                )
            )

        return results

    def _check_data_quality(self, raw_data: Dict) -> List[ValidationResult]:
        """Check data quality - detect placeholder/gibberish values"""
        results = []

        # Check for placeholder text in string values
        placeholder_fields = []
        for key, value in raw_data.items():
            if isinstance(value, str):
                value_lower = value.lower().strip()

                # Check for placeholder patterns
                for pattern in self.PLACEHOLDER_PATTERNS:
                    if pattern.lower() in value_lower:
                        placeholder_fields.append(key)
                        break

        if placeholder_fields:
            results.append(
                ValidationResult(
                    level=ValidationLevel.WARN,
                    message=f"Placeholder values detected in fields: {', '.join(placeholder_fields)}",
                    details={"placeholder_fields": placeholder_fields},
                )
            )

        # Check for gibberish (very short random-looking strings)
        suspicious_fields = []
        for key, value in raw_data.items():
            if isinstance(value, str) and len(value) > 5:
                if self._is_gibberish(value):
                    suspicious_fields.append(key)

        if suspicious_fields:
            gibberish_ratio = len(suspicious_fields) / max(len(raw_data), 1)
            if gibberish_ratio > self.MAX_GIBBERISH_RATIO:
                results.append(
                    ValidationResult(
                        level=ValidationLevel.FAIL,
                        message="Data appears to be gibberish or corrupted",
                        details={"suspicious_fields": suspicious_fields},
                    )
                )
            else:
                results.append(
                    ValidationResult(
                        level=ValidationLevel.WARN,
                        message=f"Suspicious values in fields: {', '.join(suspicious_fields)}",
                        details={"suspicious_fields": suspicious_fields},
                    )
                )

        # Check total data size
        data_size = len(str(raw_data))
        if data_size < self.MIN_DATA_SIZE:
            results.append(
                ValidationResult(
                    level=ValidationLevel.WARN,
                    message=f"Data is very small ({data_size} chars). May lack sufficient detail.",
                    details={"size_chars": data_size, "minimum": self.MIN_DATA_SIZE},
                )
            )

        return results

    def _check_data_types(self, raw_data: Dict) -> List[ValidationResult]:
        """Check data types are appropriate"""
        results = []

        for key, value in raw_data.items():
            # Skip None
            if value is None:
                continue

            # Check for obviously wrong types
            if key in ("probability", "confidence", "score", "rating") and isinstance(
                value, str
            ):
                # Numeric fields shouldn't be strings (unless they're numbers-as-strings)
                try:
                    float(value)
                except (ValueError, TypeError):
                    results.append(
                        ValidationResult(
                            level=ValidationLevel.WARN,
                            message=f"Field '{key}' expected numeric, got string",
                            details={"key": key, "type": "string"},
                        )
                    )

            # Very long strings might indicate corruption
            if isinstance(value, str) and len(value) > 50000:
                results.append(
                    ValidationResult(
                        level=ValidationLevel.WARN,
                        message=f"Field '{key}' is unusually long ({len(value)} chars). Possible data issue.",
                        details={"key": key, "length": len(value)},
                    )
                )

        return results

    def _check_value_ranges(self, raw_data: Dict) -> List[ValidationResult]:
        """Check numeric values are in reasonable ranges"""
        results = []

        for key, value in raw_data.items():
            if not isinstance(value, (int, float)):
                continue

            # Probabilities must be 0-1
            if key in (
                "probability",
                "confidence",
                "score",
                "rating",
                "pct",
                "percent",
            ):
                if not (0 <= value <= 1):
                    results.append(
                        ValidationResult(
                            level=ValidationLevel.FAIL,
                            message=f"Field '{key}' has out-of-range value {value} (expected 0-1)",
                            details={"key": key, "value": value},
                        )
                    )

            # Sizes/counts should be positive
            if key in ("size", "count", "num", "number", "simulations"):
                if value < 0:
                    results.append(
                        ValidationResult(
                            level=ValidationLevel.FAIL,
                            message=f"Field '{key}' has negative value {value}",
                            details={"key": key, "value": value},
                        )
                    )

        return results

    def _check_staleness(self, context: Dict) -> List[ValidationResult]:
        """Check data freshness"""
        results = []

        data_age = context.get("data_age_days")
        if data_age is None:
            results.append(
                ValidationResult(
                    level=ValidationLevel.WARN,
                    message="No data_age_days provided. Cannot assess freshness.",
                    details={"data_age_days": None},
                )
            )
            return results

        # Very stale data is a warning (not failure - some use cases accept old data)
        if data_age > 30:
            results.append(
                ValidationResult(
                    level=ValidationLevel.WARN,
                    message=f"Data is {data_age} days old. Predictions may be unreliable.",
                    details={"data_age_days": data_age},
                )
            )

        return results

    def _calculate_quality_score(self, raw_data: Dict, context: Dict) -> float:
        """Calculate overall data quality score 0-1"""
        score = 0.0

        # Field count contribution (max 0.3)
        field_count = len([k for k, v in raw_data.items() if v is not None and v != ""])
        score += min(field_count / 10, 1.0) * 0.3

        # Data size contribution (max 0.3)
        data_size = len(str(raw_data))
        score += min(data_size / 2000, 1.0) * 0.3

        # No placeholders (max 0.2)
        has_placeholders = any(
            p in str(v).lower()
            for v in raw_data.values()
            for p in self.PLACEHOLDER_PATTERNS
        )
        if not has_placeholders:
            score += 0.2

        # Fresh data (max 0.2)
        data_age = context.get("data_age_days", 0)
        staleness_factor = self.get_staleness_factor(data_age)
        score += staleness_factor * 0.2

        return min(score, 1.0)

    def _is_gibberish(self, text: str) -> bool:
        """Detect if text is likely gibberish/random characters"""
        if len(text) < 10:
            return False

        import re

        # Check character diversity (too uniform = suspicious)
        unique_ratio = len(set(text.lower())) / len(text)
        if unique_ratio < 0.3:
            return True

        # Check for keyboard walk patterns (qwerty, asdf, etc.)
        keyboard_patterns = ["qwerty", "asdf", "zxcv", "1234", "abcd"]
        text_lower = text.lower()
        if any(pattern in text_lower for pattern in keyboard_patterns):
            return True

        # Check for excessive repetition
        if re.search(r"(.)\1{5,}", text):  # Same char 6+ times
            return True

        return False

    def get_staleness_factor(self, data_age_days: int) -> float:
        """
        Get staleness factor that caps maximum confidence.

        This is the ceiling - even if everything else looks great,
        you can't have high confidence on stale data.
        """
        for max_age, ceiling in sorted(self.STALENESS_CEILINGS.items(), reverse=True):
            if data_age_days >= max_age:
                return ceiling

        return self.STALENESS_CEILINGS[0]  # Fresh data = 1.0

    def get_staleness_ceiling(self, data_age_days: int) -> float:
        """Alias for get_staleness_factor for clarity"""
        return self.get_staleness_factor(data_age_days)
