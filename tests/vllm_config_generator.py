#!/usr/bin/env python3
"""
vLLM Configuration Generator for Optimization Testing
Generates 24 different configurations for testing vLLM performance on dual NVIDIA A40 GPUs
"""

import json
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
import argparse


@dataclass
class VLLMConfig:
    """Complete vLLM configuration for testing"""
    config_id: str
    name: str
    description: str
    gpu_setup: str  # "single" or "dual"
    gpu_devices: str  # CUDA_VISIBLE_DEVICES value
    tensor_parallel_size: int
    memory_utilization: float
    max_model_len: int
    max_num_seqs: int
    max_num_batched_tokens: int
    enable_prefix_caching: bool
    enable_chunked_prefill: bool
    max_num_batched_tokens_chunked: Optional[int] = None
    swap_space: int = 4
    block_size: int = 16
    num_scheduler_steps: int = 1
    speculative_model: Optional[str] = None
    num_speculative_tokens: Optional[int] = None
    use_v2_block_manager: bool = False
    enable_lora: bool = False
    max_lora_rank: Optional[int] = None
    max_cpu_loras: Optional[int] = None
    quantization: Optional[str] = None
    kv_cache_dtype: str = "auto"
    dtype: str = "auto"
    enforce_eager: bool = False
    disable_custom_all_reduce: bool = False
    tokenizer_pool_size: int = 0
    tokenizer_pool_type: str = "ray"
    disable_log_stats: bool = False
    disable_log_requests: bool = True
    trust_remote_code: bool = True
    download_dir: Optional[str] = None
    load_format: str = "auto"
    config_name: str = ""
    test_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def get_vllm_args(self) -> List[str]:
        """Generate vLLM command-line arguments"""
        args = [
            "python", "-m", "vllm.entrypoints.openai.api_server",
            "--model", "mistralai/Mistral-Nemo-Instruct-2407",
            "--host", "0.0.0.0",
            "--port", "8080",
            "--tensor-parallel-size", str(self.tensor_parallel_size),
            "--gpu-memory-utilization", str(self.memory_utilization),
            "--max-model-len", str(self.max_model_len),
            "--max-num-seqs", str(self.max_num_seqs),
            "--max-num-batched-tokens", str(self.max_num_batched_tokens),
            "--swap-space", str(self.swap_space),
            "--block-size", str(self.block_size),
            "--num-scheduler-steps", str(self.num_scheduler_steps),
            "--kv-cache-dtype", self.kv_cache_dtype,
            "--dtype", self.dtype,
            "--tokenizer-pool-size", str(self.tokenizer_pool_size),
            "--tokenizer-pool-type", self.tokenizer_pool_type,
            "--load-format", self.load_format,
            "--served-model-name", "mistral-nemo-12b-instruct-128k"
        ]
        
        if self.enable_prefix_caching:
            args.append("--enable-prefix-caching")
        
        if self.enable_chunked_prefill:
            args.append("--enable-chunked-prefill")
            if self.max_num_batched_tokens_chunked:
                args.extend(["--max-num-batched-tokens-chunked", str(self.max_num_batched_tokens_chunked)])
        
        if self.use_v2_block_manager:
            args.append("--use-v2-block-manager")
        
        if self.enable_lora:
            args.append("--enable-lora")
            if self.max_lora_rank:
                args.extend(["--max-lora-rank", str(self.max_lora_rank)])
            if self.max_cpu_loras:
                args.extend(["--max-cpu-loras", str(self.max_cpu_loras)])
        
        if self.quantization:
            args.extend(["--quantization", self.quantization])
        
        if self.enforce_eager:
            args.append("--enforce-eager")
        
        if self.disable_custom_all_reduce:
            args.append("--disable-custom-all-reduce")
        
        if self.disable_log_stats:
            args.append("--disable-log-stats")
        
        if self.disable_log_requests:
            args.append("--disable-log-requests")
        
        if self.trust_remote_code:
            args.append("--trust-remote-code")
        
        if self.download_dir:
            args.extend(["--download-dir", self.download_dir])
        
        if self.speculative_model:
            args.extend(["--speculative-model", self.speculative_model])
            if self.num_speculative_tokens:
                args.extend(["--num-speculative-tokens", str(self.num_speculative_tokens)])
        
        return args
    
    def get_command_string(self) -> str:
        """Get the complete command as a string"""
        return " ".join(self.get_vllm_args())
    
    def get_systemd_service(self) -> str:
        """Generate systemd service file content"""
        service_content = f"""[Unit]
Description=vLLM Service - {self.name}
Documentation=https://docs.vllm.ai
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/luris
Environment="PATH=/usr/local/cuda/bin:/usr/local/bin:/usr/bin:/bin"
Environment="CUDA_VISIBLE_DEVICES={self.gpu_devices}"
Environment="VLLM_USE_V1=1"
Environment="VLLM_WORKER_MULTIPROC_METHOD=spawn"
Environment="PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True"
Environment="CUDA_LAUNCH_BLOCKING=0"
Environment="TOKENIZERS_PARALLELISM=false"
Environment="OMP_NUM_THREADS=1"
Environment="RAY_DEDUP_LOGS=0"

# Performance tuning for {self.description}
Environment="VLLM_ATTENTION_BACKEND=FLASH_ATTN"
Environment="VLLM_CPU_KVCACHE_SPACE=0"
Environment="VLLM_GPU_MEMORY_UTILIZATION={self.memory_utilization}"

ExecStart={self.get_command_string()}

# Restart configuration
Restart=on-failure
RestartSec=10
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=90
StandardOutput=journal
StandardError=journal

# Resource limits
LimitNOFILE=65535
LimitNPROC=32768
TasksMax=infinity

[Install]
WantedBy=multi-user.target
"""
        return service_content
    
    def get_env_vars(self) -> Dict[str, str]:
        """Get environment variables for this configuration"""
        env_vars = {
            "CUDA_VISIBLE_DEVICES": self.gpu_devices,
            "VLLM_USE_V1": "1",
            "VLLM_WORKER_MULTIPROC_METHOD": "spawn",
            "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
            "CUDA_LAUNCH_BLOCKING": "0",
            "TOKENIZERS_PARALLELISM": "false",
            "OMP_NUM_THREADS": "1",
            "RAY_DEDUP_LOGS": "0",
            "VLLM_ATTENTION_BACKEND": "FLASH_ATTN",
            "VLLM_CPU_KVCACHE_SPACE": "0",
            "VLLM_GPU_MEMORY_UTILIZATION": str(self.memory_utilization)
        }
        return env_vars
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            **asdict(self),
            "command": self.get_command_string(),
            "env_vars": self.get_env_vars()
        }


class VLLMConfigGenerator:
    """Generator for vLLM test configurations"""
    
    def __init__(self):
        self.configs: List[VLLMConfig] = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def generate_all_configs(self) -> List[VLLMConfig]:
        """Generate all 24 test configurations"""
        
        # Configuration matrix
        memory_levels = [0.85, 0.90, 0.95]
        batch_configs = [
            {"max_num_seqs": 128, "max_num_batched_tokens": 32768},
            {"max_num_seqs": 256, "max_num_batched_tokens": 65536},
            {"max_num_seqs": 512, "max_num_batched_tokens": 131072},
        ]
        
        config_counter = 1
        
        # ========== SINGLE GPU CONFIGURATIONS (12 configs) ==========
        
        # Basic single GPU configurations (3 configs)
        for mem_util in memory_levels:
            config = VLLMConfig(
                config_id=f"single_gpu_config_{config_counter:03d}",
                name=f"Single GPU Basic - {int(mem_util*100)}% Memory",
                description=f"Baseline single GPU configuration with {int(mem_util*100)}% memory utilization",
                gpu_setup="single",
                gpu_devices="0",
                tensor_parallel_size=1,
                memory_utilization=mem_util,
                max_model_len=131072,
                max_num_seqs=256,
                max_num_batched_tokens=65536,
                enable_prefix_caching=False,
                enable_chunked_prefill=False,
                trust_remote_code=True
            )
            self.configs.append(config)
            config_counter += 1
        
        # Single GPU with prefix caching (3 configs)
        for batch_config in batch_configs:
            config = VLLMConfig(
                config_id=f"single_gpu_config_{config_counter:03d}",
                name=f"Single GPU Prefix Cache - Batch {batch_config['max_num_seqs']}",
                description=f"Single GPU with prefix caching, batch size {batch_config['max_num_seqs']}",
                gpu_setup="single",
                gpu_devices="0",
                tensor_parallel_size=1,
                memory_utilization=0.90,
                max_model_len=131072,
                **batch_config,
                enable_prefix_caching=True,
                enable_chunked_prefill=False,
                trust_remote_code=True
            )
            self.configs.append(config)
            config_counter += 1
        
        # Single GPU with chunked prefill (3 configs)
        chunked_tokens = [8192, 16384, 32768]
        for i, chunk_size in enumerate(chunked_tokens):
            config = VLLMConfig(
                config_id=f"single_gpu_config_{config_counter:03d}",
                name=f"Single GPU Chunked Prefill - {chunk_size} tokens",
                description=f"Single GPU with chunked prefill, chunk size {chunk_size}",
                gpu_setup="single",
                gpu_devices="0",
                tensor_parallel_size=1,
                memory_utilization=0.90,
                max_model_len=131072,
                max_num_seqs=256,
                max_num_batched_tokens=65536,
                enable_prefix_caching=False,
                enable_chunked_prefill=True,
                max_num_batched_tokens_chunked=chunk_size,
                trust_remote_code=True
            )
            self.configs.append(config)
            config_counter += 1
        
        # Single GPU optimized configurations (3 configs)
        optimization_configs = [
            {
                "name": "KV Cache Optimized",
                "kv_cache_dtype": "fp8",
                "block_size": 32,
                "num_scheduler_steps": 2
            },
            {
                "name": "V2 Block Manager",
                "use_v2_block_manager": True,
                "block_size": 16,
                "num_scheduler_steps": 1
            },
            {
                "name": "Full Optimization",
                "enable_prefix_caching": True,
                "enable_chunked_prefill": True,
                "max_num_batched_tokens_chunked": 16384,
                "kv_cache_dtype": "fp8",
                "use_v2_block_manager": True
            }
        ]
        
        for opt_config in optimization_configs:
            config = VLLMConfig(
                config_id=f"single_gpu_config_{config_counter:03d}",
                name=f"Single GPU {opt_config['name']}",
                description=f"Single GPU with {opt_config['name'].lower()} settings",
                gpu_setup="single",
                gpu_devices="0",
                tensor_parallel_size=1,
                memory_utilization=0.92,
                max_model_len=131072,
                max_num_seqs=256,
                max_num_batched_tokens=65536,
                enable_prefix_caching=opt_config.get("enable_prefix_caching", False),
                enable_chunked_prefill=opt_config.get("enable_chunked_prefill", False),
                max_num_batched_tokens_chunked=opt_config.get("max_num_batched_tokens_chunked"),
                kv_cache_dtype=opt_config.get("kv_cache_dtype", "auto"),
                block_size=opt_config.get("block_size", 16),
                num_scheduler_steps=opt_config.get("num_scheduler_steps", 1),
                use_v2_block_manager=opt_config.get("use_v2_block_manager", False),
                trust_remote_code=True
            )
            self.configs.append(config)
            config_counter += 1
        
        # ========== DUAL GPU CONFIGURATIONS (12 configs) ==========
        
        # Basic dual GPU configurations (3 configs)
        for mem_util in memory_levels:
            config = VLLMConfig(
                config_id=f"dual_gpu_config_{config_counter:03d}",
                name=f"Dual GPU Basic - {int(mem_util*100)}% Memory",
                description=f"Tensor parallel dual GPU with {int(mem_util*100)}% memory utilization",
                gpu_setup="dual",
                gpu_devices="0,1",
                tensor_parallel_size=2,
                memory_utilization=mem_util,
                max_model_len=131072,
                max_num_seqs=512,
                max_num_batched_tokens=131072,
                enable_prefix_caching=False,
                enable_chunked_prefill=False,
                trust_remote_code=True
            )
            self.configs.append(config)
            config_counter += 1
        
        # Dual GPU with increased batch sizes (3 configs)
        large_batch_configs = [
            {"max_num_seqs": 512, "max_num_batched_tokens": 131072},
            {"max_num_seqs": 768, "max_num_batched_tokens": 196608},
            {"max_num_seqs": 1024, "max_num_batched_tokens": 262144},
        ]
        
        for batch_config in large_batch_configs:
            config = VLLMConfig(
                config_id=f"dual_gpu_config_{config_counter:03d}",
                name=f"Dual GPU Large Batch - {batch_config['max_num_seqs']} seqs",
                description=f"Dual GPU with large batch size {batch_config['max_num_seqs']}",
                gpu_setup="dual",
                gpu_devices="0,1",
                tensor_parallel_size=2,
                memory_utilization=0.90,
                max_model_len=131072,
                **batch_config,
                enable_prefix_caching=True,
                enable_chunked_prefill=False,
                trust_remote_code=True
            )
            self.configs.append(config)
            config_counter += 1
        
        # Dual GPU with advanced optimizations (3 configs)
        dual_optimizations = [
            {
                "name": "Prefix + Chunked",
                "enable_prefix_caching": True,
                "enable_chunked_prefill": True,
                "max_num_batched_tokens_chunked": 32768
            },
            {
                "name": "FP8 KV Cache",
                "enable_prefix_caching": True,
                "kv_cache_dtype": "fp8",
                "block_size": 32
            },
            {
                "name": "Maximum Performance",
                "enable_prefix_caching": True,
                "enable_chunked_prefill": True,
                "max_num_batched_tokens_chunked": 65536,
                "kv_cache_dtype": "fp8",
                "use_v2_block_manager": True,
                "num_scheduler_steps": 4
            }
        ]
        
        for opt_config in dual_optimizations:
            config = VLLMConfig(
                config_id=f"dual_gpu_config_{config_counter:03d}",
                name=f"Dual GPU {opt_config['name']}",
                description=f"Dual GPU with {opt_config['name'].lower()} optimizations",
                gpu_setup="dual",
                gpu_devices="0,1",
                tensor_parallel_size=2,
                memory_utilization=0.92,
                max_model_len=131072,
                max_num_seqs=768,
                max_num_batched_tokens=196608,
                enable_prefix_caching=opt_config.get("enable_prefix_caching", False),
                enable_chunked_prefill=opt_config.get("enable_chunked_prefill", False),
                max_num_batched_tokens_chunked=opt_config.get("max_num_batched_tokens_chunked"),
                kv_cache_dtype=opt_config.get("kv_cache_dtype", "auto"),
                block_size=opt_config.get("block_size", 16),
                num_scheduler_steps=opt_config.get("num_scheduler_steps", 1),
                use_v2_block_manager=opt_config.get("use_v2_block_manager", False),
                trust_remote_code=True
            )
            self.configs.append(config)
            config_counter += 1
        
        # Dual GPU extreme configurations (3 configs)
        extreme_configs = [
            {
                "name": "Ultra Low Latency",
                "max_num_seqs": 32,
                "max_num_batched_tokens": 8192,
                "enforce_eager": True,
                "num_scheduler_steps": 1
            },
            {
                "name": "Ultra High Throughput",
                "max_num_seqs": 2048,
                "max_num_batched_tokens": 524288,
                "memory_utilization": 0.95,
                "swap_space": 8
            },
            {
                "name": "Balanced Extreme",
                "max_num_seqs": 1024,
                "max_num_batched_tokens": 262144,
                "memory_utilization": 0.93,
                "enable_prefix_caching": True,
                "enable_chunked_prefill": True,
                "max_num_batched_tokens_chunked": 49152,
                "kv_cache_dtype": "fp8"
            }
        ]
        
        for ext_config in extreme_configs:
            config = VLLMConfig(
                config_id=f"dual_gpu_config_{config_counter:03d}",
                name=f"Dual GPU {ext_config['name']}",
                description=f"Dual GPU {ext_config['name'].lower()} configuration",
                gpu_setup="dual",
                gpu_devices="0,1",
                tensor_parallel_size=2,
                memory_utilization=ext_config.get("memory_utilization", 0.90),
                max_model_len=131072,
                max_num_seqs=ext_config.get("max_num_seqs", 512),
                max_num_batched_tokens=ext_config.get("max_num_batched_tokens", 131072),
                enable_prefix_caching=ext_config.get("enable_prefix_caching", False),
                enable_chunked_prefill=ext_config.get("enable_chunked_prefill", False),
                max_num_batched_tokens_chunked=ext_config.get("max_num_batched_tokens_chunked"),
                kv_cache_dtype=ext_config.get("kv_cache_dtype", "auto"),
                enforce_eager=ext_config.get("enforce_eager", False),
                num_scheduler_steps=ext_config.get("num_scheduler_steps", 1),
                swap_space=ext_config.get("swap_space", 4),
                trust_remote_code=True
            )
            self.configs.append(config)
            config_counter += 1
        
        return self.configs
    
    def save_configs(self, output_dir: Path):
        """Save all configurations to files"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save individual config files
        for config in self.configs:
            # Save JSON config
            config_file = output_dir / f"{config.config_id}.json"
            with open(config_file, 'w') as f:
                json.dump(config.to_dict(), f, indent=2)
            
            # Save systemd service file
            service_file = output_dir / f"{config.config_id}.service"
            with open(service_file, 'w') as f:
                f.write(config.get_systemd_service())
            
            # Save shell script
            script_file = output_dir / f"{config.config_id}.sh"
            with open(script_file, 'w') as f:
                f.write(self._generate_shell_script(config))
            script_file.chmod(0o755)
        
        # Save master configuration file
        master_config = {
            "timestamp": self.timestamp,
            "total_configs": len(self.configs),
            "configs": [config.to_dict() for config in self.configs]
        }
        
        master_file = output_dir / f"vllm_configs_{self.timestamp}.json"
        with open(master_file, 'w') as f:
            json.dump(master_config, f, indent=2)
        
        # Generate summary report
        self._generate_summary_report(output_dir)
        
        print(f"Generated {len(self.configs)} configurations in {output_dir}")
        print(f"Master config: {master_file}")
    
    def _generate_shell_script(self, config: VLLMConfig) -> str:
        """Generate shell script for running a configuration"""
        script = f"""#!/bin/bash
# vLLM Configuration: {config.config_id}
# {config.name}
# {config.description}

# Set environment variables
{chr(10).join(f'export {k}="{v}"' for k, v in config.get_env_vars().items())}

# Configuration details
echo "=========================================="
echo "Running vLLM Configuration: {config.config_id}"
echo "Name: {config.name}"
echo "GPU Setup: {config.gpu_setup}"
echo "GPUs: {config.gpu_devices}"
echo "Tensor Parallel Size: {config.tensor_parallel_size}"
echo "Memory Utilization: {config.memory_utilization}"
echo "Max Sequences: {config.max_num_seqs}"
echo "Max Batched Tokens: {config.max_num_batched_tokens}"
echo "Prefix Caching: {config.enable_prefix_caching}"
echo "Chunked Prefill: {config.enable_chunked_prefill}"
echo "=========================================="

# Check if vLLM is already running
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null ; then
    echo "Port 8080 is already in use. Please stop the existing vLLM service first."
    exit 1
fi

# Start vLLM
echo "Starting vLLM with configuration {config.config_id}..."
{config.get_command_string()}
"""
        return script
    
    def _generate_summary_report(self, output_dir: Path):
        """Generate a summary report of all configurations"""
        report_file = output_dir / f"configuration_summary_{self.timestamp}.md"
        
        with open(report_file, 'w') as f:
            f.write("# vLLM Configuration Test Suite\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Total Configurations: {len(self.configs)}\n\n")
            
            f.write("## Configuration Overview\n\n")
            
            # Single GPU configs
            f.write("### Single GPU Configurations (12 configs)\n\n")
            f.write("| Config ID | Name | Memory % | Batch Size | Features |\n")
            f.write("|-----------|------|----------|------------|----------|\n")
            
            for config in self.configs[:12]:
                features = []
                if config.enable_prefix_caching:
                    features.append("Prefix Cache")
                if config.enable_chunked_prefill:
                    features.append("Chunked Prefill")
                if config.kv_cache_dtype != "auto":
                    features.append(f"KV: {config.kv_cache_dtype}")
                if config.use_v2_block_manager:
                    features.append("V2 Block Mgr")
                
                f.write(f"| {config.config_id} | {config.name[:30]} | "
                       f"{int(config.memory_utilization*100)}% | "
                       f"{config.max_num_seqs} | "
                       f"{', '.join(features) or 'Baseline'} |\n")
            
            # Dual GPU configs
            f.write("\n### Dual GPU Configurations (12 configs)\n\n")
            f.write("| Config ID | Name | Memory % | Batch Size | Features |\n")
            f.write("|-----------|------|----------|------------|----------|\n")
            
            for config in self.configs[12:]:
                features = []
                if config.enable_prefix_caching:
                    features.append("Prefix Cache")
                if config.enable_chunked_prefill:
                    features.append("Chunked Prefill")
                if config.kv_cache_dtype != "auto":
                    features.append(f"KV: {config.kv_cache_dtype}")
                if config.use_v2_block_manager:
                    features.append("V2 Block Mgr")
                if config.enforce_eager:
                    features.append("Eager Mode")
                
                f.write(f"| {config.config_id} | {config.name[:30]} | "
                       f"{int(config.memory_utilization*100)}% | "
                       f"{config.max_num_seqs} | "
                       f"{', '.join(features) or 'Baseline'} |\n")
            
            f.write("\n## Testing Instructions\n\n")
            f.write("1. **Stop existing vLLM service**: `sudo systemctl stop luris-vllm`\n")
            f.write("2. **Run a configuration**: `./single_gpu_config_001.sh`\n")
            f.write("3. **Or use systemd**:\n")
            f.write("   ```bash\n")
            f.write("   sudo cp single_gpu_config_001.service /etc/systemd/system/luris-vllm-test.service\n")
            f.write("   sudo systemctl daemon-reload\n")
            f.write("   sudo systemctl start luris-vllm-test\n")
            f.write("   ```\n")
            f.write("4. **Run benchmarks**: Use the benchmark suite to test each configuration\n")
            f.write("5. **Collect metrics**: GPU utilization, throughput, latency, memory usage\n\n")
            
            f.write("## Key Parameters Tested\n\n")
            f.write("- **Memory Utilization**: 85%, 90%, 95%\n")
            f.write("- **Batch Sizes**: 32-2048 sequences\n")
            f.write("- **Batched Tokens**: 8K-524K tokens\n")
            f.write("- **Prefix Caching**: Enabled/Disabled\n")
            f.write("- **Chunked Prefill**: Various chunk sizes (8K, 16K, 32K, 64K)\n")
            f.write("- **KV Cache**: auto, fp8\n")
            f.write("- **Block Manager**: V1, V2\n")
            f.write("- **Tensor Parallelism**: Single GPU vs Dual GPU\n\n")
            
            f.write("## Files Generated\n\n")
            f.write(f"- **Master Config**: `vllm_configs_{self.timestamp}.json`\n")
            f.write("- **Individual Configs**: `<config_id>.json`\n")
            f.write("- **Systemd Services**: `<config_id>.service`\n")
            f.write("- **Shell Scripts**: `<config_id>.sh`\n")
            f.write(f"- **This Report**: `configuration_summary_{self.timestamp}.md`\n")
        
        print(f"Summary report saved to: {report_file}")


def main():
    parser = argparse.ArgumentParser(description="Generate vLLM test configurations")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="/srv/luris/be/entity-extraction-service/tests/vllm_configs",
        help="Output directory for configurations"
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only list configurations without saving files"
    )
    
    args = parser.parse_args()
    
    generator = VLLMConfigGenerator()
    configs = generator.generate_all_configs()
    
    if args.list_only:
        print(f"Generated {len(configs)} configurations:\n")
        for config in configs:
            print(f"{config.config_id}: {config.name}")
            print(f"  GPU: {config.gpu_setup} ({config.gpu_devices})")
            print(f"  Memory: {int(config.memory_utilization*100)}%")
            print(f"  Batch: {config.max_num_seqs} seqs, {config.max_num_batched_tokens} tokens")
            print(f"  Features: Prefix={config.enable_prefix_caching}, "
                  f"Chunked={config.enable_chunked_prefill}, "
                  f"KV={config.kv_cache_dtype}")
            print()
    else:
        output_dir = Path(args.output_dir)
        generator.save_configs(output_dir)
        print(f"\nAll configurations saved to: {output_dir}")
        print("\nTo run a configuration:")
        print(f"  cd {output_dir}")
        print("  ./single_gpu_config_001.sh")
        print("\nOr install as systemd service:")
        print(f"  sudo cp {output_dir}/single_gpu_config_001.service /etc/systemd/system/luris-vllm-test.service")
        print("  sudo systemctl daemon-reload")
        print("  sudo systemctl start luris-vllm-test")


if __name__ == "__main__":
    main()