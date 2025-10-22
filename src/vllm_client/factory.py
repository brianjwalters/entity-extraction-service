"""
vLLM Client Factory

Creates appropriate vLLM client with automatic fallback from Direct API to HTTP.
"""

import logging
from typing import Optional

from .models import VLLMConfig, VLLMClientType
from .client import VLLMClientInterface, DirectVLLMClient, HTTPVLLMClient
from .exceptions import ConnectionError as VLLMConnectionError

logger = logging.getLogger(__name__)


class VLLMClientFactory:
    """
    Factory for creating appropriate vLLM client.

    Automatically selects Direct API when available, falls back to HTTP.
    """

    @staticmethod
    async def create_client(
        preferred_type: VLLMClientType = VLLMClientType.HTTP_API,
        config: Optional[VLLMConfig] = None,
        enable_fallback: bool = False
    ) -> VLLMClientInterface:
        """
        Create vLLM client with automatic fallback.

        Args:
            preferred_type: Preferred client type
            config: Client configuration (if None, loads from centralized settings)
            enable_fallback: Enable HTTP fallback if direct fails

        Returns:
            Initialized vLLM client

        Raises:
            VLLMConnectionError: If no client can be created
        """
        # Load from centralized config if not provided
        if config is None:
            from src.core.config import get_settings
            settings = get_settings()
            config = VLLMConfig.from_settings(settings)

        # Try direct API first (if preferred)
        if preferred_type == VLLMClientType.DIRECT_API:
            try:
                logger.info("Initializing DirectVLLMClient (vLLM Python library)...")
                logger.info(f"Model: {config.model}, Max tokens: {config.max_model_len}, GPU memory: {config.gpu_memory_utilization}")

                client = DirectVLLMClient(config=config)
                success = await client.connect()

                if success:
                    logger.info("✅ DirectVLLMClient initialized successfully")
                    logger.info("✅ Guided JSON support: AVAILABLE")
                    return client
                else:
                    logger.warning("❌ DirectVLLMClient connection failed (connect() returned False)")

            except ImportError as e:
                logger.error(f"❌ vLLM library not installed: {e}")
                logger.error("Install with: source venv/bin/activate && pip install vllm==0.6.3")
                if enable_fallback:
                    logger.warning("⚠️  Falling back to HTTPVLLMClient (guided JSON may not work)")
                    logger.warning("⚠️  HTTP fallback uses OpenAI-compatible API, which may not support guided_json parameter")

            except Exception as e:
                logger.error(f"❌ DirectVLLMClient initialization failed: {e}", exc_info=True)
                if enable_fallback:
                    logger.warning("⚠️  Falling back to HTTPVLLMClient")
                    logger.warning("⚠️  HTTP fallback may not support all Direct API features (e.g., guided JSON)")

        # Fallback to HTTP API
        if enable_fallback:
            try:
                logger.info("Initializing HTTPVLLMClient (OpenAI-compatible API)...")
                logger.info(f"Base URL: {config.base_url}, Timeout: {config.http_timeout}s")

                client = HTTPVLLMClient(config=config)
                success = await client.connect()

                if success:
                    logger.info("✅ HTTPVLLMClient initialized successfully")
                    logger.warning("⚠️  Guided JSON support: LIMITED (depends on vLLM server configuration)")
                    return client
                else:
                    logger.error(f"❌ HTTPVLLMClient connection failed (connect() returned False)")
                    raise VLLMConnectionError(
                        "HTTP API connection failed",
                        base_url=config.base_url
                    )

            except VLLMConnectionError:
                # Re-raise connection errors without wrapping
                raise
            except Exception as e:
                logger.error(f"❌ HTTPVLLMClient initialization failed: {e}", exc_info=True)
                raise VLLMConnectionError(
                    f"No vLLM client available. Direct API failed, HTTP fallback failed: {e}",
                    base_url=config.base_url
                )

        raise VLLMConnectionError(
            "Failed to create any vLLM client (fallback disabled)",
            base_url=config.base_url
        )

    @staticmethod
    async def create_direct_client(
        config: Optional[VLLMConfig] = None
    ) -> DirectVLLMClient:
        """
        Create Direct vLLM client (no fallback).

        Args:
            config: Client configuration (if None, loads from centralized settings)

        Returns:
            DirectVLLMClient instance

        Raises:
            VLLMConnectionError: If initialization fails
        """
        # Load from centralized config if not provided
        if config is None:
            from src.core.config import get_settings
            settings = get_settings()
            config = VLLMConfig.from_settings(settings)

        try:
            logger.info("Initializing DirectVLLMClient (no fallback)...")
            logger.info(f"Model: {config.model}, Max tokens: {config.max_model_len}")

            client = DirectVLLMClient(config=config)
            success = await client.connect()

            if not success:
                logger.error("❌ DirectVLLMClient connection failed")
                raise VLLMConnectionError("Direct API initialization failed")

            logger.info("✅ DirectVLLMClient initialized successfully")
            return client

        except ImportError as e:
            logger.error(f"❌ vLLM library not installed: {e}")
            logger.error("Install with: source venv/bin/activate && pip install vllm==0.6.3")
            raise VLLMConnectionError(f"vLLM library not installed: {e}")

        except VLLMConnectionError:
            # Re-raise connection errors without wrapping
            raise

        except Exception as e:
            logger.error(f"❌ DirectVLLMClient initialization failed: {e}", exc_info=True)
            raise VLLMConnectionError(f"Failed to create Direct vLLM client: {e}")

    @staticmethod
    async def create_http_client(
        config: Optional[VLLMConfig] = None
    ) -> HTTPVLLMClient:
        """
        Create HTTP vLLM client (no fallback).

        Args:
            config: Client configuration (if None, loads from centralized settings)

        Returns:
            HTTPVLLMClient instance

        Raises:
            VLLMConnectionError: If initialization fails
        """
        # Load from centralized config if not provided
        if config is None:
            from src.core.config import get_settings
            settings = get_settings()
            config = VLLMConfig.from_settings(settings)

        try:
            logger.info("Initializing HTTPVLLMClient (no fallback)...")
            logger.info(f"Base URL: {config.base_url}, Timeout: {config.http_timeout}s")

            client = HTTPVLLMClient(config=config)
            success = await client.connect()

            if not success:
                logger.error(f"❌ HTTPVLLMClient connection failed to {config.base_url}")
                raise VLLMConnectionError(
                    "HTTP API connection failed",
                    base_url=config.base_url
                )

            logger.info("✅ HTTPVLLMClient initialized successfully")
            logger.warning("⚠️  Guided JSON support: LIMITED (depends on vLLM server configuration)")
            return client

        except VLLMConnectionError:
            # Re-raise connection errors without wrapping
            raise

        except Exception as e:
            logger.error(f"❌ HTTPVLLMClient initialization failed: {e}", exc_info=True)
            raise VLLMConnectionError(f"Failed to create HTTP vLLM client: {e}")

    @staticmethod
    def create_config(
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        max_model_len: Optional[int] = None,
        gpu_memory_utilization: Optional[float] = None,
        enable_prefix_caching: Optional[bool] = None,
        enable_gpu_monitoring: Optional[bool] = None,
        **kwargs
    ) -> VLLMConfig:
        """
        Create VLLMConfig with custom parameters.

        Args:
            model: Model name
            base_url: vLLM server URL
            max_model_len: Maximum context length
            gpu_memory_utilization: GPU memory fraction
            enable_prefix_caching: Enable prefix caching
            enable_gpu_monitoring: Enable GPU monitoring
            **kwargs: Additional config parameters

        Returns:
            VLLMConfig instance
        """
        config = VLLMConfig()

        if model:
            config.model = model
        if base_url:
            config.base_url = base_url
        if max_model_len:
            config.max_model_len = max_model_len
        if gpu_memory_utilization:
            config.gpu_memory_utilization = gpu_memory_utilization
        if enable_prefix_caching is not None:
            config.enable_prefix_caching = enable_prefix_caching
        if enable_gpu_monitoring is not None:
            config.enable_gpu_monitoring = enable_gpu_monitoring

        # Apply additional kwargs
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        return config


# Convenience functions
async def get_default_client(enable_fallback: bool = False) -> VLLMClientInterface:
    """
    Get default vLLM client with configuration from centralized settings.

    Args:
        enable_fallback: Enable HTTP fallback if direct fails (default: False)

    Returns:
        Initialized vLLM client with centralized configuration
    """
    # Load from centralized config
    from src.core.config import get_settings
    settings = get_settings()
    config = VLLMConfig.from_settings(settings)

    return await VLLMClientFactory.create_client(
        preferred_type=VLLMClientType.DIRECT_API,
        config=config,
        enable_fallback=enable_fallback
    )


async def get_client_for_entity_extraction() -> VLLMClientInterface:
    """
    Get vLLM client optimized for entity extraction.

    **UPDATED**: Now uses HTTP API as default (not Direct API).

    All configuration values now loaded from centralized settings.

    Returns:
        Initialized HTTP vLLM client with entity extraction optimizations
    """
    # Load from centralized config (all optimizations defined there)
    from src.core.config import get_settings
    settings = get_settings()
    config = VLLMConfig.from_settings(settings)

    return await VLLMClientFactory.create_client(
        preferred_type=VLLMClientType.HTTP_API,
        config=config,
        enable_fallback=False
    )


async def create_instruct_client(config: Optional[VLLMConfig] = None) -> HTTPVLLMClient:
    """
    Create HTTP client for Instruct service (Port 8080).

    Service: Qwen3-VL-8B-Instruct-FP8 (384K context)
    Use for: Fast entity extraction (Waves 1-3)

    Args:
        config: VLLMConfig instance (if None, loads from centralized settings)

    Returns:
        HTTPVLLMClient configured for Instruct service
    """
    from .models import VLLMServiceType

    if config is None:
        from src.core.config import get_settings
        settings = get_settings()
        config = VLLMConfig.from_settings(settings)

    logger.info("Creating Instruct client (Port 8080) for entity extraction")
    client = HTTPVLLMClient(config=config, service_type=VLLMServiceType.INSTRUCT)
    success = await client.connect()

    if not success:
        raise VLLMConnectionError("Failed to connect to Instruct service (Port 8080)")

    logger.info("✅ Instruct client initialized successfully")
    return client


async def create_thinking_client(config: Optional[VLLMConfig] = None) -> HTTPVLLMClient:
    """
    Create HTTP client for Thinking service (Port 8082).

    Service: Qwen3-VL-8B-Thinking-FP8 (256K context)
    Use for: Complex reasoning and relationship extraction (Wave 4)

    Args:
        config: VLLMConfig instance (if None, loads from centralized settings)

    Returns:
        HTTPVLLMClient configured for Thinking service
    """
    from .models import VLLMServiceType

    if config is None:
        from src.core.config import get_settings
        settings = get_settings()
        config = VLLMConfig.from_settings(settings)

    logger.info("Creating Thinking client (Port 8082) for relationship extraction")
    client = HTTPVLLMClient(config=config, service_type=VLLMServiceType.THINKING)
    success = await client.connect()

    if not success:
        raise VLLMConnectionError("Failed to connect to Thinking service (Port 8082)")

    logger.info("✅ Thinking client initialized successfully")
    return client
