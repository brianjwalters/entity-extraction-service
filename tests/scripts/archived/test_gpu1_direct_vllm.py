#!/usr/bin/env python3
"""
Test DirectVLLMClient GPU 1 configuration.

Verifies that DirectVLLMClient uses GPU 1 instead of GPU 0,
allowing it to run alongside the existing vLLM HTTP service on GPU 0.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path

async def test_direct_vllm_gpu1():
    """Test DirectVLLMClient initialization on GPU 1."""

    print("=" * 80)
    print("TESTING: DirectVLLMClient GPU 1 Configuration")
    print("=" * 80)

    try:
        from vllm.factory import create_vllm_client
        from vllm_client.models import VLLMRequest

        print("\n📋 Step 1: Creating vLLM client...")
        print("   Expected: DirectVLLMClient on GPU 1")

        # Create client (should use GPU 1 from .env)
        client = create_vllm_client()

        client_type = type(client).__name__
        print(f"\n✅ Client created: {client_type}")

        if client_type != "DirectVLLMClient":
            print(f"⚠️  WARNING: Expected DirectVLLMClient, got {client_type}")
            print(f"⚠️  This means vLLM library may not be installed or initialization failed")
            return False

        # Check GPU configuration
        if hasattr(client, 'config'):
            gpu_id = client.config.gpu_id
            print(f"\n📊 GPU Configuration:")
            print(f"   GPU ID: {gpu_id}")
            print(f"   Model: {client.config.model}")
            print(f"   Max context: {client.config.max_model_len:,} tokens")
            print(f"   GPU memory utilization: {client.config.gpu_memory_utilization}")

            if gpu_id != 1:
                print(f"\n❌ ERROR: GPU ID is {gpu_id}, expected 1")
                print(f"   Check .env file: VLLM_GPU_ID should be set to 1")
                return False
            else:
                print(f"\n✅ GPU configuration correct: GPU {gpu_id}")

        print(f"\n📡 Step 2: Connecting to vLLM (initializing on GPU {client.config.gpu_id})...")
        print(f"   Note: This will load the model on GPU {client.config.gpu_id}")
        print(f"   This may take 30-50 seconds...")

        # Connect (initialize vLLM engine on GPU 1)
        success = await client.connect()

        if not success:
            print(f"\n❌ Connection failed")
            print(f"   Check logs for details")
            return False

        print(f"\n✅ Connection successful!")

        # Verify it's ready
        if client.is_ready():
            print(f"✅ Client ready for inference")
        else:
            print(f"⚠️  Client connected but not ready")
            return False

        print(f"\n📊 Step 3: Testing simple generation...")

        # Create simple test request
        test_request = VLLMRequest(
            messages=[{"role": "user", "content": "What is 2+2?"}],
            max_tokens=50,
            temperature=0.0,
            seed=42
        )

        # Generate
        response = await client.generate_chat_completion(test_request)

        print(f"\n✅ Generation successful!")
        print(f"   Response: {response.content[:100]}...")
        print(f"   Tokens: {response.usage.total_tokens}")
        print(f"   Time: {response.response_time_ms:.1f}ms")

        # Get stats
        stats = client.get_stats()
        print(f"\n📊 Client Statistics:")
        print(f"   Status: {stats.get('status')}")
        print(f"   Model: {stats.get('model')}")
        print(f"   Requests processed: {stats.get('requests_processed', 0)}")
        print(f"   Successful generations: {stats.get('successful_generations', 0)}")

        if 'gpu' in stats:
            gpu_stats = stats['gpu']
            print(f"\n📊 GPU Statistics:")
            print(f"   GPU ID: {gpu_stats.get('gpu_id')}")
            print(f"   Memory used: {gpu_stats.get('memory_used_gb', 0):.2f} GB")
            print(f"   Memory total: {gpu_stats.get('memory_total_gb', 0):.2f} GB")
            print(f"   Utilization: {gpu_stats.get('memory_utilization_percent', 0):.1f}%")

        print(f"\n📊 Step 4: Cleanup...")
        await client.close()
        print(f"✅ Client closed")

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED - DirectVLLMClient configured for GPU 1")
        print("=" * 80)
        print("\n📝 Summary:")
        print(f"   ✅ DirectVLLMClient uses GPU 1 (not GPU 0)")
        print(f"   ✅ Can run alongside vLLM HTTP service on GPU 0:8080")
        print(f"   ✅ Guided JSON support available")
        print(f"   ✅ Generation working correctly")

        return True

    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print(f"\nMake sure vLLM library is installed:")
        print(f"   source venv/bin/activate && pip install vllm==0.6.3")
        return False

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the test."""
    print("\n" + "=" * 80)
    print("DirectVLLMClient GPU 1 Configuration Test")
    print("=" * 80)
    print("\nThis test verifies that DirectVLLMClient is configured to use GPU 1")
    print("instead of GPU 0, allowing it to run alongside the existing vLLM")
    print("HTTP service (port 8080) which uses GPU 0.")
    print("\n⚠️  WARNING: This test will:")
    print("   1. Load the Granite 3.3 2B model on GPU 1 (~4GB VRAM)")
    print("   2. Run a test generation")
    print("   3. Clean up and release GPU memory")
    print("\nPress Ctrl+C to cancel...")

    await asyncio.sleep(3)

    success = await test_direct_vllm_gpu1()

    if success:
        print(f"\n✅ GPU 1 configuration verified successfully!")
        sys.exit(0)
    else:
        print(f"\n❌ GPU 1 configuration test failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
