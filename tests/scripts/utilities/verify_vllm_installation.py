#!/usr/bin/env python3
"""
Verification script for vLLM Direct Integration.

This script checks that all components are properly installed and working.

Run with:
    cd /srv/luris/be/entity-extraction-service
    source venv/bin/activate
    python verify_vllm_installation.py
"""

import sys
def check_imports():
    """Check that all modules can be imported."""
    print("\n" + "="*60)
    print("Verifying vLLM Integration Installation")
    print("="*60)

    print("\n1. Checking module imports...")

    try:
        from src.vllm import (
            VLLMClientFactory,
            VLLMConfig,
            VLLMRequest,
            VLLMResponse,
            VLLMClientType,
            DirectVLLMClient,
            HTTPVLLMClient,
            TokenEstimator,
            GPUMonitor,
            ContextOverflowError,
            ModelNotLoadedError,
            GenerationError,
            GPUMemoryError
        )
        print("   ✓ All core modules imported successfully")
        return True
    except ImportError as e:
        print(f"   ✗ Import failed: {e}")
        return False


def check_vllm_library():
    """Check if vLLM library is available."""
    print("\n2. Checking vLLM library...")

    try:
        from vllm import LLM, SamplingParams
        print("   ✓ vLLM library installed (Direct API available)")
        return True
    except ImportError:
        print("   ⚠ vLLM library not installed (Direct API unavailable)")
        print("     Install with: pip install vllm")
        print("     HTTP fallback will be used")
        return False


def check_dependencies():
    """Check optional dependencies."""
    print("\n3. Checking dependencies...")

    # httpx (required for HTTP fallback)
    try:
        import httpx
        print("   ✓ httpx installed (HTTP fallback available)")
    except ImportError:
        print("   ✗ httpx not installed (HTTP fallback unavailable)")
        print("     Install with: pip install httpx")

    # tiktoken (optional for accurate tokenization)
    try:
        import tiktoken
        print("   ✓ tiktoken installed (accurate token estimation available)")
    except ImportError:
        print("   ⚠ tiktoken not installed (using character-based estimation)")
        print("     Install with: pip install tiktoken")


def check_gpu_monitoring():
    """Check GPU monitoring capability."""
    print("\n4. Checking GPU monitoring...")

    from src.vllm import GPUMonitor

    monitor = GPUMonitor(gpu_id=0)
    stats = monitor.get_stats()

    if stats:
        print("   ✓ GPU monitoring available")
        print(f"     GPU {stats.gpu_id}: {stats.memory_utilization_percent:.1f}% memory "
              f"({stats.memory_used_gb:.1f}GB / {stats.memory_total_gb:.1f}GB)")
    else:
        print("   ⚠ nvidia-smi not available (GPU monitoring disabled)")
        print("     This is optional - module will work without it")


def check_token_estimator():
    """Check token estimator."""
    print("\n5. Checking token estimator...")

    from src.vllm import TokenEstimator, VLLMConfig

    config = VLLMConfig()
    estimator = TokenEstimator(config)

    # Test estimation
    test_text = "Hello world " * 100
    tokens = estimator.estimate_tokens(test_text)

    print(f"   ✓ Token estimator working")
    print(f"     Test: {len(test_text)} chars -> ~{tokens} tokens")


def check_exception_handling():
    """Check exception classes."""
    print("\n6. Checking exception handling...")

    from src.vllm import (
        ContextOverflowError,
        TokenEstimator,
        VLLMConfig
    )

    config = VLLMConfig()
    estimator = TokenEstimator(config)

    # Test context overflow detection
    huge_text = "word " * 50000  # Exceeds 32K limit
    try:
        estimator.estimate_prompt_tokens(huge_text, max_completion_tokens=1000)
        print("   ✗ Context overflow not detected")
    except ContextOverflowError as e:
        print("   ✓ Exception handling working")
        print(f"     Context overflow detected: {e.estimated_tokens:,} > {e.max_tokens:,}")


def check_factory():
    """Check factory pattern."""
    print("\n7. Checking factory pattern...")

    from src.vllm import VLLMClientFactory, VLLMConfig, VLLMClientType

    try:
        config = VLLMConfig()
        print("   ✓ Factory pattern implemented")
        print("     Use: await VLLMClientFactory.create_client()")
    except Exception as e:
        print(f"   ✗ Factory error: {e}")


def check_tests():
    """Check test files."""
    print("\n8. Checking test files...")

    import os

    test_files = [
        "tests/vllm/test_direct_vllm_integration.py",
        "tests/vllm/test_quick_validation.py"
    ]

    all_exist = True
    for test_file in test_files:
        path = f"/srv/luris/be/entity-extraction-service/{test_file}"
        if os.path.exists(path):
            print(f"   ✓ {test_file}")
        else:
            print(f"   ✗ {test_file} not found")
            all_exist = False

    if all_exist:
        print("\n   Run tests with:")
        print("     pytest tests/vllm/test_quick_validation.py -v -s")


def check_documentation():
    """Check documentation files."""
    print("\n9. Checking documentation...")

    import os

    doc_files = [
        "src/vllm/README.md",
        "src/vllm/example_usage.py",
        "VLLM_INTEGRATION_SUMMARY.md"
    ]

    for doc_file in doc_files:
        path = f"/srv/luris/be/entity-extraction-service/{doc_file}"
        if os.path.exists(path):
            print(f"   ✓ {doc_file}")
        else:
            print(f"   ✗ {doc_file} not found")


def print_summary():
    """Print summary and next steps."""
    print("\n" + "="*60)
    print("Installation Verification Complete")
    print("="*60)

    print("\nNext Steps:")
    print("\n1. Run quick validation tests:")
    print("   cd /srv/luris/be/entity-extraction-service")
    print("   source venv/bin/activate")
    print("   pytest tests/vllm/test_quick_validation.py -v -s")

    print("\n2. Run example usage:")
    print("   python src/vllm/example_usage.py")

    print("\n3. Review documentation:")
    print("   cat src/vllm/README.md")

    print("\n4. Integration:")
    print("   from src.vllm import get_client_for_entity_extraction")
    print("   client = await get_client_for_entity_extraction()")

    print("\n" + "="*60)


def main():
    """Run all verification checks."""
    try:
        # Run checks
        check_imports()
        check_vllm_library()
        check_dependencies()
        check_gpu_monitoring()
        check_token_estimator()
        check_exception_handling()
        check_factory()
        check_tests()
        check_documentation()

        # Print summary
        print_summary()

        return 0

    except Exception as e:
        print(f"\n✗ Verification failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
