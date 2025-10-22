#!/usr/bin/env python3
"""Test script for the centralized extraction configuration system."""

import os
from pathlib import Path

# Add parent directory to path for imports

from src.core.config import (
    get_config, 
    reload_config,
    ExtractionServiceConfig,
    ProcessingMode
)


def test_default_configuration():
    """Test loading default configuration with environment variables."""
    print("\n=== Testing Default Configuration ===")
    
    config = get_settings()
    
    print("\n1. vLLM Settings (Conservative Defaults):")
    print(f"   - Base URL: {config.vllm.base_url}")
    print(f"   - Max concurrent requests: {config.vllm.max_concurrent_requests}")
    print(f"   - Request delay: {config.vllm.request_delay_ms}ms")
    print(f"   - Requests per minute: {config.vllm.requests_per_minute}")
    print(f"   - Circuit breaker enabled: {config.vllm.enable_circuit_breaker}")
    print(f"   - Failure threshold: {config.vllm.failure_threshold}")
    
    print("\n2. Chunking Settings:")
    print(f"   - Max chunk size: {config.chunking.max_chunk_size}")
    print(f"   - Chunk overlap: {config.chunking.chunk_overlap}")
    print(f"   - Batch size: {config.chunking.batch_size}")
    
    print("\n3. Extraction Settings:")
    print(f"   - Default mode: {config.extraction.default_mode}")
    print(f"   - Available modes: {config.extraction.available_modes}")
    print(f"   - Confidence thresholds: min={config.extraction.min_confidence}, "
          f"default={config.extraction.default_confidence}, high={config.extraction.high_confidence}")
    
    print("\n4. Performance Settings:")
    print(f"   - Processing mode: {config.performance.processing_mode}")
    print(f"   - Max concurrent requests: {config.performance.max_concurrent_requests}")
    print(f"   - Max workers: {config.performance.max_workers}")
    print(f"   - Cache enabled: {config.performance.enable_response_cache}")
    print(f"   - Rate limiting enabled: {config.performance.enable_rate_limiting}")
    
    print("\n5. Runtime Settings:")
    print(f"   - Service name: {config.runtime.service_name}")
    print(f"   - Host: {config.runtime.host}:{config.runtime.port}")
    print(f"   - Debug mode: {config.runtime.debug}")
    print(f"   - Log level: {config.runtime.log_level}")


def test_yaml_configuration():
    """Test loading configuration from YAML file."""
    print("\n=== Testing YAML Configuration Loading ===")
    
    yaml_path = Path("/srv/luris/be/entity-extraction-service/config/extraction_service.yaml")
    
    if yaml_path.exists():
        config = ExtractionServiceConfig.from_yaml(yaml_path)
        print(f"✓ Successfully loaded configuration from {yaml_path}")
        print(f"  Processing mode: {config.performance.processing_mode}")
        print(f"  vLLM max concurrent: {config.vllm.max_concurrent_requests}")
        print(f"  Circuit breaker: {config.vllm.enable_circuit_breaker}")
    else:
        print(f"✗ YAML config file not found at {yaml_path}")


def test_environment_override():
    """Test environment variable overrides."""
    print("\n=== Testing Environment Variable Overrides ===")
    
    # Set some environment variables
    os.environ["VLLM_MAX_CONCURRENT_REQUESTS"] = "1"
    os.environ["PERFORMANCE_PROCESSING_MODE"] = "throttled"
    os.environ["VLLM_REQUEST_DELAY_MS"] = "1000"
    
    # Reload configuration
    config = reload_config()
    
    print("✓ Environment variables applied:")
    print(f"  VLLM max concurrent requests: {config.vllm.max_concurrent_requests}")
    print(f"  Processing mode: {config.performance.processing_mode}")
    print(f"  Request delay: {config.vllm.request_delay_ms}ms")


def test_configuration_validation():
    """Test configuration validation."""
    print("\n=== Testing Configuration Validation ===")
    
    config = get_settings()
    errors = config.validate()
    
    if not errors:
        print("✓ Configuration is valid")
    else:
        print("✗ Validation errors found:")
        for error in errors:
            print(f"  - {error}")


def test_processing_modes():
    """Test different processing modes."""
    print("\n=== Testing Processing Mode Application ===")
    
    # Test throttled mode
    config = ExtractionServiceConfig()
    config.performance.processing_mode = ProcessingMode.THROTTLED.value
    config.vllm.max_concurrent_requests = 10  # Will be limited
    config.apply_processing_mode()
    print(f"\n1. THROTTLED mode:")
    print(f"   Max concurrent (limited): {config.vllm.max_concurrent_requests}")
    print(f"   Request delay (minimum): {config.vllm.request_delay_ms}ms")
    
    # Test normal mode
    config = ExtractionServiceConfig()
    config.performance.processing_mode = ProcessingMode.NORMAL.value
    config.vllm.max_concurrent_requests = 10  # Will be limited
    config.apply_processing_mode()
    print(f"\n2. NORMAL mode:")
    print(f"   Max concurrent (limited): {config.vllm.max_concurrent_requests}")
    print(f"   Request delay (minimum): {config.vllm.request_delay_ms}ms")
    
    # Test performance mode
    config = ExtractionServiceConfig()
    config.performance.processing_mode = ProcessingMode.PERFORMANCE.value
    config.vllm.max_concurrent_requests = 10  # No limits
    config.apply_processing_mode()
    print(f"\n3. PERFORMANCE mode:")
    print(f"   Max concurrent (no limit): {config.vllm.max_concurrent_requests}")
    print(f"   Request delay: {config.vllm.request_delay_ms}ms")


def test_config_export():
    """Test exporting configuration to YAML."""
    print("\n=== Testing Configuration Export ===")
    
    config = get_settings()
    export_path = Path("/srv/luris/be/entity-extraction-service/tests/exported_config.yaml")
    
    config.to_yaml(export_path)
    print(f"✓ Configuration exported to {export_path}")
    
    # Load it back to verify
    loaded_config = ExtractionServiceConfig.from_yaml(export_path)
    print(f"✓ Exported configuration successfully loaded back")
    print(f"  Processing mode: {loaded_config.performance.processing_mode}")


def main():
    """Run all configuration tests."""
    print("=" * 60)
    print("Entity Extraction Service Configuration System Test")
    print("=" * 60)
    
    test_default_configuration()
    test_yaml_configuration()
    test_environment_override()
    test_configuration_validation()
    test_processing_modes()
    test_config_export()
    
    print("\n" + "=" * 60)
    print("Configuration System Test Complete")
    print("=" * 60)
    
    # Show final configuration summary
    config = get_settings()
    print("\n📋 Final Configuration Summary:")
    print(f"  Mode: {config.performance.processing_mode}")
    print(f"  vLLM Concurrent: {config.vllm.max_concurrent_requests}")
    print(f"  Request Delay: {config.vllm.request_delay_ms}ms")
    print(f"  RPM Limit: {config.vllm.requests_per_minute}")
    print(f"  Circuit Breaker: {'✓' if config.vllm.enable_circuit_breaker else '✗'}")
    print(f"  Response Cache: {'✓' if config.performance.enable_response_cache else '✗'}")
    print(f"  Rate Limiting: {'✓' if config.performance.enable_rate_limiting else '✗'}")


if __name__ == "__main__":
    main()