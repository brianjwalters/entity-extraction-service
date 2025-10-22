"""
Integration module for using ThrottledVLLMClient in the entity extraction service.

This module demonstrates how to integrate the throttled client
as a drop-in replacement for the standard VLLMLocalClient.
"""

import logging
from typing import Optional, Dict, Any

from src.client.vllm_direct_client import DirectVLLMEngine
from src.core.throttled_vllm_client import ThrottledVLLMClient

# Compatibility alias
VLLMLocalClient = DirectVLLMEngine
from src.core.config import get_config

logger = logging.getLogger(__name__)


class ThrottledVLLMClientFactory:
    """
    Factory for creating vLLM clients with optional throttling.
    
    This factory allows seamless switching between throttled and
    non-throttled clients based on configuration.
    """
    
    _instance: Optional['ThrottledVLLMClientFactory'] = None
    _clients: Dict[str, Any] = {}
    
    def __new__(cls):
        """Singleton pattern for factory."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def create_client(
        self,
        client_id: str = "default",
        enable_throttling: Optional[bool] = None,
        config_override: Optional[Dict[str, Any]] = None
    ) -> VLLMLocalClient:
        """
        Create a vLLM client with optional throttling.
        
        Args:
            client_id: Unique identifier for client caching
            enable_throttling: Whether to enable throttling (None = use config)
            config_override: Configuration overrides
            
        Returns:
            VLLMLocalClient or ThrottledVLLMClient instance
        """
        # Check cache first
        if client_id in self._clients:
            logger.debug(f"Returning cached client: {client_id}")
            return self._clients[client_id]
        
        # Load configuration
        config = get_settings()
        
        # Determine if throttling should be enabled
        if enable_throttling is None:
            # Use config to determine throttling
            enable_throttling = (
                config.performance.processing_mode == "throttled" or
                config.performance.enable_rate_limiting
            )
        
        # Create base client with DirectVLLMEngine
        base_client = DirectVLLMEngine(
            model_name=config.vllm.model,
            max_model_len=getattr(config.vllm, 'max_model_len', 131072)
        )
        
        # Wrap with throttling if enabled
        if enable_throttling:
            logger.info(f"Creating THROTTLED client: {client_id}")
            client = ThrottledVLLMClient(
                base_client=base_client,
                config_override=config_override
            )
        else:
            logger.info(f"Creating STANDARD client: {client_id}")
            client = base_client
        
        # Cache the client
        self._clients[client_id] = client
        
        return client
    
    def get_client(self, client_id: str = "default") -> Optional[VLLMLocalClient]:
        """
        Get an existing client by ID.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Client instance or None if not found
        """
        return self._clients.get(client_id)
    
    def clear_cache(self):
        """Clear all cached clients."""
        self._clients.clear()
        logger.info("Client cache cleared")


def get_vllm_client(
    throttled: Optional[bool] = None,
    config_override: Optional[Dict[str, Any]] = None
) -> VLLMLocalClient:
    """
    Convenience function to get a vLLM client.
    
    This is the recommended way to get a vLLM client in the
    entity extraction service.
    
    Args:
        throttled: Whether to use throttling (None = auto-detect from config)
        config_override: Configuration overrides
        
    Returns:
        VLLMLocalClient or ThrottledVLLMClient instance
    
    Example:
        # Auto-detect throttling from config
        client = get_vllm_client()
        
        # Force throttled client
        client = get_vllm_client(throttled=True)
        
        # Custom configuration
        client = get_vllm_client(
            throttled=True,
            config_override={
                "max_concurrent_requests": 1,
                "requests_per_minute": 10
            }
        )
    """
    factory = ThrottledVLLMClientFactory()
    return factory.create_client(
        client_id="main",
        enable_throttling=throttled,
        config_override=config_override
    )


async def example_entity_extraction_with_throttling():
    """
    Example of using throttled client for entity extraction.
    
    This shows how the throttled client can be used as a drop-in
    replacement in existing entity extraction code.
    """
    import json
    from src.client.vllm_http_client import VLLMRequest
    
    # Get throttled client (auto-detect from config)
    client = get_vllm_client()
    
    # Sample legal text for extraction
    legal_text = """
    In the case of Smith v. Jones, 123 F.3d 456 (2d Cir. 2023), 
    Judge Sarah Williams ruled that the defendant, Jones Corporation,
    violated Section 10(b) of the Securities Exchange Act of 1934.
    The plaintiff, John Smith, was awarded $2.5 million in damages.
    The decision was affirmed by the Court of Appeals on March 15, 2023.
    """
    
    # Create extraction prompt
    extraction_prompt = f"""
    Extract all legal entities from the following text.
    Return the results as a JSON array with objects containing:
    - entity_type: The type of entity (case_citation, party, judge, statute, date, monetary_amount)
    - text: The exact text of the entity
    - normalized: A normalized form if applicable
    
    Text:
    {legal_text}
    
    Respond only with the JSON array, no other text.
    """
    
    # Create request
    request = VLLMRequest(
        messages=[
            {"role": "system", "content": "You are a legal entity extraction system."},
            {"role": "user", "content": extraction_prompt}
        ],
        max_tokens=500,
        temperature=0.1,
        response_format="json"
    )
    
    try:
        logger.info("Extracting entities with throttled client...")
        
        # Make extraction request
        response = await client.generate_chat_completion(request)
        
        # Parse extracted entities
        entities = json.loads(response.content)
        
        logger.info(f"Extracted {len(entities)} entities")
        
        # If using throttled client, check stats
        if isinstance(client, ThrottledVLLMClient):
            stats = client.get_throttling_stats()
            logger.info(f"Throttling stats:")
            logger.info(f"  - Total requests: {stats.total_requests}")
            logger.info(f"  - Average response time: {stats.average_response_time_ms:.1f}ms")
            logger.info(f"  - Adaptive delay: {stats.adaptive_delay_ms:.1f}ms")
            logger.info(f"  - Circuit state: {stats.circuit_state}")
        
        return entities
        
    except Exception as e:
        logger.error(f"Entity extraction failed: {e}")
        
        # Check if it's a circuit breaker issue
        if "Circuit breaker is OPEN" in str(e):
            logger.error("vLLM service is unavailable due to repeated failures")
            # Could fall back to regex-based extraction here
        
        raise


class EntityExtractionServiceAdapter:
    """
    Adapter to integrate throttled client into entity extraction service.
    
    This class shows how to adapt existing service code to use
    the throttled client transparently.
    """
    
    def __init__(self, enable_throttling: Optional[bool] = None):
        """
        Initialize the adapter.
        
        Args:
            enable_throttling: Whether to enable throttling (None = auto)
        """
        self.client = get_vllm_client(throttled=enable_throttling)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def extract_entities_ai_enhanced(
        self,
        text: str,
        entity_types: Optional[list] = None
    ) -> list:
        """
        Extract entities using AI-enhanced mode with throttling.
        
        Args:
            text: Text to extract entities from
            entity_types: Optional list of entity types to extract
            
        Returns:
            List of extracted entities
        """
        if not entity_types:
            entity_types = [
                "case_citation", "party", "judge", "attorney", 
                "court", "date", "statute", "regulation"
            ]
        
        # Build extraction prompt
        entity_list = ", ".join(entity_types)
        prompt = f"""
        Extract the following types of legal entities from the text:
        {entity_list}
        
        Text: {text}
        
        Return a JSON array of entities with fields:
        - type: entity type
        - text: extracted text
        - start: start position
        - end: end position
        """
        
        request = VLLMRequest(
            messages=[
                {"role": "system", "content": "You are a legal entity extraction system."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.1
        )
        
        try:
            response = await self.client.generate_chat_completion(request)
            
            # Parse and validate entities
            import json
            entities = json.loads(response.content)
            
            # Log performance if throttled
            if isinstance(self.client, ThrottledVLLMClient):
                health = await self.client.health_check()
                throttling_stats = health.get("throttling", {}).get("stats", {})
                
                self.logger.debug(
                    f"Extraction completed - "
                    f"avg response: {throttling_stats.get('average_response_time_ms', 0):.1f}ms, "
                    f"queue size: {throttling_stats.get('queue_size', 0)}"
                )
            
            return entities
            
        except Exception as e:
            self.logger.error(f"AI-enhanced extraction failed: {e}")
            # Could fall back to regex extraction
            raise
    
    async def get_service_health(self) -> Dict[str, Any]:
        """
        Get service health including throttling status.
        
        Returns:
            Health status dictionary
        """
        health = {
            "service": "entity-extraction",
            "status": "healthy",
            "vllm_client": type(self.client).__name__
        }
        
        # Add throttling info if available
        if isinstance(self.client, ThrottledVLLMClient):
            client_health = await self.client.health_check()
            health["throttling"] = client_health.get("throttling", {})
        
        return health


# Example of modifying existing code to use throttled client
def modify_existing_extraction_code():
    """
    Example of how to modify existing extraction code.
    
    Original code:
        client = VLLMLocalClient()
        response = await client.generate_chat_completion(request)
    
    Modified code (Option 1 - Minimal change):
        from src.core.throttled_integration import get_vllm_client
        client = get_vllm_client()  # Auto-detects throttling need
        response = await client.generate_chat_completion(request)
    
    Modified code (Option 2 - Explicit throttling):
        from src.core.throttled_vllm_client import ThrottledVLLMClient
        base_client = VLLMLocalClient()
        client = ThrottledVLLMClient(base_client)
        response = await client.generate_chat_completion(request)
    
    Modified code (Option 3 - Conditional throttling):
        from src.core.throttled_integration import get_vllm_client
        config = get_settings()
        client = get_vllm_client(
            throttled=(config.performance.processing_mode == "throttled")
        )
        response = await client.generate_chat_completion(request)
    """


if __name__ == "__main__":
    # Test the integration
    import asyncio
    
    async def test():
        """Test throttled integration."""
        print("Testing throttled vLLM client integration...")
        
        # Test factory
        factory = ThrottledVLLMClientFactory()
        
        # Create different clients
        standard_client = factory.create_client("standard", enable_throttling=False)
        throttled_client = factory.create_client("throttled", enable_throttling=True)
        
        print(f"Standard client type: {type(standard_client).__name__}")
        print(f"Throttled client type: {type(throttled_client).__name__}")
        
        # Test adapter
        adapter = EntityExtractionServiceAdapter(enable_throttling=True)
        health = await adapter.get_service_health()
        print(f"Service health: {health}")
        
        # Test extraction (if vLLM is available)
        try:
            entities = await example_entity_extraction_with_throttling()
            print(f"Extraction successful: {len(entities)} entities")
        except Exception as e:
            print(f"Extraction test skipped: {e}")
    
    asyncio.run(test())