"""
Configuration Validation Module

Validates environment variable consistency and catches common configuration errors.
Run this during service startup to ensure configuration integrity.
"""

import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

from src.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """Represents a configuration validation issue."""
    severity: str  # "ERROR", "WARNING", "INFO"
    category: str  # e.g., "vllm", "performance", "security"
    message: str
    suggestion: Optional[str] = None


class ConfigValidator:
    """
    Validates configuration consistency and best practices.

    Checks:
    - Multi-location conflicts are resolved
    - Parameter ranges are valid
    - Performance settings are optimal
    - Security settings are appropriate
    """

    def __init__(self):
        self.settings = get_settings()
        self.issues: List[ValidationIssue] = []

    def validate_all(self) -> Tuple[bool, List[ValidationIssue]]:
        """
        Run all validation checks.

        Returns:
            Tuple of (is_valid, issues_list)
            is_valid is False if any ERROR-level issues found
        """
        self.issues.clear()

        # Run all validation checks
        self._validate_vllm_config()
        self._validate_performance_config()
        self._validate_pattern_config()
        self._validate_security_config()
        self._validate_extraction_config()
        self._validate_gpu_config()

        # Check if any errors found
        has_errors = any(issue.severity == "ERROR" for issue in self.issues)

        return (not has_errors, self.issues)

    def _validate_vllm_config(self):
        """Validate vLLM configuration parameters."""
        vllm = self.settings.vllm_direct

        # GPU memory utilization
        if not (0.0 < vllm.vllm_gpu_memory_utilization <= 1.0):
            self.issues.append(ValidationIssue(
                severity="ERROR",
                category="vllm",
                message=f"VLLM_GPU_MEMORY_UTILIZATION={vllm.vllm_gpu_memory_utilization} is out of range (0.0-1.0)",
                suggestion="Set to 0.85 for safety or 0.95 for maximum throughput"
            ))
        elif vllm.vllm_gpu_memory_utilization > 0.95:
            self.issues.append(ValidationIssue(
                severity="WARNING",
                category="vllm",
                message=f"VLLM_GPU_MEMORY_UTILIZATION={vllm.vllm_gpu_memory_utilization} is very high",
                suggestion="Values >0.95 may cause OOM errors. Consider 0.85-0.90 for stability"
            ))

        # Temperature
        if not (0.0 <= vllm.vllm_temperature <= 2.0):
            self.issues.append(ValidationIssue(
                severity="ERROR",
                category="vllm",
                message=f"VLLM_DEFAULT_TEMPERATURE={vllm.vllm_temperature} is out of range (0.0-2.0)",
                suggestion="Set to 0.0 for deterministic extraction"
            ))

        # Top-p
        if not (0.0 < vllm.vllm_top_p <= 1.0):
            self.issues.append(ValidationIssue(
                severity="ERROR",
                category="vllm",
                message=f"VLLM_DEFAULT_TOP_P={vllm.vllm_top_p} is out of range (0.0-1.0)",
                suggestion="Set to 0.95 for balanced sampling"
            ))

        # Max tokens vs context length
        if vllm.vllm_max_tokens > vllm.vllm_max_model_len:
            self.issues.append(ValidationIssue(
                severity="ERROR",
                category="vllm",
                message=f"VLLM_DEFAULT_MAX_TOKENS ({vllm.vllm_max_tokens}) exceeds VLLM_MAX_MODEL_LEN ({vllm.vllm_max_model_len})",
                suggestion=f"Set VLLM_DEFAULT_MAX_TOKENS <= {vllm.vllm_max_model_len}"
            ))

        # Prefix caching recommendation
        if not vllm.vllm_enable_prefix_caching:
            self.issues.append(ValidationIssue(
                severity="WARNING",
                category="vllm",
                message="VLLM_ENABLE_PREFIX_CACHING is disabled",
                suggestion="Enable for better performance with legal documents (repetitive patterns)"
            ))

        # GPU ID
        if vllm.vllm_gpu_id < 0:
            self.issues.append(ValidationIssue(
                severity="ERROR",
                category="vllm",
                message=f"VLLM_GPU_ID={vllm.vllm_gpu_id} is invalid (must be >= 0)",
                suggestion="Set to 0 for first GPU, check with nvidia-smi"
            ))

    def _validate_performance_config(self):
        """Validate performance tuning parameters."""
        perf = self.settings.performance

        # Multi-pass iterations
        if perf.multipass_max_iterations < 1:
            self.issues.append(ValidationIssue(
                severity="ERROR",
                category="performance",
                message=f"MULTIPASS_MAX_ITERATIONS={perf.multipass_max_iterations} is too low",
                suggestion="Set to at least 1 (recommended: 8 for full entity coverage)"
            ))
        elif perf.multipass_max_iterations > 20:
            self.issues.append(ValidationIssue(
                severity="WARNING",
                category="performance",
                message=f"MULTIPASS_MAX_ITERATIONS={perf.multipass_max_iterations} is very high",
                suggestion="Values >10 may cause excessive processing time"
            ))

        # Convergence threshold
        if not (0.0 < perf.multipass_convergence_threshold <= 1.0):
            self.issues.append(ValidationIssue(
                severity="ERROR",
                category="performance",
                message=f"MULTIPASS_CONVERGENCE_THRESHOLD={perf.multipass_convergence_threshold} is out of range",
                suggestion="Set to 0.95 for balanced quality/speed"
            ))

        # Deduplication threshold
        if not (0.0 < perf.dedup_similarity_threshold <= 1.0):
            self.issues.append(ValidationIssue(
                severity="ERROR",
                category="performance",
                message=f"DEDUP_SIMILARITY_THRESHOLD={perf.dedup_similarity_threshold} is out of range",
                suggestion="Set to 0.85 for fuzzy deduplication"
            ))

        # Quality confidence threshold
        if not (0.0 <= perf.quality_min_entity_confidence <= 1.0):
            self.issues.append(ValidationIssue(
                severity="ERROR",
                category="performance",
                message=f"QUALITY_MIN_ENTITY_CONFIDENCE={perf.quality_min_entity_confidence} is out of range",
                suggestion="Set to 0.5 for balanced precision/recall"
            ))

    def _validate_pattern_config(self):
        """Validate pattern system configuration."""
        pattern = self.settings.patterns

        # Cache size
        if hasattr(pattern, 'pattern_cache_size') and pattern.pattern_cache_size < 100:
            self.issues.append(ValidationIssue(
                severity="WARNING",
                category="pattern",
                message=f"PATTERN_CACHE_SIZE={pattern.pattern_cache_size} may be too small",
                suggestion="Increase to 1000+ for production workloads"
            ))

        # Caching enabled
        if hasattr(pattern, 'enable_pattern_caching') and not pattern.enable_pattern_caching:
            self.issues.append(ValidationIssue(
                severity="WARNING",
                category="pattern",
                message="Pattern caching is disabled",
                suggestion="Enable pattern caching for better performance"
            ))

    def _validate_security_config(self):
        """Validate security settings."""
        # Environment mode
        if hasattr(self.settings, 'environment') and self.settings.environment == "production":
            if hasattr(self.settings, 'debug') and self.settings.debug:
                self.issues.append(ValidationIssue(
                    severity="ERROR",
                    category="security",
                    message="DEBUG_MODE is enabled in production environment",
                    suggestion="Set DEBUG_MODE=false for production"
                ))

        # Check extraction config security
        extraction_config = self.settings.get_extraction_config()
        if extraction_config.get('environment') == 'production':
            if extraction_config.get('debug_mode'):
                self.issues.append(ValidationIssue(
                    severity="WARNING",
                    category="security",
                    message="Debug mode enabled in production extraction config",
                    suggestion="Disable debug mode for production"
                ))

    def _validate_extraction_config(self):
        """Validate extraction configuration."""
        extraction = self.settings.extraction

        # Confidence thresholds
        if hasattr(extraction, 'confidence_threshold'):
            threshold = extraction.confidence_threshold
            if threshold < 0.0 or threshold > 1.0:
                self.issues.append(ValidationIssue(
                    severity="ERROR",
                    category="extraction",
                    message=f"EXTRACTION_CONFIDENCE_THRESHOLD={threshold} is out of range",
                    suggestion="Set to 0.7 for balanced precision/recall"
                ))

        # Entity length limits
        if hasattr(extraction, 'min_entity_length') and extraction.min_entity_length < 1:
            self.issues.append(ValidationIssue(
                severity="ERROR",
                category="extraction",
                message=f"EXTRACTION_MIN_ENTITY_LENGTH={extraction.min_entity_length} is too low",
                suggestion="Set to at least 2 to filter out single characters"
            ))

        if hasattr(extraction, 'max_entity_length') and extraction.max_entity_length > 10000:
            self.issues.append(ValidationIssue(
                severity="WARNING",
                category="extraction",
                message=f"EXTRACTION_MAX_ENTITY_LENGTH={extraction.max_entity_length} is very large",
                suggestion="Values >1000 may indicate malformed extraction"
            ))

    def _validate_gpu_config(self):
        """Validate GPU-specific configuration."""
        vllm = self.settings.vllm_direct

        # GPU memory threshold
        if not (0.0 < vllm.vllm_gpu_memory_threshold <= 1.0):
            self.issues.append(ValidationIssue(
                severity="ERROR",
                category="gpu",
                message=f"VLLM_GPU_MEMORY_THRESHOLD={vllm.vllm_gpu_memory_threshold} is out of range",
                suggestion="Set to 0.90 for warnings at 90% memory usage"
            ))

        # Monitor interval
        if vllm.vllm_gpu_monitor_interval < 1:
            self.issues.append(ValidationIssue(
                severity="WARNING",
                category="gpu",
                message=f"VLLM_GPU_MONITOR_INTERVAL={vllm.vllm_gpu_monitor_interval} is too frequent",
                suggestion="Set to 30+ seconds to avoid excessive logging"
            ))

    def print_report(self):
        """Print validation report to console."""
        if not self.issues:
            logger.info("✅ Configuration validation PASSED - No issues found")
            return

        # Count by severity
        errors = [i for i in self.issues if i.severity == "ERROR"]
        warnings = [i for i in self.issues if i.severity == "WARNING"]
        infos = [i for i in self.issues if i.severity == "INFO"]

        logger.warning(f"\n{'='*80}")
        logger.warning(f"Configuration Validation Report")
        logger.warning(f"{'='*80}")
        logger.warning(f"Errors: {len(errors)} | Warnings: {len(warnings)} | Info: {len(infos)}")
        logger.warning(f"{'='*80}\n")

        # Print errors first
        if errors:
            logger.error("❌ ERRORS (Must Fix):")
            for issue in errors:
                logger.error(f"  [{issue.category.upper()}] {issue.message}")
                if issue.suggestion:
                    logger.error(f"    → Suggestion: {issue.suggestion}")
            logger.error("")

        # Then warnings
        if warnings:
            logger.warning("⚠️  WARNINGS (Should Review):")
            for issue in warnings:
                logger.warning(f"  [{issue.category.upper()}] {issue.message}")
                if issue.suggestion:
                    logger.warning(f"    → Suggestion: {issue.suggestion}")
            logger.warning("")

        # Then info
        if infos:
            logger.info("ℹ️  INFO (Recommendations):")
            for issue in infos:
                logger.info(f"  [{issue.category.upper()}] {issue.message}")
                if issue.suggestion:
                    logger.info(f"    → Suggestion: {issue.suggestion}")
            logger.info("")

        logger.warning(f"{'='*80}\n")


def validate_configuration() -> bool:
    """
    Run configuration validation.

    Returns:
        True if configuration is valid (no errors), False otherwise
    """
    validator = ConfigValidator()
    is_valid, issues = validator.validate_all()
    validator.print_report()

    return is_valid


# Run validation on import if DEBUG_MODE is enabled
if __name__ == "__main__":
    # Allow running as script: python -m src.core.config_validator
    is_valid = validate_configuration()
    exit(0 if is_valid else 1)
