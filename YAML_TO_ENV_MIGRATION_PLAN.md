# YAML to Environment Variables Migration Plan
**Entity Extraction Service Configuration Migration**

**Date:** 2025-10-15
**Author:** System Architect
**Objective:** Migrate from YAML configuration to environment variables only

---

## Executive Summary

This migration plan provides a comprehensive strategy to remove YAML configuration loading from `src/core/config.py` and migrate all 234 YAML settings to environment variables in `.env`. The service currently uses Pydantic BaseSettings which supports automatic environment variable loading with the `ENTITY_EXTRACTION_` prefix and `__` nested delimiter.

**Key Benefits:**
- Simplifies configuration management
- Eliminates dual configuration sources (YAML + env vars)
- Improves production deployment practices (12-factor app compliance)
- Reduces code complexity by ~240 lines
- Maintains full backward compatibility through Pydantic defaults

---

## Part 1: Complete YAML → Environment Variable Mapping

### Naming Convention
All environment variables use:
- **Prefix:** `ENTITY_EXTRACTION_`
- **Nested Delimiter:** `__` (double underscore)
- **Example:** `extraction.chunk_size` → `ENTITY_EXTRACTION_EXTRACTION__CHUNK_SIZE`

### 1.1 Service Configuration (10 variables)

| YAML Path | Environment Variable | Current Value | Type |
|-----------|---------------------|---------------|------|
| `service_name` | `ENTITY_EXTRACTION_SERVICE_NAME` | `"entity-extraction-service"` | string |
| `port` | `ENTITY_EXTRACTION_PORT` | `8007` | int |
| `debug` | `ENTITY_EXTRACTION_DEBUG` | `false` | bool |
| `environment` | `ENTITY_EXTRACTION_ENVIRONMENT` | `"development"` | string |
| `secret_key` | `ENTITY_EXTRACTION_SECRET_KEY` | `"change-me-in-production"` | string |
| `host` | `ENTITY_EXTRACTION_HOST` | `"0.0.0.0"` | string |
| `service_version` | `ENTITY_EXTRACTION_SERVICE_VERSION` | `"2.0.0"` | string |
| `log_service_url` | `ENTITY_EXTRACTION_LOG_SERVICE_URL` | `"http://localhost:8001"` | string |
| `supabase_service_url` | `ENTITY_EXTRACTION_SUPABASE_SERVICE_URL` | `"http://localhost:8002"` | string |
| `config_file` | `ENTITY_EXTRACTION_CONFIG_FILE` | `"config/settings.yaml"` | string |

**Notes:**
- `config_file` will be deprecated after migration
- `secret_key` is required by BaseServiceSettings (inherited field)

### 1.2 Extraction Settings (22 variables)

| YAML Path | Environment Variable | Current Value | Type |
|-----------|---------------------|---------------|------|
| `extraction.default_extraction_mode` | `ENTITY_EXTRACTION_EXTRACTION__DEFAULT_EXTRACTION_MODE` | `"ai_enhanced"` | string |
| `extraction.available_extraction_modes` | `ENTITY_EXTRACTION_EXTRACTION__AVAILABLE_EXTRACTION_MODES` | `["ai_enhanced", "multi_pass"]` | list[str] |
| `extraction.default_confidence_threshold` | `ENTITY_EXTRACTION_EXTRACTION__DEFAULT_CONFIDENCE_THRESHOLD` | `0.7` | float |
| `extraction.min_confidence_threshold` | `ENTITY_EXTRACTION_EXTRACTION__MIN_CONFIDENCE_THRESHOLD` | `0.3` | float |
| `extraction.high_confidence_threshold` | `ENTITY_EXTRACTION_EXTRACTION__HIGH_CONFIDENCE_THRESHOLD` | `0.9` | float |
| `extraction.max_content_length` | `ENTITY_EXTRACTION_EXTRACTION__MAX_CONTENT_LENGTH` | `1000000` | int |
| `extraction.max_context_window` | `ENTITY_EXTRACTION_EXTRACTION__MAX_CONTEXT_WINDOW` | `1000` | int |
| `extraction.chunk_size` | `ENTITY_EXTRACTION_EXTRACTION__CHUNK_SIZE` | `5000` | int |
| `extraction.chunk_overlap` | `ENTITY_EXTRACTION_EXTRACTION__CHUNK_OVERLAP` | `500` | int |
| `extraction.max_concurrent_extractions` | `ENTITY_EXTRACTION_EXTRACTION__MAX_CONCURRENT_EXTRACTIONS` | `10` | int |
| `extraction.processing_timeout_seconds` | `ENTITY_EXTRACTION_EXTRACTION__PROCESSING_TIMEOUT_SECONDS` | `1200` | int |
| `extraction.batch_size` | `ENTITY_EXTRACTION_EXTRACTION__BATCH_SIZE` | `50` | int |
| `extraction.enable_multi_pass` | `ENTITY_EXTRACTION_EXTRACTION__ENABLE_MULTI_PASS` | `true` | bool |
| `extraction.extraction_passes` | `ENTITY_EXTRACTION_EXTRACTION__EXTRACTION_PASSES` | `["actors", "citations", "concepts"]` | list[str] |
| `extraction.multi_pass_chunk_size` | `ENTITY_EXTRACTION_EXTRACTION__MULTI_PASS_CHUNK_SIZE` | `4000` | int |
| `extraction.multi_pass_max_tokens` | `ENTITY_EXTRACTION_EXTRACTION__MULTI_PASS_MAX_TOKENS` | `500` | int |
| `extraction.multi_pass_temperature` | `ENTITY_EXTRACTION_EXTRACTION__MULTI_PASS_TEMPERATURE` | `0.0` | float |
| `extraction.uvicorn_timeout_keep_alive` | `ENTITY_EXTRACTION_UVICORN_TIMEOUT` | `1800` | int |

**Notes:**
- List values can be JSON-encoded strings or comma-separated values
- `uvicorn_timeout_keep_alive` has custom env mapping to `ENTITY_EXTRACTION_UVICORN_TIMEOUT`

### 1.3 AI Settings (17 variables)

| YAML Path | Environment Variable | Current Value | Type |
|-----------|---------------------|---------------|------|
| `ai.enable_ai_enhancement` | `ENTITY_EXTRACTION_AI__ENABLE_AI_ENHANCEMENT` | `true` | bool |
| `ai.ai_timeout_seconds` | `ENTITY_EXTRACTION_AI__AI_TIMEOUT_SECONDS` | `1200` | int |
| `ai.ai_max_retries` | `ENTITY_EXTRACTION_AI__AI_MAX_RETRIES` | `3` | int |
| `ai.ai_retry_delay_seconds` | `ENTITY_EXTRACTION_AI__AI_RETRY_DELAY_SECONDS` | `1.0` | float |
| `ai.enable_ai_fallback` | `ENTITY_EXTRACTION_AI__ENABLE_AI_FALLBACK` | `true` | bool |
| `ai.default_temperature` | `ENTITY_EXTRACTION_AI__DEFAULT_TEMPERATURE` | `0.1` | float |
| `ai.default_max_tokens` | `ENTITY_EXTRACTION_AI__DEFAULT_MAX_TOKENS` | `4096` | int |
| `ai.llm_max_response_tokens` | `ENTITY_EXTRACTION_AI__LLM_MAX_RESPONSE_TOKENS` | `8000` | int |
| `ai.prompt_template_max_tokens` | `ENTITY_EXTRACTION_AI__PROMPT_TEMPLATE_MAX_TOKENS` | `50000` | int |
| `ai.default_top_p` | `ENTITY_EXTRACTION_AI__DEFAULT_TOP_P` | `0.9` | float |
| `ai.default_extraction_model` | `ENTITY_EXTRACTION_AI__DEFAULT_EXTRACTION_MODEL` | `"llama-3-8b"` | string |
| `ai.default_validation_model` | `ENTITY_EXTRACTION_AI__DEFAULT_VALIDATION_MODEL` | `"llama-3-8b"` | string |
| `ai.model_rotation_enabled` | `ENTITY_EXTRACTION_AI__MODEL_ROTATION_ENABLED` | `false` | bool |
| `ai.max_context_examples` | `ENTITY_EXTRACTION_AI__MAX_CONTEXT_EXAMPLES` | `5` | int |
| `ai.enable_context_enrichment` | `ENTITY_EXTRACTION_AI__ENABLE_CONTEXT_ENRICHMENT` | `true` | bool |
| `ai.context_similarity_threshold` | `ENTITY_EXTRACTION_AI__CONTEXT_SIMILARITY_THRESHOLD` | `0.8` | float |
| `ai.prefer_local_processing` | `ENTITY_EXTRACTION_AI__PREFER_LOCAL_PROCESSING` | `true` | bool |
| `ai.local_processing_mode` | `ENTITY_EXTRACTION_AI__LOCAL_PROCESSING_MODE` | `"hybrid"` | string |

### 1.4 Pattern Settings (14 variables)

| YAML Path | Environment Variable | Current Value | Type |
|-----------|---------------------|---------------|------|
| `patterns.patterns_directory` | `ENTITY_EXTRACTION_PATTERNS__PATTERNS_DIRECTORY` | `"src/patterns"` | string |
| `patterns.enable_pattern_validation` | `PATTERN_VALIDATE_ON_LOAD` | `true` | bool |
| `patterns.enable_pattern_compilation` | `ENTITY_EXTRACTION_PATTERNS__ENABLE_PATTERN_COMPILATION` | `true` | bool |
| `patterns.pattern_loading_timeout` | `ENTITY_EXTRACTION_PATTERNS__PATTERN_LOADING_TIMEOUT` | `1200` | int |
| `patterns.enable_pattern_caching` | `PATTERN_ENABLE_CACHING` | `true` | bool |
| `patterns.pattern_cache_size` | `PATTERN_CACHE_SIZE` | `1000` | int |
| `patterns.pattern_cache_ttl_seconds` | `PATTERN_CACHE_TTL` | `3600` | int |
| `patterns.enable_threaded_loading` | `ENTITY_EXTRACTION_PATTERNS__ENABLE_THREADED_LOADING` | `true` | bool |
| `patterns.max_loader_threads` | `PATTERN_MAX_WORKERS` | `4` | int |
| `patterns.enable_pattern_auto_reload` | `PATTERN_AUTO_RELOAD` | `false` | bool |
| `patterns.pattern_reload_interval_seconds` | `ENTITY_EXTRACTION_PATTERNS__PATTERN_RELOAD_INTERVAL_SECONDS` | `300` | int |
| `patterns.min_pattern_confidence` | `ENTITY_EXTRACTION_PATTERNS__MIN_PATTERN_CONFIDENCE` | `0.5` | float |
| `patterns.max_patterns_per_file` | `ENTITY_EXTRACTION_PATTERNS__MAX_PATTERNS_PER_FILE` | `500` | int |
| `patterns.pattern_lazy_loading` | `PATTERN_LAZY_LOADING` | `false` | bool |
| `patterns.pattern_compression_enabled` | `PATTERN_COMPRESSION_ENABLED` | `false` | bool |

**Notes:**
- Several pattern settings already have direct `env=` mappings without `ENTITY_EXTRACTION_` prefix
- These are intentional for direct pattern loader integration

### 1.5 Performance Settings (30 variables)

| YAML Path | Environment Variable | Current Value | Type |
|-----------|---------------------|---------------|------|
| `performance.enable_performance_monitoring` | `ENTITY_EXTRACTION_PERFORMANCE__ENABLE_PERFORMANCE_MONITORING` | `true` | bool |
| `performance.performance_sample_rate` | `ENTITY_EXTRACTION_PERFORMANCE__PERFORMANCE_SAMPLE_RATE` | `0.1` | float |
| `performance.enable_metrics_export` | `ENTITY_EXTRACTION_PERFORMANCE__ENABLE_METRICS_EXPORT` | `true` | bool |
| `performance.max_memory_usage_mb` | `ENTITY_EXTRACTION_PERFORMANCE__MAX_MEMORY_USAGE_MB` | `2048` | int |
| `performance.memory_check_interval_seconds` | `ENTITY_EXTRACTION_PERFORMANCE__MEMORY_CHECK_INTERVAL_SECONDS` | `60` | int |
| `performance.enable_memory_cleanup` | `ENTITY_EXTRACTION_PERFORMANCE__ENABLE_MEMORY_CLEANUP` | `true` | bool |
| `performance.max_worker_threads` | `ENTITY_EXTRACTION_PERFORMANCE__MAX_WORKER_THREADS` | `10` | int |
| `performance.thread_pool_size` | `ENTITY_EXTRACTION_PERFORMANCE__THREAD_POOL_SIZE` | `8` | int |
| `performance.enable_result_caching` | `ENTITY_EXTRACTION_PERFORMANCE__ENABLE_RESULT_CACHING` | `true` | bool |
| `performance.result_cache_size` | `ENTITY_EXTRACTION_PERFORMANCE__RESULT_CACHE_SIZE` | `1000` | int |
| `performance.result_cache_ttl_seconds` | `ENTITY_EXTRACTION_PERFORMANCE__RESULT_CACHE_TTL_SECONDS` | `1800` | int |
| `performance.multipass_max_iterations` | `MULTIPASS_MAX_ITERATIONS` | `8` | int |
| `performance.multipass_convergence_threshold` | `MULTIPASS_CONVERGENCE_THRESHOLD` | `0.95` | float |
| `performance.multipass_enable_parallel` | `MULTIPASS_ENABLE_PARALLEL` | `true` | bool |
| `performance.multipass_batch_size` | `MULTIPASS_BATCH_SIZE` | `10` | int |
| `performance.multipass_timeout_per_pass` | `MULTIPASS_TIMEOUT_PER_PASS` | `300` | int |
| `performance.dedup_similarity_threshold` | `DEDUP_SIMILARITY_THRESHOLD` | `0.85` | float |
| `performance.dedup_algorithm` | `DEDUP_ALGORITHM` | `"fuzzy"` | string |
| `performance.dedup_preserve_highest_confidence` | `DEDUP_PRESERVE_HIGHEST_CONFIDENCE` | `true` | bool |
| `performance.dedup_cross_type_dedup` | `DEDUP_CROSS_TYPE_DEDUP` | `false` | bool |
| `performance.response_parser_strict_mode` | `RESPONSE_PARSER_STRICT_MODE` | `false` | bool |
| `performance.response_parser_auto_repair` | `RESPONSE_PARSER_AUTO_REPAIR` | `true` | bool |
| `performance.response_parser_max_repair_attempts` | `RESPONSE_PARSER_MAX_REPAIR_ATTEMPTS` | `3` | int |
| `performance.response_validation_schema_strict` | `RESPONSE_VALIDATION_SCHEMA_STRICT` | `false` | bool |
| `performance.model_context_window_buffer` | `MODEL_CONTEXT_WINDOW_BUFFER` | `1000` | int |
| `performance.model_output_token_buffer` | `MODEL_OUTPUT_TOKEN_BUFFER` | `500` | int |
| `performance.model_enable_dynamic_batching` | `MODEL_ENABLE_DYNAMIC_BATCHING` | `true` | bool |
| `performance.model_batch_timeout_ms` | `MODEL_BATCH_TIMEOUT_MS` | `100` | int |
| `performance.quality_min_entity_confidence` | `QUALITY_MIN_ENTITY_CONFIDENCE` | `0.5` | float |
| `performance.quality_enable_confidence_calibration` | `QUALITY_ENABLE_CONFIDENCE_CALIBRATION` | `true` | bool |
| `performance.quality_reject_partial_matches` | `QUALITY_REJECT_PARTIAL_MATCHES` | `false` | bool |

**Notes:**
- Many performance settings have direct `env=` mappings without prefix for component-specific configuration

### 1.6 Logging Settings (16 variables)

| YAML Path | Environment Variable | Current Value | Type |
|-----------|---------------------|---------------|------|
| `logging.log_level` | `ENTITY_EXTRACTION_LOGGING__LOG_LEVEL` | `"INFO"` | string |
| `logging.enable_structured_logging` | `ENTITY_EXTRACTION_LOGGING__ENABLE_STRUCTURED_LOGGING` | `true` | bool |
| `logging.log_format` | `ENTITY_EXTRACTION_LOGGING__LOG_FORMAT` | `"json"` | string |
| `logging.log_extraction_details` | `ENTITY_EXTRACTION_LOGGING__LOG_EXTRACTION_DETAILS` | `true` | bool |
| `logging.log_pattern_matching` | `ENTITY_EXTRACTION_LOGGING__LOG_PATTERN_MATCHING` | `false` | bool |
| `logging.log_ai_requests` | `ENTITY_EXTRACTION_LOGGING__LOG_AI_REQUESTS` | `true` | bool |
| `logging.log_performance_metrics` | `ENTITY_EXTRACTION_LOGGING__LOG_PERFORMANCE_METRICS` | `true` | bool |
| `logging.enable_request_id_logging` | `ENTITY_EXTRACTION_LOGGING__ENABLE_REQUEST_ID_LOGGING` | `true` | bool |
| `logging.log_request_body` | `ENTITY_EXTRACTION_LOGGING__LOG_REQUEST_BODY` | `false` | bool |
| `logging.log_response_body` | `ENTITY_EXTRACTION_LOGGING__LOG_RESPONSE_BODY` | `false` | bool |
| `logging.enable_file_logging` | `ENTITY_EXTRACTION_LOGGING__ENABLE_FILE_LOGGING` | `true` | bool |
| `logging.log_file_path` | `ENTITY_EXTRACTION_LOGGING__LOG_FILE_PATH` | `"logs/entity-extraction.log"` | string |
| `logging.log_rotation_size_mb` | `ENTITY_EXTRACTION_LOGGING__LOG_ROTATION_SIZE_MB` | `100` | int |
| `logging.log_retention_days` | `ENTITY_EXTRACTION_LOGGING__LOG_RETENTION_DAYS` | `30` | int |

### 1.7 Health Check Settings (13 variables)

| YAML Path | Environment Variable | Current Value | Type |
|-----------|---------------------|---------------|------|
| `health.enable_health_checks` | `ENTITY_EXTRACTION_HEALTH__ENABLE_HEALTH_CHECKS` | `true` | bool |
| `health.health_check_interval_seconds` | `ENTITY_EXTRACTION_HEALTH__HEALTH_CHECK_INTERVAL_SECONDS` | `30` | int |
| `health.health_check_timeout_seconds` | `ENTITY_EXTRACTION_HEALTH__HEALTH_CHECK_TIMEOUT_SECONDS` | `5` | int |
| `health.check_pattern_loader` | `ENTITY_EXTRACTION_HEALTH__CHECK_PATTERN_LOADER` | `true` | bool |
| `health.check_ai_services` | `ENTITY_EXTRACTION_HEALTH__CHECK_AI_SERVICES` | `true` | bool |
| `health.check_database_connection` | `ENTITY_EXTRACTION_HEALTH__CHECK_DATABASE_CONNECTION` | `true` | bool |
| `health.check_memory_usage` | `ENTITY_EXTRACTION_HEALTH__CHECK_MEMORY_USAGE` | `true` | bool |
| `health.memory_warning_threshold_percent` | `ENTITY_EXTRACTION_HEALTH__MEMORY_WARNING_THRESHOLD_PERCENT` | `80.0` | float |
| `health.memory_critical_threshold_percent` | `ENTITY_EXTRACTION_HEALTH__MEMORY_CRITICAL_THRESHOLD_PERCENT` | `95.0` | float |
| `health.extraction_latency_warning_ms` | `ENTITY_EXTRACTION_HEALTH__EXTRACTION_LATENCY_WARNING_MS` | `5000` | int |
| `health.extraction_latency_critical_ms` | `ENTITY_EXTRACTION_HEALTH__EXTRACTION_LATENCY_CRITICAL_MS` | `15000` | int |

### 1.8 Local Llama Settings (32 variables)

| YAML Path | Environment Variable | Current Value | Type |
|-----------|---------------------|---------------|------|
| `llama_local.enable_local_processing` | `ENTITY_EXTRACTION_LLAMA_LOCAL__ENABLE_LOCAL_PROCESSING` | `true` | bool |
| `llama_local.model_path` | `ENTITY_EXTRACTION_LLAMA_LOCAL__MODEL_PATH` | `"Qwen3-VL-8B-Instruct-FP8-GGUF"` | string |
| `llama_local.model_file` | `ENTITY_EXTRACTION_LLAMA_LOCAL__MODEL_FILE` | `"Qwen3-VL-8B-Instruct-FP8-Q4_K_M.gguf"` | string |
| `llama_local.auto_load_model` | `ENTITY_EXTRACTION_LLAMA_LOCAL__AUTO_LOAD_MODEL` | `true` | bool |
| `llama_local.n_gpu_layers` | `ENTITY_EXTRACTION_LLAMA_LOCAL__N_GPU_LAYERS` | `64` | int |
| `llama_local.n_parallel` | `ENTITY_EXTRACTION_LLAMA_LOCAL__N_PARALLEL` | `64` | int |
| `llama_local.n_batch` | `ENTITY_EXTRACTION_LLAMA_LOCAL__N_BATCH` | `65536` | int |
| `llama_local.n_ubatch` | `ENTITY_EXTRACTION_LLAMA_LOCAL__N_UBATCH` | `16384` | int |
| `llama_local.n_ctx` | `ENTITY_EXTRACTION_LLAMA_LOCAL__N_CTX` | `1024` | int |
| `llama_local.n_threads` | `ENTITY_EXTRACTION_LLAMA_LOCAL__N_THREADS` | `20` | int |
| `llama_local.n_threads_batch` | `ENTITY_EXTRACTION_LLAMA_LOCAL__N_THREADS_BATCH` | `32` | int |
| `llama_local.use_mmap` | `ENTITY_EXTRACTION_LLAMA_LOCAL__USE_MMAP` | `false` | bool |
| `llama_local.use_mlock` | `ENTITY_EXTRACTION_LLAMA_LOCAL__USE_MLOCK` | `true` | bool |
| `llama_local.numa` | `ENTITY_EXTRACTION_LLAMA_LOCAL__NUMA` | `true` | bool |
| `llama_local.rope_freq_base` | `ENTITY_EXTRACTION_LLAMA_LOCAL__ROPE_FREQ_BASE` | `100000.0` | float |
| `llama_local.rope_scaling_type` | `ENTITY_EXTRACTION_LLAMA_LOCAL__ROPE_SCALING_TYPE` | `"dynamic"` | string |
| `llama_local.flash_attn` | `ENTITY_EXTRACTION_LLAMA_LOCAL__FLASH_ATTN` | `true` | bool |
| `llama_local.cache_type_k` | `ENTITY_EXTRACTION_LLAMA_LOCAL__CACHE_TYPE_K` | `"f16"` | string |
| `llama_local.cache_type_v` | `ENTITY_EXTRACTION_LLAMA_LOCAL__CACHE_TYPE_V` | `"f16"` | string |
| `llama_local.seed` | `ENTITY_EXTRACTION_LLAMA_LOCAL__SEED` | `-1` | int |
| `llama_local.verbose` | `ENTITY_EXTRACTION_LLAMA_LOCAL__VERBOSE` | `false` | bool |
| `llama_local.model_load_timeout` | `ENTITY_EXTRACTION_LLAMA_LOCAL__MODEL_LOAD_TIMEOUT` | `1200` | int |
| `llama_local.generation_timeout` | `ENTITY_EXTRACTION_LLAMA_LOCAL__GENERATION_TIMEOUT` | `1200` | int |
| `llama_local.max_retries` | `ENTITY_EXTRACTION_LLAMA_LOCAL__MAX_RETRIES` | `3` | int |
| `llama_local.health_check_interval` | `ENTITY_EXTRACTION_LLAMA_LOCAL__HEALTH_CHECK_INTERVAL` | `60` | int |
| `llama_local.min_memory_gb` | `ENTITY_EXTRACTION_LLAMA_LOCAL__MIN_MEMORY_GB` | `4.0` | float |
| `llama_local.max_memory_gb` | `ENTITY_EXTRACTION_LLAMA_LOCAL__MAX_MEMORY_GB` | `16.0` | float |
| `llama_local.memory_check_interval` | `ENTITY_EXTRACTION_LLAMA_LOCAL__MEMORY_CHECK_INTERVAL` | `30` | int |
| `llama_local.enable_fallback_to_remote` | `ENTITY_EXTRACTION_LLAMA_LOCAL__ENABLE_FALLBACK_TO_REMOTE` | `true` | bool |
| `llama_local.fallback_threshold_ms` | `ENTITY_EXTRACTION_LLAMA_LOCAL__FALLBACK_THRESHOLD_MS` | `5000` | int |

### 1.9 Regex Engine Settings (5 variables)

| YAML Path | Environment Variable | Current Value | Type |
|-----------|---------------------|---------------|------|
| `regex.regex_cache_size` | `REGEX_CACHE_SIZE` | `500` | int |
| `regex.regex_timeout_ms` | `REGEX_TIMEOUT_MS` | `1000` | int |
| `regex.regex_enable_multiline` | `REGEX_ENABLE_MULTILINE` | `true` | bool |
| `regex.regex_enable_dotall` | `REGEX_ENABLE_DOTALL` | `false` | bool |
| `regex.regex_max_recursion_depth` | `REGEX_MAX_RECURSION_DEPTH` | `100` | int |

**Notes:**
- All regex settings have direct `env=` mappings without prefix

### 1.10 Intelligent Routing Settings (11 variables)

| YAML Path | Environment Variable | Current Value | Type |
|-----------|---------------------|---------------|------|
| `routing.size_threshold_very_small` | `ENTITY_EXTRACTION_ROUTING__SIZE_THRESHOLD_VERY_SMALL` | `5000` | int |
| `routing.size_threshold_small` | `ENTITY_EXTRACTION_ROUTING__SIZE_THRESHOLD_SMALL` | `50000` | int |
| `routing.size_threshold_medium` | `ENTITY_EXTRACTION_ROUTING__SIZE_THRESHOLD_MEDIUM` | `150000` | int |
| `routing.enable_intelligent_routing` | `ENTITY_EXTRACTION_ROUTING__ENABLE_INTELLIGENT_ROUTING` | `true` | bool |
| `routing.default_routing_mode` | `ENTITY_EXTRACTION_ROUTING__DEFAULT_ROUTING_MODE` | `"intelligent"` | string |
| `routing.extraction_chunker_size` | `ENTITY_EXTRACTION_ROUTING__EXTRACTION_CHUNKER_SIZE` | `8000` | int |
| `routing.extraction_chunker_overlap` | `ENTITY_EXTRACTION_ROUTING__EXTRACTION_CHUNKER_OVERLAP` | `500` | int |
| `routing.enable_three_wave_prompts` | `ENTITY_EXTRACTION_ROUTING__ENABLE_THREE_WAVE_PROMPTS` | `true` | bool |
| `routing.wave_1_entity_types` | `ENTITY_EXTRACTION_ROUTING__WAVE_1_ENTITY_TYPES` | `["PERSON", "JUDGE", ...]` | list[str] |
| `routing.wave_2_entity_types` | `ENTITY_EXTRACTION_ROUTING__WAVE_2_ENTITY_TYPES` | `["CASE_CITATION", ...]` | list[str] |
| `routing.wave_3_entity_types` | `ENTITY_EXTRACTION_ROUTING__WAVE_3_ENTITY_TYPES` | `["LEGAL_DOCTRINE", ...]` | list[str] |

### 1.11 vLLM Direct Settings (36 variables)

| YAML Path | Environment Variable | Current Value | Type |
|-----------|---------------------|---------------|------|
| `vllm_direct.enable_vllm_direct` | `ENTITY_EXTRACTION_VLLM_DIRECT__ENABLE_VLLM_DIRECT` | `true` | bool |
| `vllm_direct.vllm_host` | `ENTITY_EXTRACTION_VLLM_DIRECT__VLLM_HOST` | `"10.10.0.87"` | string |
| `vllm_direct.vllm_port` | `ENTITY_EXTRACTION_VLLM_DIRECT__VLLM_PORT` | `8080` | int |
| `vllm_direct.vllm_model_name` | `VLLM_MODEL` | `"Qwen3-VL-8B-Instruct-FP8"` | string |
| `vllm_direct.vllm_temperature` | `VLLM_DEFAULT_TEMPERATURE` | `0.0` | float |
| `vllm_direct.vllm_seed` | `VLLM_SEED` | `42` | int |
| `vllm_direct.vllm_max_tokens` | `VLLM_DEFAULT_MAX_TOKENS` | `4096` | int |
| `vllm_direct.vllm_top_p` | `VLLM_DEFAULT_TOP_P` | `0.95` | float |
| `vllm_direct.vllm_top_k` | `VLLM_DEFAULT_TOP_K` | `40` | int |
| `vllm_direct.vllm_repetition_penalty` | `VLLM_DEFAULT_REPETITION_PENALTY` | `1.0` | float |
| `vllm_direct.vllm_max_model_len` | `VLLM_MAX_MODEL_LEN` | `131072` | int |
| `vllm_direct.vllm_gpu_memory_utilization` | `VLLM_GPU_MEMORY_UTILIZATION` | `0.80` | float |
| `vllm_direct.vllm_enable_prefix_caching` | `VLLM_ENABLE_PREFIX_CACHING` | `true` | bool |
| `vllm_direct.vllm_enable_chunked_prefill` | `VLLM_ENABLE_CHUNKED_PREFILL` | `true` | bool |
| `vllm_direct.vllm_max_num_batched_tokens` | `VLLM_MAX_NUM_BATCHED_TOKENS` | `8192` | int |
| `vllm_direct.vllm_max_num_seqs` | `VLLM_MAX_NUM_SEQS` | `256` | int |
| `vllm_direct.vllm_block_size` | `VLLM_BLOCK_SIZE` | `16` | int |
| `vllm_direct.vllm_swap_space` | `VLLM_SWAP_SPACE` | `4` | int |
| `vllm_direct.vllm_enforce_eager` | `VLLM_ENFORCE_EAGER` | `false` | bool |
| `vllm_direct.vllm_gpu_id` | `VLLM_GPU_ID` | `1` | int |
| `vllm_direct.vllm_gpu_memory_threshold` | `VLLM_GPU_MEMORY_THRESHOLD` | `0.90` | float |
| `vllm_direct.vllm_enable_gpu_monitoring` | `VLLM_ENABLE_GPU_MONITORING` | `false` | bool |
| `vllm_direct.vllm_gpu_monitor_interval` | `VLLM_GPU_MONITOR_INTERVAL` | `30` | int |
| `vllm_direct.vllm_timeout_seconds` | `VLLM_HTTP_TIMEOUT` | `300` | int |
| `vllm_direct.vllm_max_retries` | `VLLM_HTTP_MAX_RETRIES` | `3` | int |
| `vllm_direct.vllm_retry_delay` | `VLLM_HTTP_RETRY_DELAY` | `1.0` | float |
| `vllm_direct.vllm_connect_timeout` | `VLLM_HTTP_CONNECT_TIMEOUT` | `10` | int |
| `vllm_direct.vllm_connection_pool_size` | `ENTITY_EXTRACTION_VLLM_DIRECT__VLLM_CONNECTION_POOL_SIZE` | `10` | int |
| `vllm_direct.vllm_chars_per_token` | `VLLM_CHARS_PER_TOKEN` | `4.0` | float |
| `vllm_direct.vllm_token_overlap_percent` | `VLLM_TOKEN_OVERLAP_PERCENT` | `0.1` | float |
| `vllm_direct.vllm_prefill_rate` | `VLLM_PREFILL_RATE` | `19000` | int |
| `vllm_direct.vllm_decode_rate` | `VLLM_DECODE_RATE` | `150` | int |
| `vllm_direct.vllm_warmup_enabled` | `VLLM_WARMUP_ENABLED` | `true` | bool |
| `vllm_direct.vllm_warmup_max_tokens` | `VLLM_WARMUP_MAX_TOKENS` | `10` | int |
| `vllm_direct.enforce_reproducibility` | `ENTITY_EXTRACTION_VLLM_DIRECT__ENFORCE_REPRODUCIBILITY` | `true` | bool |
| `vllm_direct.reproducibility_validation` | `ENTITY_EXTRACTION_VLLM_DIRECT__REPRODUCIBILITY_VALIDATION` | `true` | bool |

**Notes:**
- Most vLLM settings have direct `env=` mappings without prefix for vLLM client integration
- GPU ID set to 1 (not 0) per current .env configuration

### 1.12 Chunking Integration Settings (23 variables)

| YAML Path | Environment Variable | Current Value | Type |
|-----------|---------------------|---------------|------|
| `chunking.default_chunking_strategy` | `ENTITY_EXTRACTION_CHUNKING__DEFAULT_CHUNKING_STRATEGY` | `"extraction"` | string |
| `chunking.available_chunking_strategies` | `ENTITY_EXTRACTION_CHUNKING__AVAILABLE_CHUNKING_STRATEGIES` | `["extraction", "semantic", ...]` | list[str] |
| `chunking.enable_contextual_enhancement` | `ENTITY_EXTRACTION_CHUNKING__ENABLE_CONTEXTUAL_ENHANCEMENT` | `false` | bool |
| `chunking.contextual_enhancement_template` | `ENTITY_EXTRACTION_CHUNKING__CONTEXTUAL_ENHANCEMENT_TEMPLATE` | `"document_context"` | string |
| `chunking.chunk_quality_threshold` | `ENTITY_EXTRACTION_CHUNKING__CHUNK_QUALITY_THRESHOLD` | `0.7` | float |
| `chunking.enable_chunk_validation` | `ENTITY_EXTRACTION_CHUNKING__ENABLE_CHUNK_VALIDATION` | `true` | bool |
| `chunking.chunking_max_size` | `CHUNKING_MAX_SIZE` | `2000` | int |
| `chunking.chunking_min_size` | `CHUNKING_MIN_SIZE` | `100` | int |
| `chunking.chunking_overlap` | `CHUNKING_OVERLAP` | `500` | int |
| `chunking.chunking_enable_smart` | `CHUNKING_ENABLE_SMART` | `true` | bool |
| `chunking.chunking_preserve_sentences` | `CHUNKING_PRESERVE_SENTENCES` | `true` | bool |
| `chunking.chunking_preserve_paragraphs` | `CHUNKING_PRESERVE_PARAGRAPHS` | `false` | bool |
| `chunking.chunking_batch_size` | `CHUNKING_BATCH_SIZE` | `5` | int |
| `chunking.chunking_max_chunks_per_doc` | `CHUNKING_MAX_CHUNKS_PER_DOC` | `100` | int |
| `chunking.smart_chunk_threshold` | `SMART_CHUNK_THRESHOLD` | `50000` | int |
| `chunking.context_window_size` | `CONTEXT_WINDOW_SIZE` | `128000` | int |
| `chunking.context_window_buffer` | `CONTEXT_WINDOW_BUFFER` | `0.8` | float |
| `chunking.chunking_bypass` | `CHUNKING_BYPASS` | `true` | bool |
| `chunking.force_unified_processing` | `FORCE_UNIFIED_PROCESSING` | `true` | bool |
| `chunking.disable_micro_chunking` | `DISABLE_MICRO_CHUNKING` | `true` | bool |
| `chunking.discovery_chunk_size` | `DISCOVERY_CHUNK_SIZE` | `3000` | int |
| `chunking.max_unified_document_size` | `MAX_UNIFIED_DOCUMENT_SIZE` | `1000000` | int |

**Notes:**
- Many chunking settings have direct `env=` mappings without prefix

### 1.13 Supabase Settings (18 variables)

| YAML Path | Environment Variable | Current Value | Type |
|-----------|---------------------|---------------|------|
| `supabase.supabase_url` | `SUPABASE_URL` | `"https://tqfshsnwyhfnkchaiudg.supabase.co"` | string |
| `supabase.supabase_api_key` | `SUPABASE_API_KEY` | `""` | string |
| `supabase.supabase_service_key` | `SUPABASE_SERVICE_KEY` | `""` | string |
| `supabase.simple_op_timeout` | `ENTITY_EXTRACTION_SUPABASE__SIMPLE_OP_TIMEOUT` | `8` | int |
| `supabase.complex_op_timeout` | `ENTITY_EXTRACTION_SUPABASE__COMPLEX_OP_TIMEOUT` | `20` | int |
| `supabase.batch_op_timeout` | `ENTITY_EXTRACTION_SUPABASE__BATCH_OP_TIMEOUT` | `30` | int |
| `supabase.vector_op_timeout` | `ENTITY_EXTRACTION_SUPABASE__VECTOR_OP_TIMEOUT` | `25` | int |
| `supabase.max_retries` | `ENTITY_EXTRACTION_SUPABASE__MAX_RETRIES` | `3` | int |
| `supabase.backoff_max` | `ENTITY_EXTRACTION_SUPABASE__BACKOFF_MAX` | `30` | int |
| `supabase.backoff_factor` | `ENTITY_EXTRACTION_SUPABASE__BACKOFF_FACTOR` | `2.0` | float |
| `supabase.max_connections` | `ENTITY_EXTRACTION_SUPABASE__MAX_CONNECTIONS` | `30` | int |
| `supabase.connection_timeout` | `ENTITY_EXTRACTION_SUPABASE__CONNECTION_TIMEOUT` | `5` | int |
| `supabase.pool_recycle` | `ENTITY_EXTRACTION_SUPABASE__POOL_RECYCLE` | `300` | int |
| `supabase.circuit_breaker_enabled` | `ENTITY_EXTRACTION_SUPABASE__CIRCUIT_BREAKER_ENABLED` | `true` | bool |
| `supabase.circuit_breaker_failure_threshold` | `ENTITY_EXTRACTION_SUPABASE__CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `5` | int |
| `supabase.circuit_breaker_recovery_timeout` | `ENTITY_EXTRACTION_SUPABASE__CIRCUIT_BREAKER_RECOVERY_TIMEOUT` | `60` | int |
| `supabase.batch_size` | `ENTITY_EXTRACTION_SUPABASE__BATCH_SIZE` | `100` | int |
| `supabase.enable_metrics` | `ENTITY_EXTRACTION_SUPABASE__ENABLE_METRICS` | `true` | bool |
| `supabase.enable_slow_query_log` | `ENTITY_EXTRACTION_SUPABASE__ENABLE_SLOW_QUERY_LOG` | `true` | bool |
| `supabase.slow_query_threshold` | `ENTITY_EXTRACTION_SUPABASE__SLOW_QUERY_THRESHOLD` | `5.0` | float |

**Notes:**
- Core Supabase credentials already exist in .env
- These are additional Supabase client configuration options

### 1.14 Database & Security Settings (5 variables)

| YAML Path | Environment Variable | Current Value | Type |
|-----------|---------------------|---------------|------|
| `store_extraction_results` | `ENTITY_EXTRACTION_STORE_EXTRACTION_RESULTS` | `true` | bool |
| `extraction_retention_days` | `ENTITY_EXTRACTION_EXTRACTION_RETENTION_DAYS` | `30` | int |
| `enable_rate_limiting` | `ENTITY_EXTRACTION_ENABLE_RATE_LIMITING` | `true` | bool |
| `rate_limit_requests` | `ENTITY_EXTRACTION_RATE_LIMIT_REQUESTS` | `100` | int |
| `max_request_size` | `ENTITY_EXTRACTION_MAX_REQUEST_SIZE` | `10485760` | int |

### 1.15 Supported Entity Types (1 variable)

| YAML Path | Environment Variable | Current Value | Type |
|-----------|---------------------|---------------|------|
| `supported_entity_types` | `ENTITY_EXTRACTION_SUPPORTED_ENTITY_TYPES` | `["case_citations", "statute_citations", ...]` | list[str] |

**Notes:**
- 31 entity types total
- Can be represented as JSON array or comma-separated string

---

## Part 2: Code Removal Plan

### 2.1 Methods to Remove from config.py

**Location:** `/srv/luris/be/entity-extraction-service/src/core/config.py`

#### Remove these methods from `EntityExtractionServiceSettings` class:

1. **`__init__()` method** (lines 1642-1655)
   - **Action:** REMOVE ENTIRELY
   - **Reason:** Pydantic BaseSettings handles env var loading automatically
   - **Lines to delete:** 1642-1655 (14 lines)

2. **`_load_yaml_config()` method** (lines 1657-1679)
   - **Action:** REMOVE ENTIRELY
   - **Reason:** YAML loading no longer needed
   - **Lines to delete:** 1657-1679 (23 lines)

3. **`_create_default_config_file()` method** (lines 1681-1694)
   - **Action:** REMOVE ENTIRELY
   - **Reason:** No longer creating YAML config files
   - **Lines to delete:** 1681-1694 (14 lines)

4. **`_generate_default_yaml_config()` method** (lines 1696-1879)
   - **Action:** REMOVE ENTIRELY
   - **Reason:** Hardcoded YAML template no longer needed
   - **Lines to delete:** 1696-1879 (184 lines)

**Total lines removed:** ~240 lines

### 2.2 Import to Remove

```python
# Line 7 - Remove this import
import yaml
```

**Note:** Keep `from pathlib import Path` as it may be used elsewhere in the file.

### 2.3 Simplified EntityExtractionServiceSettings Class

After removal, the class should look like this:

```python
class EntityExtractionServiceSettings(BaseSettings):
    """Main configuration class for Entity Extraction Service."""

    # Service Identification
    service_name: str = Field(
        default="document-intelligence-service",
        description="Service name (formerly entity-extraction-service)"
    )
    # ... all other fields remain unchanged ...

    model_config = SettingsConfigDict(
        env_prefix="ENTITY_EXTRACTION_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__"
    )

    # NO __init__ method needed - Pydantic handles everything automatically

    def validate_production_config(self) -> List[str]:
        """Validate configuration for production environment."""
        # Keep this method as-is
        ...
```

### 2.4 config_file Field Deprecation

**Option 1: Remove config_file field entirely**
```python
# DELETE these lines (1500-1504)
config_file: Optional[str] = Field(
    default="config/settings.yaml",
    env="ENTITY_EXTRACTION_CONFIG_FILE",
    description="Path to YAML configuration file"
)
```

**Option 2: Keep for backward compatibility with deprecation warning**
```python
# MODIFY to include deprecation notice
config_file: Optional[str] = Field(
    default=None,
    env="ENTITY_EXTRACTION_CONFIG_FILE",
    description="[DEPRECATED] YAML configuration no longer supported. Use environment variables."
)
```

**Recommendation:** Option 1 (remove entirely) for clean migration.

---

## Part 3: .env File Migration

### 3.1 Current .env Status

**Current .env file has:** 113 variables (lines 1-208)

**YAML settings.yaml has:** 234 settings

**Gap:** ~121 settings not yet in .env

### 3.2 .env File Organization

The migrated .env should maintain the same structure with these sections:

```bash
# ===============================================================================
# SECTION 1: SERVICE CONFIGURATION (10 variables)
# ===============================================================================

# ===============================================================================
# SECTION 2: EXTRACTION SETTINGS (22 variables)
# ===============================================================================

# ===============================================================================
# SECTION 3: AI SETTINGS (17 variables)
# ===============================================================================

# ===============================================================================
# SECTION 4: PATTERN SETTINGS (14 variables)
# ===============================================================================

# ===============================================================================
# SECTION 5: PERFORMANCE SETTINGS (30 variables)
# ===============================================================================

# ===============================================================================
# SECTION 6: LOGGING SETTINGS (16 variables)
# ===============================================================================

# ===============================================================================
# SECTION 7: HEALTH CHECK SETTINGS (13 variables)
# ===============================================================================

# ===============================================================================
# SECTION 8: LOCAL LLAMA SETTINGS (32 variables)
# ===============================================================================

# ===============================================================================
# SECTION 9: REGEX ENGINE SETTINGS (5 variables)
# ===============================================================================

# ===============================================================================
# SECTION 10: INTELLIGENT ROUTING SETTINGS (11 variables)
# ===============================================================================

# ===============================================================================
# SECTION 11: vLLM DIRECT SETTINGS (36 variables)
# ===============================================================================

# ===============================================================================
# SECTION 12: CHUNKING INTEGRATION SETTINGS (23 variables)
# ===============================================================================

# ===============================================================================
# SECTION 13: SUPABASE SETTINGS (18 variables)
# ===============================================================================

# ===============================================================================
# SECTION 14: DATABASE & SECURITY SETTINGS (5 variables)
# ===============================================================================

# ===============================================================================
# SECTION 15: SUPPORTED ENTITY TYPES (1 variable - JSON array)
# ===============================================================================

# ===============================================================================
# TOTAL: ~253 VARIABLES (includes existing + new from YAML)
# ===============================================================================
```

### 3.3 Settings Already in .env (No Changes Needed)

These settings are already properly configured in the current .env:
- All vLLM Direct Integration settings (Section 3)
- All Core Extraction Settings (Section 4)
- All Chunking Configuration (Section 5)
- Service URLs (Section 6)
- Performance & Resource Management (Section 7)
- Security settings (Section 8)
- vLLM Advanced Configuration (Section 9)
- Pattern System Configuration (Section 10)
- Regex Engine Configuration (Section 11)
- Performance & Model Tuning (Section 12)

### 3.4 Settings to ADD to .env

The following settings need to be added as they only exist in YAML:

#### Service Configuration Additions
```bash
ENTITY_EXTRACTION_SERVICE_NAME=entity-extraction-service
ENTITY_EXTRACTION_HOST=0.0.0.0
ENTITY_EXTRACTION_SERVICE_VERSION=2.0.0
ENTITY_EXTRACTION_SECRET_KEY=change-me-in-production
```

#### Extraction Settings Additions
```bash
ENTITY_EXTRACTION_EXTRACTION__AVAILABLE_EXTRACTION_MODES=["ai_enhanced", "multi_pass"]
ENTITY_EXTRACTION_EXTRACTION__ENABLE_MULTI_PASS=true
ENTITY_EXTRACTION_EXTRACTION__EXTRACTION_PASSES=["actors", "citations", "concepts"]
ENTITY_EXTRACTION_EXTRACTION__MULTI_PASS_CHUNK_SIZE=4000
ENTITY_EXTRACTION_EXTRACTION__MULTI_PASS_MAX_TOKENS=500
ENTITY_EXTRACTION_EXTRACTION__MULTI_PASS_TEMPERATURE=0.0
```

#### AI Settings Additions
```bash
ENTITY_EXTRACTION_AI__PREFER_LOCAL_PROCESSING=true
ENTITY_EXTRACTION_AI__LOCAL_PROCESSING_MODE=hybrid
```

#### Logging Settings (ALL need to be added)
```bash
ENTITY_EXTRACTION_LOGGING__LOG_LEVEL=INFO
ENTITY_EXTRACTION_LOGGING__ENABLE_STRUCTURED_LOGGING=true
ENTITY_EXTRACTION_LOGGING__LOG_FORMAT=json
ENTITY_EXTRACTION_LOGGING__LOG_EXTRACTION_DETAILS=true
ENTITY_EXTRACTION_LOGGING__LOG_PATTERN_MATCHING=false
ENTITY_EXTRACTION_LOGGING__LOG_AI_REQUESTS=true
ENTITY_EXTRACTION_LOGGING__LOG_PERFORMANCE_METRICS=true
ENTITY_EXTRACTION_LOGGING__ENABLE_REQUEST_ID_LOGGING=true
ENTITY_EXTRACTION_LOGGING__LOG_REQUEST_BODY=false
ENTITY_EXTRACTION_LOGGING__LOG_RESPONSE_BODY=false
ENTITY_EXTRACTION_LOGGING__ENABLE_FILE_LOGGING=true
ENTITY_EXTRACTION_LOGGING__LOG_FILE_PATH=logs/entity-extraction.log
ENTITY_EXTRACTION_LOGGING__LOG_ROTATION_SIZE_MB=100
ENTITY_EXTRACTION_LOGGING__LOG_RETENTION_DAYS=30
```

#### Health Check Settings (ALL need to be added)
```bash
ENTITY_EXTRACTION_HEALTH__ENABLE_HEALTH_CHECKS=true
ENTITY_EXTRACTION_HEALTH__HEALTH_CHECK_INTERVAL_SECONDS=30
ENTITY_EXTRACTION_HEALTH__HEALTH_CHECK_TIMEOUT_SECONDS=5
ENTITY_EXTRACTION_HEALTH__CHECK_PATTERN_LOADER=true
ENTITY_EXTRACTION_HEALTH__CHECK_AI_SERVICES=true
ENTITY_EXTRACTION_HEALTH__CHECK_DATABASE_CONNECTION=true
ENTITY_EXTRACTION_HEALTH__CHECK_MEMORY_USAGE=true
ENTITY_EXTRACTION_HEALTH__MEMORY_WARNING_THRESHOLD_PERCENT=80.0
ENTITY_EXTRACTION_HEALTH__MEMORY_CRITICAL_THRESHOLD_PERCENT=95.0
ENTITY_EXTRACTION_HEALTH__EXTRACTION_LATENCY_WARNING_MS=5000
ENTITY_EXTRACTION_HEALTH__EXTRACTION_LATENCY_CRITICAL_MS=15000
```

#### Local Llama Settings (ALL need to be added)
```bash
ENTITY_EXTRACTION_LLAMA_LOCAL__ENABLE_LOCAL_PROCESSING=true
ENTITY_EXTRACTION_LLAMA_LOCAL__MODEL_PATH=Qwen3-VL-8B-Instruct-FP8-GGUF
ENTITY_EXTRACTION_LLAMA_LOCAL__MODEL_FILE=Qwen3-VL-8B-Instruct-FP8-Q4_K_M.gguf
ENTITY_EXTRACTION_LLAMA_LOCAL__AUTO_LOAD_MODEL=true
ENTITY_EXTRACTION_LLAMA_LOCAL__N_GPU_LAYERS=64
ENTITY_EXTRACTION_LLAMA_LOCAL__N_PARALLEL=64
ENTITY_EXTRACTION_LLAMA_LOCAL__N_BATCH=65536
ENTITY_EXTRACTION_LLAMA_LOCAL__N_UBATCH=16384
ENTITY_EXTRACTION_LLAMA_LOCAL__N_CTX=1024
ENTITY_EXTRACTION_LLAMA_LOCAL__N_THREADS=20
ENTITY_EXTRACTION_LLAMA_LOCAL__N_THREADS_BATCH=32
ENTITY_EXTRACTION_LLAMA_LOCAL__USE_MMAP=false
ENTITY_EXTRACTION_LLAMA_LOCAL__USE_MLOCK=true
ENTITY_EXTRACTION_LLAMA_LOCAL__NUMA=true
ENTITY_EXTRACTION_LLAMA_LOCAL__ROPE_FREQ_BASE=100000.0
ENTITY_EXTRACTION_LLAMA_LOCAL__ROPE_SCALING_TYPE=dynamic
ENTITY_EXTRACTION_LLAMA_LOCAL__FLASH_ATTN=true
ENTITY_EXTRACTION_LLAMA_LOCAL__CACHE_TYPE_K=f16
ENTITY_EXTRACTION_LLAMA_LOCAL__CACHE_TYPE_V=f16
ENTITY_EXTRACTION_LLAMA_LOCAL__SEED=-1
ENTITY_EXTRACTION_LLAMA_LOCAL__VERBOSE=false
ENTITY_EXTRACTION_LLAMA_LOCAL__MODEL_LOAD_TIMEOUT=1200
ENTITY_EXTRACTION_LLAMA_LOCAL__GENERATION_TIMEOUT=1200
ENTITY_EXTRACTION_LLAMA_LOCAL__MAX_RETRIES=3
ENTITY_EXTRACTION_LLAMA_LOCAL__HEALTH_CHECK_INTERVAL=60
ENTITY_EXTRACTION_LLAMA_LOCAL__MIN_MEMORY_GB=4.0
ENTITY_EXTRACTION_LLAMA_LOCAL__MAX_MEMORY_GB=16.0
ENTITY_EXTRACTION_LLAMA_LOCAL__MEMORY_CHECK_INTERVAL=30
ENTITY_EXTRACTION_LLAMA_LOCAL__ENABLE_FALLBACK_TO_REMOTE=true
ENTITY_EXTRACTION_LLAMA_LOCAL__FALLBACK_THRESHOLD_MS=5000
```

#### Intelligent Routing Settings (ALL need to be added)
```bash
ENTITY_EXTRACTION_ROUTING__SIZE_THRESHOLD_VERY_SMALL=5000
ENTITY_EXTRACTION_ROUTING__SIZE_THRESHOLD_SMALL=50000
ENTITY_EXTRACTION_ROUTING__SIZE_THRESHOLD_MEDIUM=150000
ENTITY_EXTRACTION_ROUTING__ENABLE_INTELLIGENT_ROUTING=true
ENTITY_EXTRACTION_ROUTING__DEFAULT_ROUTING_MODE=intelligent
ENTITY_EXTRACTION_ROUTING__EXTRACTION_CHUNKER_SIZE=8000
ENTITY_EXTRACTION_ROUTING__EXTRACTION_CHUNKER_OVERLAP=500
ENTITY_EXTRACTION_ROUTING__ENABLE_THREE_WAVE_PROMPTS=true
ENTITY_EXTRACTION_ROUTING__WAVE_1_ENTITY_TYPES=["PERSON", "JUDGE", "ATTORNEY", "PARTY", "COURT"]
ENTITY_EXTRACTION_ROUTING__WAVE_2_ENTITY_TYPES=["CASE_CITATION", "STATUTE_CITATION", "REGULATION"]
ENTITY_EXTRACTION_ROUTING__WAVE_3_ENTITY_TYPES=["LEGAL_DOCTRINE", "PROCEDURAL_TERM", "LEGAL_CONCEPT"]
```

#### Chunking Integration Additions
```bash
ENTITY_EXTRACTION_CHUNKING__DEFAULT_CHUNKING_STRATEGY=extraction
ENTITY_EXTRACTION_CHUNKING__AVAILABLE_CHUNKING_STRATEGIES=["extraction", "semantic", "legal", "hybrid", "simple"]
ENTITY_EXTRACTION_CHUNKING__ENABLE_CONTEXTUAL_ENHANCEMENT=false
ENTITY_EXTRACTION_CHUNKING__CONTEXTUAL_ENHANCEMENT_TEMPLATE=document_context
ENTITY_EXTRACTION_CHUNKING__CHUNK_QUALITY_THRESHOLD=0.7
ENTITY_EXTRACTION_CHUNKING__ENABLE_CHUNK_VALIDATION=true
```

#### Supabase Settings Additions
```bash
ENTITY_EXTRACTION_SUPABASE__SIMPLE_OP_TIMEOUT=8
ENTITY_EXTRACTION_SUPABASE__COMPLEX_OP_TIMEOUT=20
ENTITY_EXTRACTION_SUPABASE__BATCH_OP_TIMEOUT=30
ENTITY_EXTRACTION_SUPABASE__VECTOR_OP_TIMEOUT=25
ENTITY_EXTRACTION_SUPABASE__MAX_RETRIES=3
ENTITY_EXTRACTION_SUPABASE__BACKOFF_MAX=30
ENTITY_EXTRACTION_SUPABASE__BACKOFF_FACTOR=2.0
ENTITY_EXTRACTION_SUPABASE__MAX_CONNECTIONS=30
ENTITY_EXTRACTION_SUPABASE__CONNECTION_TIMEOUT=5
ENTITY_EXTRACTION_SUPABASE__POOL_RECYCLE=300
ENTITY_EXTRACTION_SUPABASE__CIRCUIT_BREAKER_ENABLED=true
ENTITY_EXTRACTION_SUPABASE__CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
ENTITY_EXTRACTION_SUPABASE__CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60
ENTITY_EXTRACTION_SUPABASE__BATCH_SIZE=100
ENTITY_EXTRACTION_SUPABASE__ENABLE_METRICS=true
ENTITY_EXTRACTION_SUPABASE__ENABLE_SLOW_QUERY_LOG=true
ENTITY_EXTRACTION_SUPABASE__SLOW_QUERY_THRESHOLD=5.0
```

#### Database & Security Additions
```bash
ENTITY_EXTRACTION_STORE_EXTRACTION_RESULTS=true
ENTITY_EXTRACTION_EXTRACTION_RETENTION_DAYS=30
```

#### Supported Entity Types Addition
```bash
ENTITY_EXTRACTION_SUPPORTED_ENTITY_TYPES=["case_citations","statute_citations","constitutional_references","regulatory_citations","administrative_codes","local_ordinances","international_law","treaty_references","court_names","judges","attorneys","parties","legal_entities","dates","filing_deadlines","monetary_amounts","damages_calculations","legal_fees","court_costs","legal_doctrines","procedural_terms","legal_references","jurisdictions","legal_standards","evidence_types","motion_types","legal_precedents","contracts","agreements","arbitration_clauses","settlement_terms"]
```

---

## Part 4: Migration Execution Steps

### Step 1: Backup Current Configuration
```bash
# Backup existing files
cp /srv/luris/be/entity-extraction-service/.env /srv/luris/be/entity-extraction-service/.env.backup
cp /srv/luris/be/entity-extraction-service/config/settings.yaml /srv/luris/be/entity-extraction-service/config/settings.yaml.backup
cp /srv/luris/be/entity-extraction-service/src/core/config.py /srv/luris/be/entity-extraction-service/src/core/config.py.backup
```

### Step 2: Update .env File
```bash
# Add all missing environment variables from Part 3.4
# Use the complete mapping tables from Part 1
# Maintain section organization for readability
```

### Step 3: Update config.py
```bash
# Remove YAML-related methods (Part 2)
# 1. Delete __init__ method (lines 1642-1655)
# 2. Delete _load_yaml_config method (lines 1657-1679)
# 3. Delete _create_default_config_file method (lines 1681-1694)
# 4. Delete _generate_default_yaml_config method (lines 1696-1879)
# 5. Remove 'import yaml' (line 7)
# 6. Optionally remove config_file field (lines 1500-1504)
```

### Step 4: Test Configuration Loading
```bash
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate

# Test configuration import
python -c "from src.core.config import get_settings; settings = get_settings(); print('✅ Config loaded successfully')"

# Verify all nested settings load correctly
python -c "
from src.core.config import get_settings
settings = get_settings()
print(f'Port: {settings.port}')
print(f'Extraction mode: {settings.extraction.default_extraction_mode}')
print(f'AI temperature: {settings.ai.default_temperature}')
print(f'Pattern cache size: {settings.patterns.pattern_cache_size}')
print(f'vLLM GPU ID: {settings.vllm_direct.vllm_gpu_id}')
print('✅ All nested settings accessible')
"
```

### Step 5: Restart Service
```bash
# Stop service
sudo systemctl stop luris-entity-extraction

# Start service with new configuration
sudo systemctl start luris-entity-extraction

# Check service status
sudo systemctl status luris-entity-extraction

# Monitor logs for startup
sudo journalctl -u luris-entity-extraction -f
```

### Step 6: Validate Service Health
```bash
# Check health endpoint
curl http://localhost:8007/health

# Verify configuration endpoint (if available)
curl http://localhost:8007/api/config

# Test extraction endpoint
curl -X POST http://localhost:8007/api/v2/process/extract \
  -H "Content-Type: application/json" \
  -d '{"content": "Test document", "entity_types": ["case_citations"]}'
```

### Step 7: Archive YAML Configuration
```bash
# Move YAML file to archive (do not delete immediately)
mkdir -p /srv/luris/be/entity-extraction-service/config/archive
mv /srv/luris/be/entity-extraction-service/config/settings.yaml \
   /srv/luris/be/entity-extraction-service/config/archive/settings.yaml.deprecated

# Add README explaining deprecation
cat > /srv/luris/be/entity-extraction-service/config/archive/README.md << 'EOF'
# Deprecated YAML Configuration

This directory contains deprecated YAML configuration files.

**YAML configuration is no longer supported as of v2.1.0.**

All configuration is now managed through environment variables in `.env`.

See `/srv/luris/be/entity-extraction-service/.env` for current configuration.

For migration details, see `YAML_TO_ENV_MIGRATION_PLAN.md` in the service root.
EOF
```

---

## Part 5: Validation Checklist

### 5.1 Pre-Migration Validation

- [ ] Current service is running and healthy
- [ ] Backup of .env file created
- [ ] Backup of config.py created
- [ ] Backup of settings.yaml created
- [ ] Document current service behavior for comparison

### 5.2 Migration Validation

- [ ] All 234 YAML settings mapped to environment variables
- [ ] .env file updated with missing variables
- [ ] YAML loading methods removed from config.py
- [ ] `import yaml` removed from config.py
- [ ] `config_file` field removed or deprecated
- [ ] Configuration loads without errors
- [ ] All nested settings accessible via Pydantic

### 5.3 Post-Migration Validation

- [ ] Service starts successfully
- [ ] Health endpoint returns healthy status
- [ ] Configuration values match pre-migration behavior
- [ ] Extraction endpoint processes requests correctly
- [ ] All service URLs are correct
- [ ] Database connections work
- [ ] AI/vLLM integration functions properly
- [ ] Pattern loading succeeds
- [ ] Logging configuration applied correctly
- [ ] Performance settings active
- [ ] No YAML-related errors in logs

### 5.4 Regression Testing

- [ ] Test all extraction modes (ai_enhanced, multi_pass)
- [ ] Test with various document sizes
- [ ] Test all entity types
- [ ] Test chunking strategies
- [ ] Test routing logic
- [ ] Test health checks
- [ ] Test performance monitoring
- [ ] Test error handling and fallbacks
- [ ] Verify metrics collection
- [ ] Check log output format

---

## Part 6: Risk Assessment

### 6.1 Low Risk Items
- **Pydantic BaseSettings automatic env var loading** - Well-tested, production-ready
- **Environment variable naming** - Standard convention, clear mapping
- **Nested delimiter `__`** - Pydantic built-in feature
- **Default values in Field()** - Existing safety net

### 6.2 Medium Risk Items
- **List/Array environment variables** - JSON parsing may need testing
  - **Mitigation:** Test all list fields explicitly
  - **Fallback:** Use comma-separated strings if JSON fails

- **Missing environment variables** - Service may fail to start
  - **Mitigation:** Pydantic provides defaults for all fields
  - **Validation:** Pre-flight config check before migration

- **Environment-specific overrides** - YAML had dev/staging/production sections
  - **Mitigation:** Use separate .env files per environment
  - **Alternative:** Continue using ENVIRONMENT variable to switch behavior in code

### 6.3 High Risk Items
**NONE IDENTIFIED** - This is a straightforward configuration migration with multiple safety mechanisms:
- All fields have default values
- Pydantic validates all types
- Service can run with defaults if env vars missing
- Rollback is simple (restore backups)

### 6.4 Rollback Plan

If migration fails:

1. **Immediate Rollback:**
   ```bash
   # Stop service
   sudo systemctl stop luris-entity-extraction

   # Restore backups
   cp /srv/luris/be/entity-extraction-service/.env.backup \
      /srv/luris/be/entity-extraction-service/.env
   cp /srv/luris/be/entity-extraction-service/src/core/config.py.backup \
      /srv/luris/be/entity-extraction-service/src/core/config.py
   cp /srv/luris/be/entity-extraction-service/config/settings.yaml.backup \
      /srv/luris/be/entity-extraction-service/config/settings.yaml

   # Restart service
   sudo systemctl start luris-entity-extraction
   ```

2. **Verify Rollback:**
   ```bash
   # Check service health
   curl http://localhost:8007/health

   # Verify logs
   sudo journalctl -u luris-entity-extraction -n 50
   ```

3. **Analyze Failure:**
   - Check logs for specific configuration errors
   - Identify which settings caused issues
   - Fix individual settings in .env
   - Retry migration with fixes

---

## Part 7: Benefits of Migration

### 7.1 Operational Benefits
- **12-Factor App Compliance** - Strict separation of config from code
- **Container-Ready** - Easy Docker/Kubernetes deployment
- **Environment Parity** - Same codebase across dev/staging/production
- **Security** - No config files in version control (except .env.example)
- **Secrets Management** - Compatible with HashiCorp Vault, AWS Secrets Manager

### 7.2 Development Benefits
- **Simplified Configuration** - Single source of truth (.env)
- **Reduced Code Complexity** - ~240 lines removed from config.py
- **Better IDE Support** - Environment variables in .env are easier to edit
- **Clear Precedence** - Environment variables always override defaults
- **Easier Testing** - Override specific vars without touching files

### 7.3 Maintenance Benefits
- **No YAML Parsing Errors** - Eliminate yaml.safe_load() issues
- **Type Safety** - Pydantic validates all values at startup
- **Self-Documenting** - Field descriptions in Pydantic models
- **Easier Debugging** - Clear variable names match Field names exactly

---

## Part 8: Post-Migration Recommendations

### 8.1 Documentation Updates
- [ ] Update README.md with environment variable configuration instructions
- [ ] Create .env.example file with all variables and documentation
- [ ] Update deployment guides to use environment variables
- [ ] Document migration process for other services

### 8.2 Environment Management
- [ ] Create separate .env files for dev/staging/production
- [ ] Implement secrets management solution (Vault, AWS Secrets Manager)
- [ ] Add .env validation script to CI/CD pipeline
- [ ] Create environment variable documentation generator

### 8.3 Monitoring
- [ ] Add configuration validation to startup logging
- [ ] Monitor service behavior for configuration-related issues
- [ ] Track any performance differences post-migration
- [ ] Document any unexpected behavior changes

### 8.4 Future Improvements
- [ ] Consider creating .env.schema for validation
- [ ] Implement configuration hot-reload capability
- [ ] Add configuration diff tool for environment comparison
- [ ] Create automated .env generator from Pydantic models

---

## Summary

**Migration Scope:**
- **Total YAML Settings:** 234
- **Environment Variables to Add:** ~121
- **Code Lines to Remove:** ~240 lines
- **Estimated Migration Time:** 2-3 hours (including testing)
- **Risk Level:** LOW (with proper backups and validation)

**Key Success Factors:**
1. Complete .env file with all 253 variables
2. Removal of all YAML loading code
3. Thorough testing of nested configuration access
4. Service restart with health validation
5. Comprehensive regression testing

**Next Steps:**
1. Review and approve this migration plan
2. Schedule migration window (non-peak hours)
3. Execute backup procedures
4. Implement .env updates
5. Execute code changes
6. Validate and test
7. Monitor post-migration

---

**Document Version:** 1.0
**Last Updated:** 2025-10-15
**Approved By:** [System Architect]
**Implementation Date:** [To Be Scheduled]
