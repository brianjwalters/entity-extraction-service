#!/usr/bin/env python3
"""
Test Suite for vLLM Resilience System

Comprehensive tests for fallback strategies, retry logic,
and error recovery mechanisms.
"""

import asyncio
import json
import pytest
import time
from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from pathlib import Path

from src.core.vllm_resilience import (
    VLLMResilienceManager,
    RetryConfig,
    FallbackConfig,
    ResponseCache,
    ResponseValidator,
    ExponentialBackoff,
    FailureType,
    RecoveryStrategy,
    resilient_vllm_operation
)


class TestResponseValidator:
    """Test response validation functionality."""
    
    def test_valid_json_structure(self):
        """Test validation of correct JSON structure."""
        validator = ResponseValidator()
        
        # Valid response
        response = '{"entities": [{"text": "John Doe", "entity_type": "PERSON"}]}'
        valid, data, error = validator.validate_json_structure(response)
        
        assert valid is True
        assert data is not None
        assert "entities" in data
        assert len(data["entities"]) == 1
        assert error is None
    
    def test_invalid_json_structure(self):
        """Test detection of invalid JSON."""
        validator = ResponseValidator()
        
        # Invalid JSON
        response = '{"entities": [{"text": "John Doe", "entity_type": "PERSON"'
        valid, data, error = validator.validate_json_structure(response)
        
        assert valid is False
        assert data is None
        assert error is not None
        assert "Invalid JSON" in error
    
    def test_json_repair(self):
        """Test automatic JSON repair functionality."""
        validator = ResponseValidator()
        
        # JSON with markdown code blocks
        response = '```json\n{"entities": [{"text": "test", "entity_type": "TEST"}]}\n```'
        valid, data, error = validator.validate_json_structure(response)
        
        assert valid is True
        assert data is not None
        assert len(data["entities"]) == 1
    
    def test_empty_response_detection(self):
        """Test detection of empty responses."""
        validator = ResponseValidator()
        
        # Empty entities array
        assert validator.is_empty_response({"entities": []}) is True
        assert validator.is_empty_response({"entities": None}) is True
        assert validator.is_empty_response({}) is True
        
        # Non-empty response
        assert validator.is_empty_response({
            "entities": [{"text": "test", "entity_type": "TEST"}]
        }) is False
    
    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        validator = ResponseValidator()
        
        # Empty response
        assert validator.calculate_confidence({"entities": []}) == 0.0
        
        # Response with entities
        data = {
            "entities": [
                {"text": "test1", "confidence": 0.9},
                {"text": "test2", "confidence": 0.7},
                {"text": "test3", "confidence": 0.8}
            ]
        }
        confidence = validator.calculate_confidence(data)
        assert 0.7 < confidence < 0.9  # Should be average
    
    def test_field_name_variations(self):
        """Test handling of field name variations."""
        validator = ResponseValidator()
        
        # Response with "type" instead of "entity_type"
        response = '{"entities": [{"text": "John Doe", "type": "PERSON"}]}'
        valid, data, error = validator.validate_json_structure(response)
        
        assert valid is True
        assert data["entities"][0]["entity_type"] == "PERSON"
        
        # Response with "value" instead of "text"
        response = '{"entities": [{"value": "John Doe", "entity_type": "PERSON"}]}'
        valid, data, error = validator.validate_json_structure(response)
        
        assert valid is True
        assert data["entities"][0]["text"] == "John Doe"


class TestResponseCache:
    """Test caching functionality."""
    
    def test_cache_operations(self):
        """Test basic cache operations."""
        cache = ResponseCache(ttl_seconds=60)
        
        # Test set and get
        response = {"entities": [{"text": "test"}]}
        cache.set("content", "strategy", {}, response, 0.9)
        
        cached = cache.get("content", "strategy", {})
        assert cached is not None
        assert cached["entities"][0]["text"] == "test"
        
        # Test cache miss
        assert cache.get("different", "strategy", {}) is None
    
    def test_cache_expiration(self):
        """Test cache TTL expiration."""
        cache = ResponseCache(ttl_seconds=0)  # Immediate expiration
        
        response = {"entities": [{"text": "test"}]}
        cache.set("content", "strategy", {}, response, 0.9)
        
        # Should be expired immediately
        time.sleep(0.1)
        assert cache.get("content", "strategy", {}) is None
    
    def test_cache_eviction(self):
        """Test LRU cache eviction."""
        cache = ResponseCache(ttl_seconds=3600)
        cache.cache = {}  # Clear any existing entries
        
        # Fill cache to capacity
        for i in range(1001):
            cache.set(f"content_{i}", "strategy", {}, {"id": i}, 0.9)
        
        # Should have evicted oldest entry
        assert len(cache.cache) <= 1000
    
    def test_clear_expired(self):
        """Test clearing of expired entries."""
        cache = ResponseCache(ttl_seconds=0)
        
        # Add multiple entries
        for i in range(5):
            cache.set(f"content_{i}", "strategy", {}, {"id": i}, 0.9)
        
        time.sleep(0.1)
        
        # Clear expired entries
        cleared = cache.clear_expired()
        assert cleared == 5
        assert len(cache.cache) == 0


class TestExponentialBackoff:
    """Test exponential backoff logic."""
    
    def test_delay_calculation(self):
        """Test exponential delay calculation."""
        config = RetryConfig(
            initial_delay_ms=100,
            max_delay_ms=10000,
            exponential_base=2.0,
            jitter_factor=0.0  # No jitter for predictable testing
        )
        backoff = ExponentialBackoff(config)
        
        # Test exponential growth
        assert backoff.get_delay_ms(1) == 100
        assert backoff.get_delay_ms(2) == 200
        assert backoff.get_delay_ms(3) == 400
        assert backoff.get_delay_ms(4) == 800
        
        # Test max delay cap
        assert backoff.get_delay_ms(10) <= 10000
    
    def test_jitter(self):
        """Test jitter in delay calculation."""
        config = RetryConfig(
            initial_delay_ms=1000,
            jitter_factor=0.2
        )
        backoff = ExponentialBackoff(config)
        
        # Get multiple delays for same attempt
        delays = [backoff.get_delay_ms(3) for _ in range(10)]
        
        # Should have variation due to jitter
        assert len(set(delays)) > 1
        assert all(800 <= d <= 1200 for d in delays)  # ±20% jitter
    
    @pytest.mark.asyncio
    async def test_wait(self):
        """Test async wait functionality."""
        config = RetryConfig(initial_delay_ms=10)
        backoff = ExponentialBackoff(config)
        
        start = time.time()
        await backoff.wait(1)
        elapsed = (time.time() - start) * 1000
        
        # Should wait approximately the calculated delay
        assert 8 <= elapsed <= 20  # Allow some tolerance


class TestVLLMResilienceManager:
    """Test main resilience manager."""
    
    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """Test successful execution without retries."""
        manager = VLLMResilienceManager()
        
        # Mock successful vLLM function
        async def mock_vllm(content, **kwargs):
            return {"entities": [{"text": "John Doe", "entity_type": "PERSON"}]}
        
        success, result, metadata = await manager.execute_with_resilience(
            mock_vllm,
            "John Doe is a person",
            "ai_enhanced",
            {}
        )
        
        assert success is True
        assert len(result["entities"]) == 1
        assert metadata["attempts"] == 1
        assert metadata["final_strategy"] == "vllm"
    
    @pytest.mark.asyncio
    async def test_retry_on_empty_response(self):
        """Test retry logic for empty responses."""
        manager = VLLMResilienceManager(
            retry_config=RetryConfig(max_retries=3, initial_delay_ms=10)
        )
        
        attempt_count = 0
        
        async def mock_vllm(content, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count < 3:
                return {"entities": []}  # Empty response
            return {"entities": [{"text": "Success", "entity_type": "TEST"}]}
        
        success, result, metadata = await manager.execute_with_resilience(
            mock_vllm,
            "test content",
            "ai_enhanced",
            {}
        )
        
        assert success is True
        assert attempt_count == 3
        assert metadata["attempts"] == 3
        assert len(result["entities"]) == 1
    
    @pytest.mark.asyncio
    async def test_fallback_to_regex(self):
        """Test fallback to regex extraction."""
        manager = VLLMResilienceManager(
            fallback_config=FallbackConfig(enable_regex_fallback=True)
        )
        
        # Mock failing vLLM
        async def mock_vllm(content, **kwargs):
            raise ConnectionError("Cannot connect to vLLM")
        
        # Mock regex fallback
        async def mock_regex(content):
            return {"entities": [{"text": "regex result", "entity_type": "REGEX"}]}
        
        success, result, metadata = await manager.execute_with_resilience(
            mock_vllm,
            "test content",
            "ai_enhanced",
            {},
            regex_fallback_func=mock_regex
        )
        
        assert success is True
        assert result["entities"][0]["text"] == "regex result"
        assert "regex_fallback" in metadata["strategies_used"]
    
    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test cache hit scenario."""
        manager = VLLMResilienceManager(
            fallback_config=FallbackConfig(enable_caching=True)
        )
        
        call_count = 0
        
        async def mock_vllm(content, **kwargs):
            nonlocal call_count
            call_count += 1
            return {"entities": [{"text": "cached", "entity_type": "TEST"}]}
        
        # First call - should execute function
        success1, result1, metadata1 = await manager.execute_with_resilience(
            mock_vllm,
            "test content",
            "ai_enhanced",
            {}
        )
        
        # Second call - should hit cache
        success2, result2, metadata2 = await manager.execute_with_resilience(
            mock_vllm,
            "test content",
            "ai_enhanced",
            {}
        )
        
        assert call_count == 1  # Function called only once
        assert metadata1["cached"] is False
        assert metadata2["cached"] is True
        assert result1 == result2
    
    @pytest.mark.asyncio
    async def test_chunking_fallback(self):
        """Test chunking fallback for large content."""
        manager = VLLMResilienceManager(
            fallback_config=FallbackConfig(
                enable_chunking=True,
                chunk_size=10,
                chunk_overlap=2
            )
        )
        
        # Mock vLLM that fails on long content
        async def mock_vllm(content, **kwargs):
            if len(content) > 20:
                raise ValueError("Context overflow")
            return {"entities": [{"text": f"chunk_{len(content)}", "entity_type": "TEST"}]}
        
        # Long content that needs chunking
        long_content = "a" * 50
        
        success, result, metadata = await manager.execute_with_resilience(
            mock_vllm,
            long_content,
            "ai_enhanced",
            {}
        )
        
        # Should have succeeded with chunking
        assert success is True
        assert len(result["entities"]) > 0
        assert "chunking" in metadata["strategies_used"]
    
    def test_failure_classification(self):
        """Test failure type classification."""
        manager = VLLMResilienceManager()
        
        # Test various error types
        assert manager.classify_failure(
            ConnectionError("Connection refused")
        ) == FailureType.CONNECTION_ERROR
        
        assert manager.classify_failure(
            TimeoutError("Request timed out")
        ) == FailureType.TIMEOUT
        
        assert manager.classify_failure(
            ValueError("Rate limit exceeded")
        ) == FailureType.RATE_LIMIT
        
        assert manager.classify_failure(
            RuntimeError("CUDA out of memory")
        ) == FailureType.MODEL_OVERLOAD
    
    def test_metrics_tracking(self):
        """Test metrics collection."""
        manager = VLLMResilienceManager(enable_metrics=True)
        
        # Check initial metrics
        metrics = manager.get_metrics_summary()
        assert metrics["total_requests"] == 0
        assert metrics["success_rate"] == 0
        
        # TODO: Add more metrics tests after executing operations


class TestResilientDecorator:
    """Test resilient operation decorator."""
    
    @pytest.mark.asyncio
    async def test_decorator_basic(self):
        """Test basic decorator functionality."""
        
        @resilient_vllm_operation()
        async def extract_entities(content: str, **kwargs) -> Dict:
            return {"entities": [{"text": "decorated", "entity_type": "TEST"}]}
        
        result = await extract_entities("test content")
        
        assert "entities" in result
        assert "_resilience_metadata" in result
        assert result["entities"][0]["text"] == "decorated"
    
    @pytest.mark.asyncio
    async def test_decorator_with_retry(self):
        """Test decorator with retry logic."""
        attempt_count = 0
        
        @resilient_vllm_operation(
            retry_config=RetryConfig(max_retries=3, initial_delay_ms=10)
        )
        async def flaky_extraction(content: str, **kwargs) -> Dict:
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count < 2:
                raise ConnectionError("Temporary failure")
            
            return {"entities": [{"text": "success", "entity_type": "TEST"}]}
        
        result = await flaky_extraction("test content")
        
        assert attempt_count == 2
        assert result["entities"][0]["text"] == "success"
        assert result["_resilience_metadata"]["attempts"] == 2


class TestIntegrationScenarios:
    """Integration tests for complex scenarios."""
    
    @pytest.mark.asyncio
    async def test_progressive_degradation(self):
        """Test progressive degradation through multiple strategies."""
        manager = VLLMResilienceManager(
            retry_config=RetryConfig(max_retries=2, initial_delay_ms=10),
            fallback_config=FallbackConfig(
                enable_regex_fallback=True,
                enable_hybrid_mode=True
            )
        )
        
        attempt_count = 0
        
        async def mock_vllm(content, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            
            # Fail first attempts
            if attempt_count <= 2:
                return {"entities": []}  # Empty response
            
            # Should not reach here due to fallback
            return {"entities": [{"text": "vllm", "entity_type": "TEST"}]}
        
        async def mock_hybrid(content, **kwargs):
            return {"entities": [{"text": "hybrid", "entity_type": "TEST"}]}
        
        async def mock_regex(content):
            return {"entities": [{"text": "regex", "entity_type": "TEST"}]}
        
        success, result, metadata = await manager.execute_with_resilience(
            mock_vllm,
            "test content",
            "ai_enhanced",
            {},
            regex_fallback_func=mock_regex,
            hybrid_func=mock_hybrid
        )
        
        assert success is True
        # Should have tried vLLM twice, then fallen back
        assert attempt_count == 2
        assert len(metadata["strategies_used"]) > 0
    
    @pytest.mark.asyncio
    async def test_malformed_response_handling(self):
        """Test handling of malformed JSON responses."""
        manager = VLLMResilienceManager(
            retry_config=RetryConfig(max_retries=2, initial_delay_ms=10)
        )
        
        responses = [
            '{"entities": [{"text": "broken"',  # Malformed JSON
            '{"entities": "not_a_list"}',        # Wrong type
            '{"entities": [{"text": "valid", "entity_type": "TEST"}]}'  # Valid
        ]
        
        call_count = 0
        
        async def mock_vllm(content, **kwargs):
            nonlocal call_count
            response = responses[min(call_count, len(responses) - 1)]
            call_count += 1
            
            # Simulate string response that needs validation
            return response
        
        # Need to patch the validation in the manager
        with patch.object(manager.validator, 'validate_json_structure') as mock_validate:
            # Setup validation responses
            mock_validate.side_effect = [
                (False, None, "Malformed JSON"),
                (False, None, "Wrong type"),
                (True, json.loads(responses[2]), None)
            ]
            
            success, result, metadata = await manager.execute_with_resilience(
                mock_vllm,
                "test content",
                "ai_enhanced",
                {}
            )
        
        # Should have retried and eventually succeeded
        assert call_count >= 2
        assert FailureType.MALFORMED_JSON.value in metadata["failure_types"]


def run_tests():
    """Run all tests."""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    run_tests()