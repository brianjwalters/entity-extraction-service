"""
Unit tests for ExtractionOrchestrator vLLM client integration.

Tests validate interface compatibility between ExtractionOrchestrator
and both DirectVLLMClient and HTTPVLLMClient implementations.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from src.core.extraction_orchestrator import ExtractionOrchestrator
from src.vllm_client.models import VLLMRequest, VLLMResponse, VLLMUsage
from src.routing.document_router import RoutingDecision, ProcessingStrategy
from src.routing.size_detector import DocumentSizeInfo, SizeCategory


class TestExtractionOrchestratorVLLMIntegration:
    """Test ExtractionOrchestrator integration with vLLM clients."""

    @pytest.fixture
    def mock_vllm_client(self):
        """Create mock vLLM client with correct interface."""
        client = AsyncMock()

        # Mock generate_chat_completion method (correct interface)
        async def mock_generate_chat_completion(request: VLLMRequest) -> VLLMResponse:
            """Mock implementation returning VLLMResponse."""
            return VLLMResponse(
                content='[{"type": "PERSON", "text": "John Doe", "start": 0, "end": 8}]',
                model="test-model",
                usage=VLLMUsage(
                    prompt_tokens=100,
                    completion_tokens=50,
                    total_tokens=150
                ),
                finish_reason="stop",
                response_time_ms=123.45,
                metadata={"test": True}
            )

        client.generate_chat_completion = mock_generate_chat_completion
        return client

    @pytest.fixture
    def orchestrator_with_mock_client(self, mock_vllm_client):
        """Create orchestrator with mocked vLLM client."""
        with patch('src.core.extraction_orchestrator.PromptManager') as MockPromptManager:
            mock_prompt_manager = MockPromptManager.return_value
            mock_prompt_manager.get_single_pass_prompt.return_value = MagicMock(
                content="Test prompt template",
                token_count=500
            )

            orchestrator = ExtractionOrchestrator(
                prompt_manager=mock_prompt_manager,
                vllm_client=mock_vllm_client
            )
            return orchestrator

    @pytest.fixture
    def sample_size_info(self):
        """Create sample document size info."""
        return DocumentSizeInfo(
            chars=1000,
            tokens=250,
            pages=1,
            category=SizeCategory.VERY_SMALL,
            words=150,
            lines=20
        )

    @pytest.fixture
    def sample_routing_decision(self, sample_size_info):
        """Create sample routing decision."""
        return RoutingDecision(
            strategy=ProcessingStrategy.SINGLE_PASS,
            prompt_version="single_pass_v1",
            chunk_config=None,
            estimated_tokens=2000,
            estimated_duration=1.5,
            estimated_cost=0.001,
            expected_accuracy=0.95,
            size_info=sample_size_info,
            rationale="Document is very small (1000 chars)",
            num_chunks=0
        )

    @pytest.mark.asyncio
    async def test_call_vllm_creates_correct_request(self, orchestrator_with_mock_client):
        """Test that _call_vllm creates VLLMRequest with correct structure."""
        orchestrator = orchestrator_with_mock_client

        # Execute _call_vllm
        prompt = "Test prompt for entity extraction"
        result = await orchestrator._call_vllm(prompt)

        # Verify result structure
        assert "text" in result
        assert "tokens_used" in result
        assert isinstance(result["text"], str)
        assert isinstance(result["tokens_used"], int)

        # Verify response content
        assert result["text"] == '[{"type": "PERSON", "text": "John Doe", "start": 0, "end": 8}]'
        assert result["tokens_used"] == 150

    @pytest.mark.asyncio
    async def test_call_vllm_uses_generate_chat_completion(self, orchestrator_with_mock_client):
        """Test that _call_vllm calls generate_chat_completion method."""
        orchestrator = orchestrator_with_mock_client
        client = orchestrator.vllm_client

        # Track call to generate_chat_completion
        call_tracker = {"called": False, "request": None}

        async def track_call(request: VLLMRequest):
            call_tracker["called"] = True
            call_tracker["request"] = request
            return VLLMResponse(
                content="test response",
                model="test",
                usage=VLLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                finish_reason="stop",
                response_time_ms=100.0
            )

        client.generate_chat_completion = track_call

        # Execute
        await orchestrator._call_vllm("Test prompt")

        # Verify correct method was called
        assert call_tracker["called"], "generate_chat_completion was not called"
        assert call_tracker["request"] is not None, "No request object passed"

        # Verify request structure
        request = call_tracker["request"]
        assert isinstance(request, VLLMRequest)
        assert len(request.messages) == 1
        assert request.messages[0]["role"] == "user"
        assert request.messages[0]["content"] == "Test prompt"
        assert request.max_tokens == 4096
        assert request.temperature == 0.0
        assert request.seed == 42
        assert request.stream is False

    @pytest.mark.asyncio
    async def test_call_vllm_accesses_response_attributes_correctly(self, orchestrator_with_mock_client):
        """Test that _call_vllm accesses VLLMResponse attributes (not dict keys)."""
        orchestrator = orchestrator_with_mock_client

        # Create response with specific values
        test_response = VLLMResponse(
            content="Test entity extraction result",
            model="mistral-nemo-12b-instruct-128k",
            usage=VLLMUsage(
                prompt_tokens=200,
                completion_tokens=100,
                total_tokens=300
            ),
            finish_reason="stop",
            response_time_ms=250.5
        )

        async def return_test_response(request):
            return test_response

        orchestrator.vllm_client.generate_chat_completion = return_test_response

        # Execute
        result = await orchestrator._call_vllm("Test prompt")

        # Verify correct attribute access
        assert result["text"] == "Test entity extraction result"
        assert result["tokens_used"] == 300

    @pytest.mark.asyncio
    async def test_single_pass_extraction_integration(
        self,
        orchestrator_with_mock_client,
        sample_routing_decision,
        sample_size_info
    ):
        """Test full single-pass extraction with vLLM integration."""
        orchestrator = orchestrator_with_mock_client

        # Document text
        document_text = "This is a test document with John Doe mentioned."

        # Execute extraction
        result = await orchestrator.extract(
            document_text=document_text,
            routing_decision=sample_routing_decision,
            size_info=sample_size_info
        )

        # Verify result structure
        assert result.entities is not None
        assert isinstance(result.entities, list)
        assert result.strategy == ProcessingStrategy.SINGLE_PASS
        assert result.waves_executed == 1
        assert result.tokens_used > 0
        assert result.processing_time >= 0

    @pytest.mark.asyncio
    async def test_error_handling_on_client_failure(self, orchestrator_with_mock_client):
        """Test that errors from vLLM client are properly propagated."""
        orchestrator = orchestrator_with_mock_client

        # Configure client to raise exception
        async def raise_error(request):
            raise RuntimeError("vLLM service unavailable")

        orchestrator.vllm_client.generate_chat_completion = raise_error

        # Verify exception propagates correctly
        with pytest.raises(Exception) as exc_info:
            await orchestrator._call_vllm("Test prompt")

        assert "vLLM service unavailable" in str(exc_info.value)

    def test_vllm_request_imports_correctly(self):
        """Test that VLLMRequest can be imported within _call_vllm context."""
        # This test validates import availability
        from src.vllm_client.models import VLLMRequest

        # Create request to verify structure
        request = VLLMRequest(
            messages=[{"role": "user", "content": "test"}],
            max_tokens=100,
            temperature=0.0,
            seed=42
        )

        assert request.messages[0]["role"] == "user"
        assert request.max_tokens == 100
        assert request.temperature == 0.0
        assert request.seed == 42


class TestInterfaceCompatibility:
    """Test interface compatibility between clients and orchestrator."""

    def test_direct_vllm_client_has_generate_chat_completion(self):
        """Verify DirectVLLMClient implements generate_chat_completion method."""
        from src.vllm_client.client import DirectVLLMClient

        # Check method exists
        assert hasattr(DirectVLLMClient, 'generate_chat_completion')

        # Verify it's a method
        import inspect
        method = getattr(DirectVLLMClient, 'generate_chat_completion')
        assert inspect.iscoroutinefunction(method), "generate_chat_completion must be async"

    def test_http_vllm_client_has_generate_chat_completion(self):
        """Verify HTTPVLLMClient implements generate_chat_completion method."""
        from src.vllm_client.client import HTTPVLLMClient

        # Check method exists
        assert hasattr(HTTPVLLMClient, 'generate_chat_completion')

        # Verify it's a method
        import inspect
        method = getattr(HTTPVLLMClient, 'generate_chat_completion')
        assert inspect.iscoroutinefunction(method), "generate_chat_completion must be async"

    def test_vllm_response_has_required_attributes(self):
        """Verify VLLMResponse has content and usage attributes."""
        from src.vllm_client.models import VLLMResponse, VLLMUsage

        response = VLLMResponse(
            content="test content",
            model="test-model",
            usage=VLLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            finish_reason="stop",
            response_time_ms=100.0
        )

        # Verify attributes exist and are accessible
        assert hasattr(response, 'content')
        assert hasattr(response, 'usage')
        assert response.content == "test content"
        assert response.usage.total_tokens == 15

    def test_vllm_request_structure(self):
        """Verify VLLMRequest accepts expected parameters."""
        from src.vllm_client.models import VLLMRequest

        # Test with all parameters used in _call_vllm
        request = VLLMRequest(
            messages=[{"role": "user", "content": "test prompt"}],
            max_tokens=4096,
            temperature=0.0,
            seed=42,
            stream=False
        )

        assert request.messages[0]["role"] == "user"
        assert request.messages[0]["content"] == "test prompt"
        assert request.max_tokens == 4096
        assert request.temperature == 0.0
        assert request.seed == 42
        assert request.stream is False


# Run tests with: pytest tests/unit/test_extraction_orchestrator_vllm_integration.py -v
