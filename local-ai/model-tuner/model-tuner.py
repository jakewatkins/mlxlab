#!/usr/bin/env python3
"""
Model Tuner - Fine-tune models using Apple's MLX framework with LoRA

This script wraps mlx_lm.lora to provide a simplified interface for fine-tuning
models with configuration stored in config.json.
"""

import argparse
import json
import os
import sys
import subprocess
from pathlib import Path


def load_config(script_dir):
    """Load and parse the config.json file from the script directory."""
    config_path = script_dir / "config.json"
    
    if not config_path.exists():
        print(f"Error: Configuration file not found at {config_path}")
        print("Please create a config.json file in the same directory as model-tuner.py")
        sys.exit(1)
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse config.json: {e}")
        sys.exit(1)
    
    # Validate required fields
    required_fields = ["iters", "steps-per-eval", "val-batches", "learning-rate", "lora-layers"]
    missing_fields = [field for field in required_fields if field not in config]
    
    if missing_fields:
        print(f"Error: Missing required fields in config.json: {', '.join(missing_fields)}")
        sys.exit(1)
    
    return config


def validate_data_directory(data_path):
    """Validate that the data directory exists and contains required JSONL files."""
    data_dir = Path(data_path)
    
    if not data_dir.exists():
        print(f"Error: Data directory does not exist: {data_path}")
        sys.exit(1)
    
    if not data_dir.is_dir():
        print(f"Error: Data path is not a directory: {data_path}")
        sys.exit(1)
    
    # Look for required MLX training files
    required_files = ["train.jsonl", "valid.jsonl", "test.jsonl"]
    missing_files = []
    
    for filename in required_files:
        file_path = data_dir / filename
        if not file_path.exists():
            missing_files.append(filename)
    
    if missing_files:
        print(f"Error: Missing required files in {data_path}:")
        for filename in missing_files:
            print(f"  - {filename}")
        sys.exit(1)


def validate_output_directory(output_path):
    """Validate that the output directory exists."""
    output_dir = Path(output_path)
    
    if not output_dir.exists():
        print(f"Error: Output directory does not exist: {output_path}")
        print("Please create the output directory before running the script.")
        sys.exit(1)
    
    if not output_dir.is_dir():
        print(f"Error: Output path is not a directory: {output_path}")
        sys.exit(1)


def run_mlx_lora(model, data_path, output_path, config):
    """Run mlx_lm.lora as a subprocess with the provided configuration."""
    
    # Construct the command
    cmd = [
        "python", "-m", "mlx_lm", "lora",
        "--model", model,
        "--train",
        "--data", data_path,
        "--iters", str(config["iters"]),
        "--steps-per-eval", str(config["steps-per-eval"]),
        "--val-batches", str(config["val-batches"]),
        "--learning-rate", str(config["learning-rate"]),
        "--num-layers", str(config["lora-layers"]),
        "--adapter-path", output_path
    ]
    
    # Add optional parameters if present in config
    if "batch-size" in config:
        cmd.extend(["--batch-size", str(config["batch-size"])])
    if "max-seq-length" in config:
        cmd.extend(["--max-seq-length", str(config["max-seq-length"])])
    
    print(f"\nStarting fine-tuning with the following configuration:")
    print(f"  Model: {model}")
    print(f"  Data: {data_path}")
    print(f"  Output: {output_path}")
    print(f"  Iterations: {config['iters']}")
    print(f"  Steps per eval: {config['steps-per-eval']}")
    print(f"  Validation batches: {config['val-batches']}")
    print(f"  Learning rate: {config['learning-rate']}")
    print(f"  Number of layers: {config['lora-layers']}")
    if "batch-size" in config:
        print(f"  Batch size: {config['batch-size']}")
    if "max-seq-length" in config:
        print(f"  Max sequence length: {config['max-seq-length']}")
    print(f"\nRunning command: {' '.join(cmd)}\n")
    
    try:
        # Run the command and stream output in real-time
        result = subprocess.run(cmd, check=True)
        print("\n✓ Fine-tuning completed successfully!")
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"\nError: Fine-tuning failed with exit code {e.returncode}")
        sys.exit(1)
    except FileNotFoundError:
        print("\nError: mlx_lm module not found. Please ensure MLX is installed:")
        print("  pip install mlx-lm")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Fine-tune models using Apple's MLX framework with LoRA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python model-tuner.py \\
    --model "microsoft/Phi-3-mini-4k-instruct" \\
    --data "/path/to/training-data" \\
    --output "/path/to/output"
        """
    )
    
    parser.add_argument(
        "--model",
        required=True,
        help="Model path or HuggingFace model ID (e.g., 'microsoft/Phi-3-mini-4k-instruct')"
    )
    
    parser.add_argument(
        "--data",
        required=True,
        help="Path to directory containing training data JSONL files"
    )
    
    parser.add_argument(
        "--output",
        required=True,
        help="Path to output directory for fine-tuned model adapters"
    )
    
    args = parser.parse_args()
    
    # Get script directory for config.json lookup
    script_dir = Path(__file__).parent.absolute()
    
    # Load configuration
    print("Loading configuration...")
    config = load_config(script_dir)
    
    # Validate data directory and files
    print(f"Validating data directory: {args.data}")
    validate_data_directory(args.data)
    
    # Validate output directory
    print(f"Validating output directory: {args.output}")
    validate_output_directory(args.output)
    
    # Run MLX LoRA fine-tuning
    run_mlx_lora(args.model, args.data, args.output, config)


if __name__ == "__main__":
    main()
