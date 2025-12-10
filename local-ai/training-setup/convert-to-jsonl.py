#!/usr/bin/env python3
"""
Convert Training Data to JSONL Format
Converts classified email JSON data to JSONL format for MLX-LM LoRA fine-tuning
"""

import json
import sys
import argparse
from pathlib import Path


def convert_simple_format(content, classification):
    """
    Simple prompt-completion format (recommended)
    """
    text = f"Classify this email:\n\n{content}\n\nCategory: {classification}"
    return {"text": text}


def convert_instruction_format(content, classification):
    """
    Instruction format with separate input/output fields
    """
    return {
        "instruction": "Classify the following email into a category.",
        "input": content,
        "output": classification
    }


def convert_conversational_format(content, classification):
    """
    Conversational format with messages array
    """
    return {
        "messages": [
            {
                "role": "system",
                "content": "You are an email classification assistant."
            },
            {
                "role": "user",
                "content": f"Classify this email: {content}"
            },
            {
                "role": "assistant",
                "content": classification
            }
        ]
    }


def convert_to_jsonl(input_file, output_file, format_type="simple"):
    """
    Convert JSON training data to JSONL format
    """
    # Format conversion function mapping
    format_functions = {
        "simple": convert_simple_format,
        "instruction": convert_instruction_format,
        "conversational": convert_conversational_format
    }
    
    if format_type not in format_functions:
        print(f"Error: Invalid format '{format_type}'. Choose from: simple, instruction, conversational")
        sys.exit(1)
    
    convert_func = format_functions[format_type]
    
    # Load input JSON file
    print(f"Loading training data from: {input_file}")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✓ Loaded {len(data)} entries\n")
    except FileNotFoundError:
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)
    
    # Convert and write to JSONL
    print(f"Converting to JSONL format: {format_type}")
    print(f"Output file: {output_file}")
    print("=" * 50)
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for i, entry in enumerate(data, 1):
                # Validate entry has required fields
                if 'Content' not in entry or 'Classification' not in entry:
                    print(f"Warning: Entry {i} missing required fields, skipping")
                    continue
                
                content = entry['Content']
                classification = entry['Classification']
                
                # Convert to target format
                jsonl_entry = convert_func(content, classification)
                
                # Write as single line JSON
                f.write(json.dumps(jsonl_entry, ensure_ascii=False) + '\n')
                
                # Show progress every 100 entries
                if i % 100 == 0:
                    print(f"Processed {i} entries...")
        
        print("=" * 50)
        print(f"\n✓ Conversion complete!")
        print(f"✓ Wrote {len(data)} entries to {output_file}")
        
        # Show category distribution
        category_counts = {}
        for entry in data:
            cat = entry.get('Classification', 'unknown')
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        print(f"\nCategory distribution:")
        for cat in sorted(category_counts.keys()):
            count = category_counts[cat]
            percentage = (count / len(data) * 100)
            print(f"  {cat}: {count} ({percentage:.1f}%)")
        
        # Show sample of first entry
        print(f"\nSample entry (first line of {output_file}):")
        with open(output_file, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            sample = json.loads(first_line)
            print(json.dumps(sample, indent=2, ensure_ascii=False))
            
    except Exception as e:
        print(f"Error writing output file: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Convert classified email JSON data to JSONL format for MLX-LM LoRA training',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Format options:
  simple         : Simple prompt-completion format (recommended)
                   {"text": "Classify this email:\\n\\nemail body\\n\\nCategory: category"}
  
  instruction    : Instruction format with separate fields
                   {"instruction": "...", "input": "...", "output": "..."}
  
  conversational : Conversational format with messages array
                   {"messages": [{"role": "...", "content": "..."}, ...]}

Examples:
  python convert-to-jsonl.py input.json
  python convert-to-jsonl.py input.json --format instruction
  python convert-to-jsonl.py input.json --output custom-output.jsonl
        """
    )
    
    parser.add_argument(
        'input_file',
        help='Input JSON file with classified emails'
    )
    
    parser.add_argument(
        '--format',
        choices=['simple', 'instruction', 'conversational'],
        default='simple',
        help='Output format type (default: simple)'
    )
    
    parser.add_argument(
        '--output',
        default='training-data.jsonl',
        help='Output JSONL file path (default: training-data.jsonl)'
    )
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not Path(args.input_file).exists():
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)
    
    # Run conversion
    convert_to_jsonl(args.input_file, args.output, args.format)


if __name__ == "__main__":
    main()
