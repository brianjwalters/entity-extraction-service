"""Configuration management for Entity Extraction Service.

Handles environment variables, service settings, and comprehensive
configuration validation for production environments.
"""

from pathlib import Path
from functools import lru_cache
from typing import List, Optional, Dict, Any

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExtractionSettings(BaseSettings):
    """Entity extraction configuration settings."""
    
    # Extraction Modes
    # Wave System (primary): /api/v2/process/extract - AI-enhanced extraction with pattern injection
    # Multipass (legacy): /api/v1/extract - Multi-pass extraction system
    default_extraction_mode: str = Field(
        default="ai_enhanced",
        description="Default extraction mode: ai_enhanced (Wave System) or multi_pass (legacy)"
    )
    available_extraction_modes: List[str] = Field(
        default=["ai_enhanced", "multi_pass"],
        description="Available extraction modes (regex/hybrid deprecated - use ai_enhanced instead)"
    )

    # Temperature configuration for entity extraction
    entity_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Temperature for entity extraction (0.0 = deterministic, reproducible results)"
    )

    relationship_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Temperature for relationship extraction (0.0 = deterministic, reproducible results)"
    )
    
    # Confidence and Thresholds
    default_confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Default confidence threshold for AI extraction"
    )
    min_confidence_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold allowed"
    )
    high_confidence_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="High confidence threshold for automatic acceptance"
    )
    
    # Content Processing Limits
    max_content_length: int = Field(
        default=1000000,  # 1MB
        gt=0,
        description="Maximum content length for extraction (bytes)"
    )
    max_context_window: int = Field(
        default=1000,
        gt=0,
        description="Maximum context window size for entity extraction"
    )
    chunk_size: int = Field(
        default=4000,  # Optimized for multi-pass extraction
        gt=0,
        description="Default chunk size for large document processing"
    )
    chunk_overlap: int = Field(
        default=1000,  # Increased overlap for better context
        ge=0,
        description="Overlap between chunks for continuity"
    )
    
    # Multi-Pass Extraction Settings
    enable_multi_pass: bool = Field(
        default=True,
        description="Enable multi-pass extraction for better accuracy"
    )
    extraction_passes: List[str] = Field(
        default=["actors", "citations", "concepts"],
        description="Extraction passes to perform in order"
    )
    multi_pass_chunk_size: int = Field(
        default=4000,
        gt=0,
        description="Chunk size for multi-pass extraction"
    )
    multi_pass_max_tokens: int = Field(
        default=500,
        gt=0,
        description="Max tokens per extraction pass"
    )
    multi_pass_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Temperature for multi-pass LLM calls"
    )
    
    # Processing Limits
    max_concurrent_extractions: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum concurrent extraction requests"
    )
    processing_timeout_seconds: int = Field(
        default=1800,  # 30 minutes - timeout for large documents
        gt=0,
        description="Maximum processing time per extraction with local AI enhancement"
    )
    uvicorn_timeout_keep_alive: int = Field(
        default=1800,  # 30 minutes - timeout for complex extractions
        env="ENTITY_EXTRACTION_UVICORN_TIMEOUT",
        gt=0,
        description="Uvicorn keep-alive timeout for long-running requests"
    )
    batch_size: int = Field(
        default=50,
        ge=1,
        description="Default batch size for bulk extractions"
    )
    
    @validator('default_extraction_mode')
    def validate_extraction_mode(cls, v, values):
        # Check for deprecated modes first
        if v in ["regex", "hybrid"]:
            raise ValueError(
                f"Extraction mode '{v}' is deprecated. "
                f"Use 'ai_enhanced' for Wave System (/api/v2/process/extract) "
                f"or 'multi_pass' for legacy multipass extraction (/api/v1/extract)."
            )

        available_modes = values.get('available_extraction_modes', ['ai_enhanced', 'multi_pass'])
        if v not in available_modes:
            raise ValueError(
                f"Invalid extraction mode '{v}'. "
                f"Available modes: {', '.join(available_modes)}"
            )
        return v
    
    @validator('chunk_overlap')
    def validate_chunk_overlap(cls, v, values):
        chunk_size = values.get('chunk_size', 5000)
        if v >= chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size")
        return v

    def validate_mode_at_runtime(self, mode: str) -> None:
        """
        Validate extraction mode at runtime and raise helpful error for deprecated modes.

        Args:
            mode: The extraction mode to validate

        Raises:
            ValueError: If mode is deprecated or invalid
        """
        if mode in ["regex", "hybrid"]:
            raise ValueError(
                f"Extraction mode '{mode}' is deprecated. "
                f"Use 'ai_enhanced' for Wave System (/api/v2/process/extract) "
                f"or 'multi_pass' for legacy multipass extraction (/api/v1/extract)."
            )
        if mode not in self.available_extraction_modes:
            raise ValueError(
                f"Invalid extraction mode '{mode}'. "
                f"Available modes: {', '.join(self.available_extraction_modes)}"
            )




class LlamaLocalSettings(BaseSettings):
    """Local Llama model configuration with breakthrough performance settings."""
    
    # Model Configuration
    enable_local_processing: bool = Field(
        default=True,
        description="Enable local Llama processing for AI enhancement"
    )
    model_path: str = Field(
        default="ibm-granite/granite-3.3-8b-instruct-GGUF",
        description="Path to local Llama model"
    )
    model_file: Optional[str] = Field(
        default="granite-3.3-8b-instruct-Q4_K_M.gguf",
        description="Specific model file name"
    )
    auto_load_model: bool = Field(
        default=True,
        description="Automatically load model on service startup"
    )
    
    # Breakthrough Performance Configuration (176ms SS tier)
    n_gpu_layers: int = Field(
        default=64,
        ge=0,
        le=256,
        description="Number of GPU layers (64 for breakthrough performance)"
    )
    n_parallel: int = Field(
        default=64,
        ge=1,
        le=512,
        description="Parallel processing slots (64 for massive parallelization)"
    )
    n_batch: int = Field(
        default=65536,
        ge=1,
        description="Batch size (65536 for large batch processing)"
    )
    n_ubatch: int = Field(
        default=16384,
        ge=1,
        description="Physical batch size (16384 - critical performance parameter)"
    )
    n_ctx: int = Field(
        default=4096,
        ge=128,
        le=131072,
        description="Context size (4096 for AI enhancement compatibility)"
    )
    n_threads: int = Field(
        default=20,
        ge=1,
        le=64,
        description="Number of threads (20 optimal for breakthrough config)"
    )
    n_threads_batch: int = Field(
        default=32,
        ge=1,
        le=64,
        description="Batch processing threads (32 for enhanced throughput)"
    )
    
    # Memory Optimization Settings
    use_mmap: bool = Field(
        default=False,
        description="Use memory mapping (False for speed optimization)"
    )
    use_mlock: bool = Field(
        default=True,
        description="Lock model in RAM (True for breakthrough performance)"
    )
    numa: bool = Field(
        default=True,
        description="Enable NUMA optimization"
    )
    
    # Advanced Performance Settings
    rope_freq_base: float = Field(
        default=100000.0,
        gt=0.0,
        description="RoPE frequency base for breakthrough config"
    )
    rope_scaling_type: str = Field(
        default="dynamic",
        description="RoPE scaling type (dynamic for optimal performance)"
    )
    flash_attn: bool = Field(
        default=True,
        description="Enable flash attention optimization"
    )
    
    # Cache Configuration
    cache_type_k: str = Field(
        default="f16",
        description="Key cache type (f16 for speed)"
    )
    cache_type_v: str = Field(
        default="f16",
        description="Value cache type (f16 for speed)"
    )
    
    # Generation Settings
    seed: int = Field(
        default=-1,
        description="Random seed (-1 for random)"
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose logging (disabled for performance)"
    )
    
    # Timeouts and Resource Management
    model_load_timeout: int = Field(
        default=1800,  # 30 minutes - timeout for model operations
        gt=0,
        description="Model loading timeout in seconds"
    )
    generation_timeout: int = Field(
        default=1800,  # 30 minutes - timeout for comprehensive AI enhancement
        gt=0,
        description="Generation timeout for comprehensive AI enhancement"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retry attempts for failed generations"
    )
    health_check_interval: int = Field(
        default=60,
        gt=0,
        description="Health check interval in seconds"
    )
    
    # Memory Management
    min_memory_gb: float = Field(
        default=4.0,
        gt=0.0,
        description="Minimum system memory required for model loading (GB)"
    )
    max_memory_gb: float = Field(
        default=16.0,
        gt=0.0,
        description="Maximum memory allowed for model (GB)"
    )
    memory_check_interval: int = Field(
        default=30,
        gt=0,
        description="Memory monitoring interval in seconds"
    )
    
    # Fallback Configuration
    enable_fallback_to_remote: bool = Field(
        default=True,
        description="Fall back to remote prompt service if local processing fails"
    )
    fallback_threshold_ms: int = Field(
        default=5000,
        gt=0,
        description="Response time threshold for fallback trigger (ms)"
    )
    
    @validator('n_ubatch')
    def validate_ubatch_size(cls, v, values):
        n_batch = values.get('n_batch', 65536)
        if v > n_batch:
            raise ValueError("n_ubatch must be less than or equal to n_batch")
        return v
    
    @validator('n_threads_batch')
    def validate_threads_batch(cls, v, values):
        n_threads = values.get('n_threads', 20)
        if v < n_threads:
            raise ValueError("n_threads_batch should be greater than or equal to n_threads")
        return v


class AISettings(BaseSettings):
    """AI and LLM configuration settings."""
    
    # AI Service Configuration
    enable_ai_enhancement: bool = Field(
        default=True,
        description="Enable AI-powered extraction enhancement"
    )
    ai_timeout_seconds: int = Field(
        default=1800,  # 30 minutes - timeout for local AI processing
        gt=0,
        description="Timeout for local AI processing for comprehensive enhancement"
    )
    ai_max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retries for AI service calls (deprecated - use llama_local.max_retries)"
    )
    ai_retry_delay_seconds: float = Field(
        default=1.0,
        ge=0.0,
        description="Delay between AI service retries"
    )
    enable_ai_fallback: bool = Field(
        default=True,
        description="Fall back to regex if AI fails"
    )
    
    # Processing Mode Configuration
    prefer_local_processing: bool = Field(
        default=True,
        description="Prefer local Llama processing over remote prompt service"
    )
    local_processing_mode: str = Field(
        default="hybrid",
        description="Local processing mode: auto, local_only, remote_only, hybrid"
    )
    
    # LLM Parameters
    default_temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Default temperature for LLM requests"
    )
    default_max_tokens: int = Field(
        default=4096,
        gt=0,
        description="Default maximum tokens for LLM responses (DEPRECATED - use llm_max_response_tokens)"
    )
    llm_max_response_tokens: int = Field(
        default=8000,
        gt=0,
        le=128000,  # IBM Granite 3.3 2B has 128K context
        description="Maximum tokens for ALL LLM responses - single source of truth for entity extraction"
    )
    prompt_template_max_tokens: int = Field(
        default=50000,
        gt=0,
        le=100000,
        description="Maximum tokens for prompt templates (supports all 272 entity types)"
    )
    default_top_p: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Default top-p value for LLM sampling"
    )
    
    # Model Configuration
    default_extraction_model: str = Field(
        default="llama-3-8b",
        description="Default model for entity extraction"
    )
    default_validation_model: str = Field(
        default="llama-3-8b",
        description="Default model for validation tasks"
    )
    model_rotation_enabled: bool = Field(
        default=False,
        description="Enable automatic model rotation for load balancing"
    )
    
    # Context and Prompt Settings
    max_context_examples: int = Field(
        default=5,
        ge=0,
        description="Maximum examples to include in prompts"
    )
    enable_context_enrichment: bool = Field(
        default=True,
        description="Enable contextual information enrichment"
    )
    context_similarity_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for context selection"
    )
    
    @validator('local_processing_mode')
    def validate_processing_mode(cls, v):
        valid_modes = ['auto', 'local_only', 'remote_only', 'hybrid']
        if v not in valid_modes:
            raise ValueError(f"local_processing_mode must be one of: {valid_modes}")
        return v


class PatternSettings(BaseSettings):
    """Pattern configuration and caching settings."""

    # Pattern Loading
    patterns_directory: str = Field(
        default="src/patterns",
        description="Directory containing pattern files"
    )
    enable_pattern_validation: bool = Field(
        default=True,
        env="PATTERN_VALIDATE_ON_LOAD",
        description="Enable pattern syntax validation on load"
    )
    enable_pattern_compilation: bool = Field(
        default=True,
        description="Enable pattern compilation optimization"
    )
    pattern_loading_timeout: int = Field(
        default=1800,  # 30 minutes - timeout for pattern operations
        gt=0,
        description="Timeout for pattern loading operations"
    )

    # Caching Configuration (from Section 10)
    enable_pattern_caching: bool = Field(
        default=True,
        env="PATTERN_ENABLE_CACHING",
        description="Enable pattern compilation caching"
    )
    pattern_cache_size: int = Field(
        default=1000,
        env="PATTERN_CACHE_SIZE",
        gt=0,
        description="Maximum number of compiled patterns to cache (LRU)"
    )
    pattern_cache_ttl_seconds: int = Field(
        default=3600,  # 1 hour
        env="PATTERN_CACHE_TTL",
        gt=0,
        description="Time-to-live for cached patterns (seconds)"
    )

    # Threading and Performance
    enable_threaded_loading: bool = Field(
        default=True,
        description="Enable threaded pattern loading"
    )
    max_loader_threads: int = Field(
        default=4,
        env="PATTERN_MAX_WORKERS",
        ge=1,
        le=16,
        description="Maximum parallel pattern loading threads"
    )
    pattern_lazy_loading: bool = Field(
        default=False,
        env="PATTERN_LAZY_LOADING",
        description="Enable lazy pattern loading"
    )
    pattern_compression_enabled: bool = Field(
        default=False,
        env="PATTERN_COMPRESSION_ENABLED",
        description="Enable pattern compression in cache"
    )

    # Auto-reload and Monitoring
    enable_pattern_auto_reload: bool = Field(
        default=False,
        env="PATTERN_AUTO_RELOAD",
        description="Enable automatic pattern reloading on file changes"
    )
    pattern_reload_interval_seconds: int = Field(
        default=300,  # 5 minutes
        gt=0,
        description="Interval for checking pattern file changes"
    )

    # Quality Control
    min_pattern_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for patterns to be loaded"
    )
    max_patterns_per_file: int = Field(
        default=500,
        gt=0,
        description="Maximum patterns allowed per file"
    )


class RegexEngineSettings(BaseSettings):
    """Regex engine configuration and execution settings (Section 11)."""

    # Regex Compilation and Execution
    regex_cache_size: int = Field(
        default=500,
        env="REGEX_CACHE_SIZE",
        gt=0,
        description="Compiled regex cache size"
    )
    regex_timeout_ms: int = Field(
        default=1000,
        env="REGEX_TIMEOUT_MS",
        gt=0,
        description="Regex execution timeout (milliseconds)"
    )
    regex_enable_multiline: bool = Field(
        default=True,
        env="REGEX_ENABLE_MULTILINE",
        description="Enable multiline mode by default"
    )
    regex_enable_dotall: bool = Field(
        default=False,
        env="REGEX_ENABLE_DOTALL",
        description="Enable dotall mode by default"
    )
    regex_max_recursion_depth: int = Field(
        default=100,
        env="REGEX_MAX_RECURSION_DEPTH",
        gt=0,
        description="Maximum regex recursion depth"
    )


class PerformanceSettings(BaseSettings):
    """Performance monitoring and optimization settings."""

    # Monitoring
    enable_performance_monitoring: bool = Field(
        default=True,
        description="Enable performance monitoring"
    )
    performance_sample_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Sample rate for performance monitoring"
    )
    enable_metrics_export: bool = Field(
        default=True,
        description="Enable metrics export to monitoring systems"
    )

    # Memory Management
    max_memory_usage_mb: int = Field(
        default=2048,  # 2GB
        gt=0,
        description="Maximum memory usage before triggering cleanup"
    )
    memory_check_interval_seconds: int = Field(
        default=60,
        gt=0,
        description="Interval for memory usage checks"
    )
    enable_memory_cleanup: bool = Field(
        default=True,
        description="Enable automatic memory cleanup"
    )

    # Concurrency and Threading
    max_worker_threads: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum worker threads for extraction tasks"
    )
    thread_pool_size: int = Field(
        default=8,
        ge=1,
        le=32,
        description="Size of the thread pool for concurrent operations"
    )

    # Caching Performance
    enable_result_caching: bool = Field(
        default=True,
        description="Enable extraction result caching"
    )
    result_cache_size: int = Field(
        default=1000,
        gt=0,
        description="Maximum number of extraction results to cache"
    )
    result_cache_ttl_seconds: int = Field(
        default=1800,  # 30 minutes
        gt=0,
        description="Time-to-live for cached extraction results"
    )

    # Multi-Pass Extraction Configuration (Section 12)
    multipass_max_iterations: int = Field(
        default=8,
        env="MULTIPASS_MAX_ITERATIONS",
        gt=0,
        description="Maximum multi-pass iterations"
    )
    multipass_convergence_threshold: float = Field(
        default=0.95,
        env="MULTIPASS_CONVERGENCE_THRESHOLD",
        ge=0.0,
        le=1.0,
        description="Stop when confidence reaches this threshold"
    )
    multipass_enable_parallel: bool = Field(
        default=True,
        env="MULTIPASS_ENABLE_PARALLEL",
        description="Enable parallel pass execution"
    )
    multipass_batch_size: int = Field(
        default=10,
        env="MULTIPASS_BATCH_SIZE",
        gt=0,
        description="Batch size for parallel passes"
    )
    multipass_timeout_per_pass: int = Field(
        default=300,
        env="MULTIPASS_TIMEOUT_PER_PASS",
        gt=0,
        description="Timeout per pass (seconds)"
    )

    # Entity Deduplication Configuration (Section 12)
    dedup_similarity_threshold: float = Field(
        default=0.85,
        env="DEDUP_SIMILARITY_THRESHOLD",
        ge=0.0,
        le=1.0,
        description="Entity similarity threshold for deduplication"
    )
    dedup_algorithm: str = Field(
        default="fuzzy",
        env="DEDUP_ALGORITHM",
        description="Deduplication algorithm (fuzzy|exact|semantic)"
    )
    dedup_preserve_highest_confidence: bool = Field(
        default=True,
        env="DEDUP_PRESERVE_HIGHEST_CONFIDENCE",
        description="Keep highest confidence duplicate"
    )
    dedup_cross_type_dedup: bool = Field(
        default=False,
        env="DEDUP_CROSS_TYPE_DEDUP",
        description="Deduplicate across entity types"
    )

    # Response Parsing & Validation (Section 12)
    response_parser_strict_mode: bool = Field(
        default=False,
        env="RESPONSE_PARSER_STRICT_MODE",
        description="Strict JSON parsing mode"
    )
    response_parser_auto_repair: bool = Field(
        default=True,
        env="RESPONSE_PARSER_AUTO_REPAIR",
        description="Auto-repair malformed JSON"
    )
    response_parser_max_repair_attempts: int = Field(
        default=3,
        env="RESPONSE_PARSER_MAX_REPAIR_ATTEMPTS",
        gt=0,
        description="Maximum JSON repair attempts"
    )
    response_validation_schema_strict: bool = Field(
        default=False,
        env="RESPONSE_VALIDATION_SCHEMA_STRICT",
        description="Strict schema validation"
    )

    # Model-Specific Tuning (Section 12)
    model_context_window_buffer: int = Field(
        default=1000,
        env="MODEL_CONTEXT_WINDOW_BUFFER",
        gt=0,
        description="Reserve buffer tokens for context"
    )
    model_output_token_buffer: int = Field(
        default=500,
        env="MODEL_OUTPUT_TOKEN_BUFFER",
        gt=0,
        description="Reserve buffer tokens for output"
    )
    model_enable_dynamic_batching: bool = Field(
        default=True,
        env="MODEL_ENABLE_DYNAMIC_BATCHING",
        description="Enable dynamic batching"
    )
    model_batch_timeout_ms: int = Field(
        default=100,
        env="MODEL_BATCH_TIMEOUT_MS",
        gt=0,
        description="Dynamic batch timeout (milliseconds)"
    )

    # Extraction Quality Controls (Section 12)
    quality_min_entity_confidence: float = Field(
        default=0.5,
        env="QUALITY_MIN_ENTITY_CONFIDENCE",
        ge=0.0,
        le=1.0,
        description="Minimum entity confidence to keep"
    )
    quality_enable_confidence_calibration: bool = Field(
        default=True,
        env="QUALITY_ENABLE_CONFIDENCE_CALIBRATION",
        description="Enable confidence calibration"
    )
    quality_reject_partial_matches: bool = Field(
        default=False,
        env="QUALITY_REJECT_PARTIAL_MATCHES",
        description="Reject partial entity matches"
    )


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""
    
    # Basic Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    enable_structured_logging: bool = Field(
        default=True,
        description="Enable structured JSON logging"
    )
    log_format: str = Field(
        default="json",
        description="Log format: json or text"
    )
    
    # Detailed Logging
    log_extraction_details: bool = Field(
        default=True,
        description="Log detailed extraction information"
    )
    log_pattern_matching: bool = Field(
        default=False,
        description="Log pattern matching details (verbose)"
    )
    log_ai_requests: bool = Field(
        default=True,
        description="Log AI service requests and responses"
    )
    log_performance_metrics: bool = Field(
        default=True,
        description="Log performance metrics"
    )
    
    # Request Tracking
    enable_request_id_logging: bool = Field(
        default=True,
        description="Enable request ID tracking in logs"
    )
    log_request_body: bool = Field(
        default=False,
        description="Log request bodies (potential PII concern)"
    )
    log_response_body: bool = Field(
        default=False,
        description="Log response bodies (potential PII concern)"
    )
    
    # File Logging
    enable_file_logging: bool = Field(
        default=True,
        description="Enable logging to files"
    )
    log_file_path: str = Field(
        default="logs/entity-extraction.log",
        description="Path for log files"
    )
    log_rotation_size_mb: int = Field(
        default=100,
        gt=0,
        description="Log file rotation size in MB"
    )
    log_retention_days: int = Field(
        default=30,
        gt=0,
        description="Days to retain log files"
    )
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()


class HealthCheckSettings(BaseSettings):
    """Health check and monitoring configuration."""

    # Health Check Configuration
    enable_health_checks: bool = Field(
        default=True,
        description="Enable health check endpoints"
    )
    health_check_interval_seconds: int = Field(
        default=30,
        gt=0,
        description="Interval between health checks"
    )
    health_check_timeout_seconds: int = Field(
        default=5,
        gt=0,
        description="Timeout for individual health checks"
    )

    # Component Health Checks
    check_pattern_loader: bool = Field(
        default=True,
        description="Include pattern loader in health checks"
    )
    check_ai_services: bool = Field(
        default=True,
        description="Include AI services in health checks"
    )
    check_database_connection: bool = Field(
        default=True,
        description="Include database connection in health checks"
    )
    check_memory_usage: bool = Field(
        default=True,
        description="Include memory usage in health checks"
    )

    # Alerting Thresholds
    memory_warning_threshold_percent: float = Field(
        default=80.0,
        ge=0.0,
        le=100.0,
        description="Memory usage warning threshold (percentage)"
    )
    memory_critical_threshold_percent: float = Field(
        default=95.0,
        ge=0.0,
        le=100.0,
        description="Memory usage critical threshold (percentage)"
    )
    extraction_latency_warning_ms: int = Field(
        default=5000,
        gt=0,
        description="Extraction latency warning threshold (milliseconds)"
    )
    extraction_latency_critical_ms: int = Field(
        default=15000,
        gt=0,
        description="Extraction latency critical threshold (milliseconds)"
    )


class IntelligentRoutingSettings(BaseSettings):
    """Intelligent document routing configuration for DIS v2.0.0."""

    # Document Size Thresholds (in characters)
    size_threshold_very_small: int = Field(
        default=5000,
        gt=0,
        description="Very small document threshold - single consolidated prompt"
    )
    size_threshold_small: int = Field(
        default=50000,
        gt=0,
        description="Small document threshold - 3-wave system, no chunking"
    )
    size_threshold_medium: int = Field(
        default=150000,
        gt=0,
        description="Medium document threshold - ExtractionChunker + 3-wave"
    )
    # Above 150K = Large documents - ExtractionChunker + adaptive (3/8-wave)

    # Routing Strategy Selection
    enable_intelligent_routing: bool = Field(
        default=True,
        description="Enable intelligent document routing based on size/complexity"
    )
    default_routing_mode: str = Field(
        default="intelligent",
        description="Default routing mode: intelligent, fixed_chunking, no_chunking"
    )

    # Chunking Configuration for Routing
    extraction_chunker_size: int = Field(
        default=8000,
        gt=0,
        description="Chunk size for ExtractionChunker strategy (optimized for 32K context)"
    )
    extraction_chunker_overlap: int = Field(
        default=500,
        gt=0,
        description="Chunk overlap for ExtractionChunker strategy"
    )

    # Wave System Configuration
    enable_three_wave_prompts: bool = Field(
        default=True,
        description="Enable 3-wave prompt system for token efficiency"
    )
    wave_1_entity_types: List[str] = Field(
        default=["PERSON", "JUDGE", "ATTORNEY", "PARTY", "COURT"],
        description="Entity types for Wave 1 (Actors)"
    )
    wave_2_entity_types: List[str] = Field(
        default=["CASE_CITATION", "STATUTE_CITATION", "REGULATION"],
        description="Entity types for Wave 2 (Citations)"
    )
    wave_3_entity_types: List[str] = Field(
        default=["LEGAL_DOCTRINE", "PROCEDURAL_TERM", "LEGAL_CONCEPT"],
        description="Entity types for Wave 3 (Concepts)"
    )

    @validator('size_threshold_small')
    def validate_small_threshold(cls, v, values):
        very_small = values.get('size_threshold_very_small', 5000)
        if v <= very_small:
            raise ValueError("Small threshold must be greater than very small threshold")
        return v

    @validator('size_threshold_medium')
    def validate_medium_threshold(cls, v, values):
        small = values.get('size_threshold_small', 50000)
        if v <= small:
            raise ValueError("Medium threshold must be greater than small threshold")
        return v


class VLLMDirectSettings(BaseSettings):
    """Direct vLLM integration settings for DIS v2.0.0."""

    # Connection Configuration
    enable_vllm_direct: bool = Field(
        default=True,
        description="Enable direct vLLM Python API integration (not HTTP)"
    )
    vllm_host: str = Field(
        default="10.10.0.87",
        description="vLLM service host"
    )
    vllm_port: int = Field(
        default=8080,
        description="vLLM service port"
    )
    vllm_model_name: str = Field(
        default="qwen3-vl-instruct-384k",
        env="VLLM_INSTRUCT_MODEL",
        description="vLLM model name for entity extraction (served model name) - Qwen3-VL-8B-Instruct-FP8 with 65K context"
    )

    # Generation Parameters (Reproducibility)
    vllm_temperature: float = Field(
        default=0.0,
        env="VLLM_DEFAULT_TEMPERATURE",
        ge=0.0,
        le=2.0,
        description="Temperature for vLLM generation (0.0 for reproducibility)"
    )
    vllm_seed: int = Field(
        default=42,
        env="VLLM_SEED",
        description="Random seed for reproducible outputs"
    )
    vllm_max_tokens: int = Field(
        default=4096,
        env="VLLM_DEFAULT_MAX_TOKENS",
        gt=0,
        description="Maximum tokens for vLLM responses"
    )
    vllm_top_p: float = Field(
        default=0.95,
        env="VLLM_DEFAULT_TOP_P",
        ge=0.0,
        le=1.0,
        description="Top-p sampling parameter"
    )
    vllm_top_k: int = Field(
        default=40,
        env="VLLM_DEFAULT_TOP_K",
        gt=0,
        description="Top-k sampling parameter"
    )
    vllm_repetition_penalty: float = Field(
        default=1.0,
        env="VLLM_DEFAULT_REPETITION_PENALTY",
        ge=1.0,
        description="Repetition penalty for vLLM generation"
    )

    # Model Configuration
    vllm_max_model_len: int = Field(
        default=131072,
        env="VLLM_MAX_MODEL_LEN",
        gt=0,
        description="Maximum context length (128K tokens)"
    )
    vllm_gpu_memory_utilization: float = Field(
        default=0.85,
        env="VLLM_GPU_MEMORY_UTILIZATION",
        ge=0.0,
        le=1.0,
        description="GPU memory fraction (0.0-1.0)"
    )

    # Performance Optimization
    vllm_enable_prefix_caching: bool = Field(
        default=True,
        env="VLLM_ENABLE_PREFIX_CACHING",
        description="Enable KV cache prefix caching"
    )
    vllm_enable_chunked_prefill: bool = Field(
        default=True,
        env="VLLM_ENABLE_CHUNKED_PREFILL",
        description="Enable chunked prefill for better memory"
    )
    vllm_max_num_batched_tokens: int = Field(
        default=8192,
        env="VLLM_MAX_NUM_BATCHED_TOKENS",
        gt=0,
        description="Max tokens in batch"
    )
    vllm_max_num_seqs: int = Field(
        default=256,
        env="VLLM_MAX_NUM_SEQS",
        gt=0,
        description="Max sequences in batch"
    )
    vllm_block_size: int = Field(
        default=16,
        env="VLLM_BLOCK_SIZE",
        gt=0,
        description="KV cache block size"
    )
    vllm_swap_space: int = Field(
        default=4,
        env="VLLM_SWAP_SPACE",
        gt=0,
        description="CPU swap space (GB)"
    )
    vllm_enforce_eager: bool = Field(
        default=False,
        env="VLLM_ENFORCE_EAGER",
        description="Disable CUDA graphs for debugging"
    )

    # GPU Configuration
    vllm_gpu_id: int = Field(
        default=0,
        env="VLLM_GPU_ID",
        ge=0,
        description="GPU device ID"
    )
    vllm_tensor_parallel_size: int = Field(
        default=1,
        env="VLLM_TENSOR_PARALLEL_SIZE",
        ge=1,
        description="Number of GPUs for tensor parallelism"
    )
    vllm_gpu_memory_threshold: float = Field(
        default=0.90,
        env="VLLM_GPU_MEMORY_THRESHOLD",
        ge=0.0,
        le=1.0,
        description="GPU memory warning threshold"
    )
    vllm_enable_gpu_monitoring: bool = Field(
        default=True,
        env="VLLM_ENABLE_GPU_MONITORING",
        description="Enable GPU monitoring"
    )
    vllm_gpu_monitor_interval: int = Field(
        default=30,
        env="VLLM_GPU_MONITOR_INTERVAL",
        gt=0,
        description="GPU monitoring interval (seconds)"
    )

    # HTTP Client Configuration
    vllm_timeout_seconds: int = Field(
        default=1800,  # 30 minutes to match processing_timeout_seconds - increased from 300 for large document chunked extraction
        env="VLLM_HTTP_TIMEOUT",
        gt=0,
        description="HTTP request timeout (seconds) - supports THREE_WAVE_CHUNKED strategy requiring 10-20+ minutes"
    )
    vllm_max_retries: int = Field(
        default=3,
        env="VLLM_HTTP_MAX_RETRIES",
        ge=0,
        description="Maximum retry attempts"
    )
    vllm_retry_delay: float = Field(
        default=1.0,
        env="VLLM_HTTP_RETRY_DELAY",
        ge=0.0,
        description="Retry delay (seconds)"
    )
    vllm_connect_timeout: int = Field(
        default=10,
        env="VLLM_HTTP_CONNECT_TIMEOUT",
        gt=0,
        description="Connection timeout (seconds)"
    )
    vllm_connection_pool_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Connection pool size for vLLM client"
    )

    # Token Estimation
    vllm_chars_per_token: float = Field(
        default=4.0,
        env="VLLM_CHARS_PER_TOKEN",
        gt=0.0,
        description="Average characters per token"
    )
    vllm_token_overlap_percent: float = Field(
        default=0.1,
        env="VLLM_TOKEN_OVERLAP_PERCENT",
        ge=0.0,
        le=1.0,
        description="Token overlap percentage"
    )
    vllm_prefill_rate: int = Field(
        default=19000,
        env="VLLM_PREFILL_RATE",
        gt=0,
        description="Prefill tokens/second (GPU dependent)"
    )
    vllm_decode_rate: int = Field(
        default=150,
        env="VLLM_DECODE_RATE",
        gt=0,
        description="Decode tokens/second (GPU dependent)"
    )

    # Warmup Configuration
    vllm_warmup_enabled: bool = Field(
        default=True,
        env="VLLM_WARMUP_ENABLED",
        description="Enable warmup on connection"
    )
    vllm_warmup_max_tokens: int = Field(
        default=10,
        env="VLLM_WARMUP_MAX_TOKENS",
        gt=0,
        description="Warmup request max tokens"
    )

    # Reproducibility Enforcement
    enforce_reproducibility: bool = Field(
        default=True,
        description="Enforce reproducibility (temperature=0.0, fixed seed)"
    )
    reproducibility_validation: bool = Field(
        default=True,
        description="Validate reproducibility in testing"
    )


class ChunkingIntegrationSettings(BaseSettings):
    """Chunking service integration settings for DIS v2.0.0."""

    # Strategy Configuration
    default_chunking_strategy: str = Field(
        default="extraction",
        description="Default chunking strategy: extraction, semantic, legal, hybrid"
    )
    available_chunking_strategies: List[str] = Field(
        default=["extraction", "semantic", "legal", "hybrid", "simple"],
        description="Available chunking strategies"
    )

    # Anthropic Contextual Enhancement
    enable_contextual_enhancement: bool = Field(
        default=False,
        description="Enable Anthropic contextual retrieval enhancement (optional)"
    )
    contextual_enhancement_template: str = Field(
        default="document_context",
        description="Template for contextual enhancement"
    )

    # Quality Thresholds
    chunk_quality_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum quality score for chunks"
    )
    enable_chunk_validation: bool = Field(
        default=True,
        description="Enable chunk quality validation"
    )

    # Chunking Parameters (from extraction_config.py consolidation)
    chunking_max_size: int = Field(
        default=1000,  # Reduced from 2000 for faster processing
        env="CHUNKING_MAX_SIZE",
        gt=0,
        description="Maximum chunk size for document processing"
    )
    chunking_min_size: int = Field(
        default=100,
        env="CHUNKING_MIN_SIZE",
        gt=0,
        description="Minimum chunk size for document processing"
    )
    chunking_overlap: int = Field(
        default=250,  # Reduced from 500 to match smaller chunk size
        env="CHUNKING_OVERLAP",
        ge=0,
        description="Overlap between chunks for continuity"
    )
    chunking_enable_smart: bool = Field(
        default=True,
        env="CHUNKING_ENABLE_SMART",
        description="Enable smart chunking for large documents"
    )
    chunking_preserve_sentences: bool = Field(
        default=True,
        env="CHUNKING_PRESERVE_SENTENCES",
        description="Preserve sentence boundaries when chunking"
    )
    chunking_preserve_paragraphs: bool = Field(
        default=False,
        env="CHUNKING_PRESERVE_PARAGRAPHS",
        description="Preserve paragraph boundaries when chunking"
    )
    chunking_batch_size: int = Field(
        default=5,
        env="CHUNKING_BATCH_SIZE",
        ge=1,
        description="Batch size for chunk processing"
    )
    chunking_max_chunks_per_doc: int = Field(
        default=100,
        env="CHUNKING_MAX_CHUNKS_PER_DOC",
        gt=0,
        description="Maximum chunks per document"
    )
    smart_chunk_threshold: int = Field(
        default=50000,
        env="SMART_CHUNK_THRESHOLD",
        gt=0,
        description="Character threshold for smart chunking activation"
    )
    context_window_size: int = Field(
        default=128000,
        env="CONTEXT_WINDOW_SIZE",
        gt=0,
        description="Context window size for LLM processing"
    )
    context_window_buffer: float = Field(
        default=0.8,
        env="CONTEXT_WINDOW_BUFFER",
        ge=0.0,
        le=1.0,
        description="Buffer percentage of context window to use"
    )
    chunking_bypass: bool = Field(
        default=True,
        env="CHUNKING_BYPASS",
        description="Bypass chunking for unified document processing"
    )
    force_unified_processing: bool = Field(
        default=True,
        env="FORCE_UNIFIED_PROCESSING",
        description="Force unified document processing without chunking"
    )
    disable_micro_chunking: bool = Field(
        default=True,
        env="DISABLE_MICRO_CHUNKING",
        description="Disable micro-chunking for small documents"
    )
    discovery_chunk_size: int = Field(
        default=3000,
        env="DISCOVERY_CHUNK_SIZE",
        gt=0,
        description="Chunk size for discovery phase processing"
    )
    max_unified_document_size: int = Field(
        default=1000000,
        env="MAX_UNIFIED_DOCUMENT_SIZE",
        gt=0,
        description="Maximum document size for unified processing (bytes)"
    )

    @validator('default_chunking_strategy')
    def validate_chunking_strategy(cls, v, values):
        available = values.get('available_chunking_strategies', ['extraction'])
        if v not in available:
            raise ValueError(f"Chunking strategy '{v}' not in available strategies: {available}")
        return v

    @validator('chunking_overlap')
    def validate_chunking_overlap(cls, v, values):
        max_size = values.get('chunking_max_size', 2000)
        if v >= max_size:
            raise ValueError("chunking_overlap must be less than chunking_max_size")
        return v

    # Compatibility properties for SmartChunker (maps chunking_* to expected names)
    @property
    def max_chunk_size(self) -> int:
        """Alias for chunking_max_size (SmartChunker compatibility)."""
        return self.chunking_max_size

    @property
    def min_chunk_size(self) -> int:
        """Alias for chunking_min_size (SmartChunker compatibility)."""
        return self.chunking_min_size

    @property
    def chunk_overlap(self) -> int:
        """Alias for chunking_overlap (SmartChunker compatibility)."""
        return self.chunking_overlap

    @property
    def enable_smart_chunking(self) -> bool:
        """Alias for chunking_enable_smart (SmartChunker compatibility)."""
        return self.chunking_enable_smart

    @property
    def preserve_sentences(self) -> bool:
        """Alias for chunking_preserve_sentences (SmartChunker compatibility)."""
        return self.chunking_preserve_sentences


class SupabaseSettings(BaseSettings):
    """Supabase database configuration for DIS v2.0.0."""

    # Core connection settings
    supabase_url: str = Field(
        default="https://tqfshsnwyhfnkchaiudg.supabase.co",
        env="SUPABASE_URL",
        description="Supabase project URL"
    )
    supabase_api_key: str = Field(
        default="",
        env="SUPABASE_API_KEY",
        description="Supabase anon/public API key"
    )
    supabase_service_key: str = Field(
        default="",
        env="SUPABASE_SERVICE_KEY",
        description="Supabase service role key (admin access)"
    )

    # Operation timeouts
    simple_op_timeout: int = Field(
        default=8,
        gt=0,
        description="Timeout for simple CRUD operations (seconds)"
    )
    complex_op_timeout: int = Field(
        default=20,
        gt=0,
        description="Timeout for complex queries (seconds)"
    )
    batch_op_timeout: int = Field(
        default=30,
        gt=0,
        description="Timeout for batch operations (seconds)"
    )
    vector_op_timeout: int = Field(
        default=25,
        gt=0,
        description="Timeout for vector operations (seconds)"
    )

    # Retry and backoff settings
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retry attempts for failed operations"
    )
    backoff_max: int = Field(
        default=30,
        gt=0,
        description="Maximum backoff time (seconds)"
    )
    backoff_factor: float = Field(
        default=2.0,
        gt=0.0,
        description="Backoff multiplier"
    )

    # Connection pool settings
    max_connections: int = Field(
        default=30,
        gt=0,
        description="Maximum concurrent connections"
    )
    connection_timeout: int = Field(
        default=5,
        gt=0,
        description="Connection timeout (seconds)"
    )
    pool_recycle: int = Field(
        default=300,
        gt=0,
        description="Connection pool recycle time (seconds)"
    )

    # Circuit breaker settings
    circuit_breaker_enabled: bool = Field(
        default=True,
        description="Enable circuit breaker for fault tolerance"
    )
    circuit_breaker_failure_threshold: int = Field(
        default=5,
        gt=0,
        description="Failures before opening circuit"
    )
    circuit_breaker_recovery_timeout: int = Field(
        default=60,
        gt=0,
        description="Time before attempting recovery (seconds)"
    )

    # Performance settings
    batch_size: int = Field(
        default=100,
        gt=0,
        description="Default batch size for bulk operations"
    )
    enable_metrics: bool = Field(
        default=True,
        description="Enable Prometheus metrics"
    )
    enable_slow_query_log: bool = Field(
        default=True,
        description="Enable slow query logging"
    )
    slow_query_threshold: float = Field(
        default=5.0,
        gt=0.0,
        description="Slow query threshold (seconds)"
    )


class EntityExtractionServiceSettings(BaseSettings):
    """Main configuration class for Entity Extraction Service."""
    
    # Service Identification
    service_name: str = Field(
        default="document-intelligence-service",
        description="Service name (formerly entity-extraction-service)"
    )
    service_version: str = Field(
        default="2.0.0",
        description="Service version (v2.0.0 = consolidated service)"
    )
    host: str = Field(
        default="0.0.0.0",
        description="Service host"
    )
    port: int = Field(
        default=8007,
        env="ENTITY_EXTRACTION_SERVICE_PORT",
        description="Document intelligence service port (formerly entity extraction)"
    )
    debug: bool = Field(
        default=False,
        description="Debug mode"
    )
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)"
    )
    
    # Configuration File
    config_file: Optional[str] = Field(
        default="config/settings.yaml",
        env="ENTITY_EXTRACTION_CONFIG_FILE",
        description="Path to YAML configuration file"
    )
    
    # Service URLs for inter-service communication
    log_service_url: str = Field(
        default="http://localhost:8001",
        env="LOG_SERVICE_URL",
        description="Log service URL"
    )
    supabase_service_url: str = Field(
        default="http://localhost:8002",
        env="SUPABASE_SERVICE_URL",
        description="Supabase service URL"
    )
    
    # Database Configuration
    store_extraction_results: bool = Field(
        default=True,
        description="Store extraction results in database"
    )
    extraction_retention_days: int = Field(
        default=30,
        gt=0,
        description="Days to retain extraction results"
    )
    
    # Security Configuration
    enable_rate_limiting: bool = Field(
        default=True,
        description="Enable rate limiting"
    )
    rate_limit_requests: int = Field(
        default=100,
        gt=0,
        description="Requests per minute per client"
    )
    max_request_size: int = Field(
        default=104857600,  # 100MB (increased for large PDF processing)
        gt=0,
        description="Maximum request size in bytes"
    )
    
    # Entity Types Configuration
    supported_entity_types: List[str] = Field(
        default=[
            "case_citations",
            "statute_citations",
            "court_names",
            "judges",
            "attorneys",
            "parties",
            "dates",
            "monetary_amounts",
            "legal_doctrines",
            "procedural_terms",
            "contracts",
            "agreements",
            "legal_references",
            "jurisdictions",
            "legal_standards",
            "evidence_types",
            "motion_types",
            "filing_deadlines",
            "legal_precedents",
            "constitutional_references",
            "regulatory_citations",
            "administrative_codes",
            "local_ordinances",
            "international_law",
            "treaty_references",
            "arbitration_clauses",
            "settlement_terms",
            "damages_calculations",
            "legal_fees",
            "court_costs",
            "legal_entities"
        ],
        description="Supported legal entity types for extraction"
    )
    
    # Sub-configuration objects
    extraction: ExtractionSettings = Field(
        default_factory=ExtractionSettings,
        description="Entity extraction configuration"
    )
    ai: AISettings = Field(
        default_factory=AISettings,
        description="AI and LLM configuration"
    )
    patterns: PatternSettings = Field(
        default_factory=PatternSettings,
        description="Pattern configuration"
    )
    regex: RegexEngineSettings = Field(
        default_factory=RegexEngineSettings,
        description="Regex engine configuration"
    )
    performance: PerformanceSettings = Field(
        default_factory=PerformanceSettings,
        description="Performance configuration"
    )
    logging: LoggingSettings = Field(
        default_factory=LoggingSettings,
        description="Logging configuration"
    )
    health: HealthCheckSettings = Field(
        default_factory=HealthCheckSettings,
        description="Health check configuration"
    )
    llama_local: LlamaLocalSettings = Field(
        default_factory=LlamaLocalSettings,
        description="Local Llama model configuration with breakthrough performance"
    )
    routing: IntelligentRoutingSettings = Field(
        default_factory=IntelligentRoutingSettings,
        description="Intelligent document routing configuration (DIS v2.0.0)"
    )
    vllm_direct: VLLMDirectSettings = Field(
        default_factory=VLLMDirectSettings,
        description="Direct vLLM integration configuration (DIS v2.0.0)"
    )
    chunking: ChunkingIntegrationSettings = Field(
        default_factory=ChunkingIntegrationSettings,
        description="Chunking service integration configuration (DIS v2.0.0)"
    )
    supabase: SupabaseSettings = Field(
        default_factory=SupabaseSettings,
        description="Supabase database configuration (DIS v2.0.0)"
    )

    model_config = SettingsConfigDict(
        env_prefix="ENTITY_EXTRACTION_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__"
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    def validate_production_config(self) -> List[str]:
        """Validate configuration for production environment."""
        issues = []
        
        if self.is_production:
            # Entity Extraction specific validations
            if self.extraction.max_concurrent_extractions > 50:
                issues.append("max_concurrent_extractions should not exceed 50 in production")
            
            if self.ai.ai_timeout_seconds > 2700:
                issues.append("ai_timeout_seconds should not exceed 2700 seconds (45 minutes) in production")
            
            if self.performance.max_memory_usage_mb > 8192:  # 8GB
                issues.append("max_memory_usage_mb should not exceed 8192 MB in production")
            
            if self.logging.log_request_body or self.logging.log_response_body:
                issues.append("Request/response body logging should be disabled in production for privacy")
            
            if not self.enable_rate_limiting:
                issues.append("Rate limiting should be enabled in production")
            
            if self.extraction.default_confidence_threshold < 0.5:
                issues.append("Confidence threshold should be at least 0.5 in production")
        
        return issues
    
    def get_service_urls(self) -> Dict[str, str]:
        """Get all service URLs for inter-service communication."""
        return {
            "log": self.log_service_url,
            "supabase": self.supabase_service_url
        }
    
    def get_extraction_config(self) -> Dict[str, Any]:
        """Get extraction configuration as dictionary."""
        return self.extraction.model_dump()
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI configuration as dictionary."""
        return self.ai.model_dump()
    
    def get_pattern_config(self) -> Dict[str, Any]:
        """Get pattern configuration as dictionary."""
        return self.patterns.model_dump()
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration as dictionary."""
        return self.performance.model_dump()
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration as dictionary."""
        return self.logging.model_dump()
    
    def get_health_config(self) -> Dict[str, Any]:
        """Get health check configuration as dictionary."""
        return self.health.model_dump()
    
    def get_llama_local_config(self) -> Dict[str, Any]:
        """Get local Llama configuration as dictionary."""
        return self.llama_local.model_dump()

    def get_regex_config(self) -> Dict[str, Any]:
        """Get regex engine configuration as dictionary."""
        return self.regex.model_dump()

    def get_vllm_config(self) -> Dict[str, Any]:
        """Get vLLM direct integration configuration as dictionary."""
        return self.vllm_direct.model_dump()

    def get_routing_config(self) -> Dict[str, Any]:
        """Get intelligent routing configuration as dictionary."""
        return self.routing.model_dump()

    def get_chunking_config(self) -> Dict[str, Any]:
        """Get chunking integration configuration as dictionary."""
        return self.chunking.model_dump()

    def get_supabase_config(self) -> Dict[str, Any]:
        """Get Supabase configuration as dictionary."""
        return self.supabase.model_dump()


# Type alias for backwards compatibility
Settings = EntityExtractionServiceSettings


@lru_cache()
def get_settings() -> EntityExtractionServiceSettings:
    """
    Get cached application settings.
    
    Returns:
        EntityExtractionServiceSettings: Application configuration instance
    """
    return EntityExtractionServiceSettings()


def validate_extraction_mode(mode: str) -> bool:
    """
    Validate extraction mode.
    
    Args:
        mode: Extraction mode to validate
        
    Returns:
        bool: True if valid mode
    """
    settings = get_settings()
    return mode in settings.extraction.available_extraction_modes


def validate_entity_types(entity_types: List[str]) -> bool:
    """
    Validate requested entity types.
    
    Args:
        entity_types: List of entity types to validate
        
    Returns:
        bool: True if all entity types are supported
    """
    settings = get_settings()
    return all(et in settings.supported_entity_types for et in entity_types)


def get_service_url(service_name: str) -> Optional[str]:
    """
    Get URL for a specific service.
    
    Args:
        service_name: Name of the service
        
    Returns:
        Optional[str]: Service URL if found
    """
    settings = get_settings()
    return settings.get_service_urls().get(service_name)


def validate_confidence_threshold(threshold: float) -> bool:
    """
    Validate confidence threshold value.
    
    Args:
        threshold: Confidence threshold to validate
        
    Returns:
        bool: True if valid threshold
    """
    settings = get_settings()
    return settings.extraction.min_confidence_threshold <= threshold <= 1.0


def validate_production_readiness() -> Dict[str, Any]:
    """
    Comprehensive production readiness validation.
    
    Returns:
        Dict[str, Any]: Validation results with issues and recommendations
    """
    settings = get_settings()
    issues = settings.validate_production_config()
    
    return {
        "is_production_ready": len(issues) == 0,
        "environment": settings.environment,
        "issues": issues,
        "recommendations": [
            "Review all configuration values for production environment",
            "Ensure proper monitoring and alerting is configured",
            "Verify all service dependencies are available",
            "Test extraction performance under expected load",
            "Validate pattern loading and caching performance",
            "Review security settings and rate limiting"
        ]
    }


def reload_settings() -> EntityExtractionServiceSettings:
    """
    Reload settings by clearing cache and creating new instance.

    Returns:
        EntityExtractionServiceSettings: New settings instance
    """
    get_settings.cache_clear()
    return get_settings()


def get_runtime_config() -> EntityExtractionServiceSettings:
    """
    Get runtime configuration.

    This function provides backwards compatibility for code that expects
    get_runtime_config(). It returns the same settings object as get_settings().

    The runtime_config has the same structure with these key attributes:
    - runtime_config.chunking: Chunking configuration
    - runtime_config.vllm: vLLM configuration (accessed via vllm_direct)

    Returns:
        EntityExtractionServiceSettings: Runtime configuration instance
    """
    return get_settings()


def get_config() -> EntityExtractionServiceSettings:
    """
    Get application configuration (alias for get_settings).

    This function provides backwards compatibility for code that expects
    get_config(). It returns the same settings object as get_settings().

    Returns:
        EntityExtractionServiceSettings: Configuration instance
    """
    return get_settings()