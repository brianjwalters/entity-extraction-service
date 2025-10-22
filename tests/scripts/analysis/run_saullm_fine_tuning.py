#!/usr/bin/env python3
"""
SaulLM Fine-Tuning Execution Script

This script sets up and executes the fine-tuning of SaulLM-7B-Instruct
for legal entity extraction using dual A40 GPUs with DeepSpeed optimization.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_gpu_availability():
    """Check if both A40 GPUs are available."""
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used', '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error("Failed to query GPU information")
            return False
        
        gpu_info = result.stdout.strip().split('\n')
        logger.info(f"Found {len(gpu_info)} GPUs:")
        
        for i, info in enumerate(gpu_info):
            parts = info.split(', ')
            if len(parts) >= 3:
                name, total_mem, used_mem = parts[0], parts[1], parts[2]
                free_mem = int(total_mem) - int(used_mem)
                logger.info(f"  GPU {i}: {name}, Total: {total_mem}MB, Used: {used_mem}MB, Free: {free_mem}MB")
                
                # Check if we have enough free memory (need ~30GB for SaulLM-7B)
                if free_mem < 30000:
                    logger.warning(f"GPU {i} may not have enough free memory for fine-tuning")
        
        return len(gpu_info) >= 2
    
    except Exception as e:
        logger.error(f"Error checking GPU availability: {e}")
        return False

def install_dependencies():
    """Install required dependencies for fine-tuning."""
    logger.info("Installing fine-tuning dependencies...")
    
    requirements_file = Path(__file__).parent / "src" / "fine_tuning" / "requirements.txt"
    
    if not requirements_file.exists():
        logger.error(f"Requirements file not found: {requirements_file}")
        return False
    
    try:
        # Activate venv first
        venv_python = Path(__file__).parent / "venv" / "bin" / "python"
        
        cmd = [str(venv_python), "-m", "pip", "install", "-r", str(requirements_file)]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to install dependencies: {result.stderr}")
            return False
        
        logger.info("Dependencies installed successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error installing dependencies: {e}")
        return False

def setup_distributed_training():
    """Setup environment for distributed training."""
    logger.info("Setting up distributed training environment...")
    
    # Set environment variables for distributed training
    os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"  # Both A40 GPUs
    os.environ["WORLD_SIZE"] = "2"
    os.environ["MASTER_ADDR"] = "localhost"
    os.environ["MASTER_PORT"] = "29500"
    
    # DeepSpeed configuration
    os.environ["DEEPSPEED_CONFIG"] = "ds_config.json"
    
    logger.info("Distributed training environment configured")

def run_fine_tuning():
    """Execute the fine-tuning process."""
    logger.info("Starting SaulLM fine-tuning with DeepSpeed...")
    
    fine_tuning_script = Path(__file__).parent / "src" / "fine_tuning" / "saullm_fine_tuner.py"
    venv_python = Path(__file__).parent / "venv" / "bin" / "python"
    
    if not fine_tuning_script.exists():
        logger.error(f"Fine-tuning script not found: {fine_tuning_script}")
        return False
    
    try:
        # Change to the script directory
        script_dir = fine_tuning_script.parent
        original_cwd = os.getcwd()
        os.chdir(script_dir)
        
        # Run with DeepSpeed
        cmd = [
            str(venv_python), "-m", "deepspeed",
            "--num_gpus=2",
            "--master_port=29500",
            str(fine_tuning_script)
        ]
        
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        # Run the fine-tuning process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Stream output in real-time
        for line in iter(process.stdout.readline, ''):
            print(line.rstrip())
        
        process.wait()
        
        # Restore original directory
        os.chdir(original_cwd)
        
        if process.returncode == 0:
            logger.info("Fine-tuning completed successfully!")
            return True
        else:
            logger.error(f"Fine-tuning failed with return code: {process.returncode}")
            return False
    
    except Exception as e:
        logger.error(f"Error during fine-tuning execution: {e}")
        return False

def main():
    """Main execution function."""
    logger.info("=== SaulLM Legal Entity Extraction Fine-Tuning ===")
    
    # Check prerequisites
    logger.info("Checking prerequisites...")
    
    # Check GPU availability
    if not check_gpu_availability():
        logger.error("Insufficient GPU resources for fine-tuning")
        return False
    
    # Install dependencies
    if not install_dependencies():
        logger.error("Failed to install required dependencies")
        return False
    
    # Setup distributed training
    setup_distributed_training()
    
    # Execute fine-tuning
    success = run_fine_tuning()
    
    if success:
        logger.info("🎉 SaulLM fine-tuning completed successfully!")
        logger.info("📁 Fine-tuned model saved in: ./fine_tuned_saullm_legal/")
        logger.info("📊 Training logs available in wandb dashboard")
        logger.info("🚀 Model ready for legal entity extraction tasks")
    else:
        logger.error("❌ Fine-tuning failed. Check logs for details.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)