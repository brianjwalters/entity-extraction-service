"""
Token estimation and context validation for vLLM.

Provides fast character-based estimation and optional accurate tokenization
using tiktoken library. Critical for preventing context overflow errors.

All default values now loaded from centralized config.py via VLLMConfig.
"""

import logging
from typing import Optional, Tuple
from .exceptions import ContextOverflowError
from .models import VLLMConfig

logger = logging.getLogger(__name__)


class TokenEstimator:
    """
    Token estimation and context validation.

    Supports two modes:
    1. Fast mode: Character-based estimation (~4 chars per token)
    2. Accurate mode: tiktoken-based tokenization (slower, more accurate)
    """

    def __init__(self, config: VLLMConfig):
        """
        Initialize TokenEstimator.

        Args:
            config: VLLMConfig with estimation parameters
        """
        self.config = config
        self.chars_per_token = config.chars_per_token
        self.use_accurate = config.use_accurate_tokenizer
        self.max_context = config.max_model_len
        self.max_prompt = config.max_prompt_tokens
        self.max_completion = config.max_completion_tokens

        # Try to import tiktoken for accurate estimation
        self._tokenizer = None
        if self.use_accurate:
            try:
                import tiktoken
                # Use cl100k_base encoding (GPT-4, GPT-3.5-turbo compatible)
                self._tokenizer = tiktoken.get_encoding("cl100k_base")
                logger.info("Accurate tokenization enabled (tiktoken)")
            except ImportError:
                logger.warning(
                    "tiktoken not available, falling back to character-based estimation. "
                    "Install with: pip install tiktoken"
                )
                self.use_accurate = False

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        if self.use_accurate and self._tokenizer:
            return len(self._tokenizer.encode(text))
        else:
            # Fast character-based estimation
            return int(len(text) / self.chars_per_token)

    def estimate_prompt_tokens(self, prompt: str, max_completion_tokens: int) -> Tuple[int, int]:
        """
        Estimate prompt tokens and validate against context limits.

        Args:
            prompt: Prompt text
            max_completion_tokens: Maximum completion tokens requested

        Returns:
            Tuple of (estimated_prompt_tokens, max_allowed_completion)

        Raises:
            ContextOverflowError: If prompt exceeds limits
        """
        prompt_tokens = self.estimate_tokens(prompt)

        # Check if prompt alone exceeds limit
        if prompt_tokens > self.max_prompt:
            excess = prompt_tokens - self.max_prompt
            raise ContextOverflowError(
                f"Prompt too large: {prompt_tokens:,} tokens exceeds "
                f"maximum {self.max_prompt:,} tokens",
                estimated_tokens=prompt_tokens,
                max_tokens=self.max_prompt,
                excess_tokens=excess
            )

        # Check total context window
        total_tokens = prompt_tokens + max_completion_tokens
        if total_tokens > self.max_context:
            # Suggest reduced completion tokens
            max_allowed_completion = max(0, self.max_context - prompt_tokens)
            excess = total_tokens - self.max_context

            if max_allowed_completion < 100:
                # Not enough space even for minimal completion
                raise ContextOverflowError(
                    f"Context overflow: prompt ({prompt_tokens:,} tokens) leaves "
                    f"only {max_allowed_completion} tokens for completion. "
                    f"Reduce prompt by ~{excess:,} tokens.",
                    estimated_tokens=total_tokens,
                    max_tokens=self.max_context,
                    excess_tokens=excess
                )

            logger.warning(
                f"Requested {max_completion_tokens:,} completion tokens, but only "
                f"{max_allowed_completion:,} available. Reducing automatically."
            )
            return prompt_tokens, max_allowed_completion

        return prompt_tokens, max_completion_tokens

    def validate_request(self, prompt: str, max_tokens: int) -> bool:
        """
        Validate request against context limits.

        Args:
            prompt: Prompt text
            max_tokens: Maximum completion tokens

        Returns:
            True if valid, False otherwise
        """
        try:
            self.estimate_prompt_tokens(prompt, max_tokens)
            return True
        except ContextOverflowError:
            return False

    def calculate_chunk_size(self, total_tokens: int, overlap_percent: float = 0.1) -> Tuple[int, int]:
        """
        Calculate optimal chunk size for large documents.

        Args:
            total_tokens: Total tokens in document
            overlap_percent: Overlap between chunks (0.0-1.0)

        Returns:
            Tuple of (chunk_size_tokens, number_of_chunks)
        """
        # Reserve space for completion
        usable_context = self.max_context - self.max_completion

        if total_tokens <= usable_context:
            return total_tokens, 1

        # Calculate overlap size
        overlap_tokens = int(usable_context * overlap_percent)
        effective_chunk = usable_context - overlap_tokens

        # Calculate number of chunks
        num_chunks = (total_tokens + effective_chunk - 1) // effective_chunk

        logger.info(
            f"Document requires chunking: {total_tokens:,} tokens -> "
            f"{num_chunks} chunks of ~{usable_context:,} tokens "
            f"({overlap_tokens:,} token overlap)"
        )

        return usable_context, num_chunks

    def estimate_processing_time(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Estimate processing time based on token counts.

        Args:
            prompt_tokens: Prompt tokens
            completion_tokens: Completion tokens

        Returns:
            Estimated time in seconds

        Note:
            Rates loaded from centralized config (GPU-dependent).
            Defaults: Prefill ~19,000 tokens/sec, Decode ~150 tokens/sec
        """
        # Load rates from centralized config
        try:
            from src.core.config import get_settings
            settings = get_settings()
            prefill_rate = settings.vllm_direct.vllm_prefill_rate  # tokens/sec
            decode_rate = settings.vllm_direct.vllm_decode_rate    # tokens/sec
        except Exception as e:
            logger.warning(f"Failed to load config rates: {e}, using defaults")
            prefill_rate = 19000  # Default fallback
            decode_rate = 150     # Default fallback

        # Prefill time (prompt processing)
        prefill_time = prompt_tokens / prefill_rate

        # Generation time (decode)
        generation_time = completion_tokens / decode_rate

        total_time = prefill_time + generation_time

        logger.debug(
            f"Estimated processing time: {total_time:.2f}s "
            f"(prefill: {prefill_time:.2f}s @ {prefill_rate} t/s, "
            f"decode: {generation_time:.2f}s @ {decode_rate} t/s)"
        )

        return total_time

    def get_stats(self) -> dict:
        """Get token estimator statistics."""
        return {
            "estimation_mode": "accurate (tiktoken)" if self.use_accurate else "fast (char-based)",
            "chars_per_token": self.chars_per_token,
            "max_context_tokens": self.max_context,
            "max_prompt_tokens": self.max_prompt,
            "max_completion_tokens": self.max_completion
        }
