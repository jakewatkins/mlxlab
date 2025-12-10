#!/usr/bin/env python3
"""
Setup Training Data Script
Splits classified email JSON data into train/validation/test sets in JSONL format
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
import random


def load_classified_data(input_file):
    """Load the classified email data from JSON file"""
    print(f"Loading data from: {input_file}")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✓ Loaded {len(data)} emails\n")
        return data
    except FileNotFoundError:
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)


def validate_data(data):
    """Validate that all entries have required fields"""
    for i, entry in enumerate(data, 1):
        if 'Content' not in entry:
            print(f"Error: Entry {i} missing 'Content' field")
            sys.exit(1)
        if 'Classification' not in entry:
            print(f"Error: Entry {i} missing 'Classification' field")
            sys.exit(1)
    print("✓ All entries have required fields\n")


def group_by_category(data):
    """Group emails by classification category"""
    category_groups = defaultdict(list)
    for entry in data:
        category = entry['Classification']
        category_groups[category].append(entry)
    return category_groups


def check_low_sample_categories(category_groups, min_samples=10):
    """Identify and warn about categories with low sample counts"""
    low_sample_categories = []
    
    print("Category distribution:")
    print("=" * 50)
    for category in sorted(category_groups.keys()):
        count = len(category_groups[category])
        if count < min_samples:
            low_sample_categories.append(category)
            print(f"  {category}: {count} samples ⚠️  (LOW - will only be in training set)")
        else:
            print(f"  {category}: {count} samples")
    
    print("=" * 50)
    
    if low_sample_categories:
        print(f"\n⚠️  Warning: {len(low_sample_categories)} categories have < {min_samples} samples")
        print("These will only appear in the training set to ensure sufficient data.\n")
    
    return low_sample_categories


def stratified_split(category_groups, low_sample_categories, train_ratio=0.8, val_ratio=0.1, test_ratio=0.1, seed=42):
    """
    Perform stratified split maintaining category distribution
    Low-sample categories go entirely to training set
    """
    random.seed(seed)
    
    train_data = []
    val_data = []
    test_data = []
    
    for category, emails in category_groups.items():
        # Shuffle the emails for this category
        shuffled_emails = emails.copy()
        random.shuffle(shuffled_emails)
        
        if category in low_sample_categories:
            # All low-sample category emails go to training
            train_data.extend(shuffled_emails)
        else:
            # Calculate split indices
            n = len(shuffled_emails)
            train_end = int(n * train_ratio)
            val_end = train_end + int(n * val_ratio)
            
            # Split the data
            train_data.extend(shuffled_emails[:train_end])
            val_data.extend(shuffled_emails[train_end:val_end])
            test_data.extend(shuffled_emails[val_end:])
    
    # Shuffle the final sets
    random.shuffle(train_data)
    random.shuffle(val_data)
    random.shuffle(test_data)
    
    return train_data, val_data, test_data


def convert_to_training_format(content, classification):
    """
    Convert to simple training format:
    {"text": "Classify this email:\n\nemail body\n\nCategory: category"}
    """
    text = f"Classify this email:\n\n{content}\n\nCategory: {classification}"
    return {"text": text}


def write_jsonl(data, output_file):
    """Write data to JSONL file"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for entry in data:
                # Convert to training format
                training_entry = convert_to_training_format(
                    entry['Content'],
                    entry['Classification']
                )
                f.write(json.dumps(training_entry, ensure_ascii=False) + '\n')
        print(f"  ✓ Wrote {len(data)} entries to {output_file.name}")
    except Exception as e:
        print(f"Error writing {output_file}: {e}")
        sys.exit(1)


def print_split_summary(train_data, val_data, test_data, category_groups):
    """Print summary statistics of the split"""
    total = len(train_data) + len(val_data) + len(test_data)
    
    print("\nSplit Summary:")
    print("=" * 50)
    print(f"Training:   {len(train_data):5d} ({len(train_data)/total*100:.1f}%)")
    print(f"Validation: {len(val_data):5d} ({len(val_data)/total*100:.1f}%)")
    print(f"Testing:    {len(test_data):5d} ({len(test_data)/total*100:.1f}%)")
    print(f"Total:      {total:5d}")
    print("=" * 50)
    
    # Category representation in each split
    print("\nCategory representation in validation set:")
    val_categories = set(entry['Classification'] for entry in val_data)
    test_categories = set(entry['Classification'] for entry in test_data)
    all_categories = set(category_groups.keys())
    
    missing_val = all_categories - val_categories
    missing_test = all_categories - test_categories
    
    if missing_val:
        print(f"  ⚠️  {len(missing_val)} categories not in validation: {', '.join(sorted(missing_val))}")
    else:
        print(f"  ✓ All {len(all_categories)} categories represented")
    
    print("\nCategory representation in test set:")
    if missing_test:
        print(f"  ⚠️  {len(missing_test)} categories not in test: {', '.join(sorted(missing_test))}")
    else:
        print(f"  ✓ All {len(all_categories)} categories represented")
    
    print()


def main():
    # Configuration
    input_file = Path("/Users/jakewatkins/source/projects/local-ai/training-data/classified-email-data.json")
    output_dir = Path("/Users/jakewatkins/source/projects/local-ai/training-data")
    
    train_ratio = 0.8
    val_ratio = 0.1
    test_ratio = 0.1
    min_samples = 10
    seed = 42
    
    print("Setup Training Data")
    print("=" * 50)
    print(f"Input:  {input_file}")
    print(f"Output: {output_dir}")
    print(f"Split:  {int(train_ratio*100)}/{int(val_ratio*100)}/{int(test_ratio*100)} (train/val/test)")
    print(f"Seed:   {seed}")
    print("=" * 50)
    print()
    
    # Check if input file exists
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)
    
    # Check if output directory exists
    if not output_dir.exists():
        print(f"Error: Output directory does not exist: {output_dir}")
        print("Please create the directory first.")
        sys.exit(1)
    
    # Load and validate data
    data = load_classified_data(input_file)
    validate_data(data)
    
    # Group by category
    category_groups = group_by_category(data)
    
    # Check for low-sample categories
    low_sample_categories = check_low_sample_categories(category_groups, min_samples)
    
    # Perform stratified split
    print("\nPerforming stratified split...")
    train_data, val_data, test_data = stratified_split(
        category_groups,
        low_sample_categories,
        train_ratio,
        val_ratio,
        test_ratio,
        seed
    )
    
    # Generate output filenames
    base_name = input_file.stem  # 'classified-email-data'
    train_file = output_dir / f"{base_name}-training.jsonl"
    val_file = output_dir / f"{base_name}-validation.jsonl"
    test_file = output_dir / f"{base_name}-testing.jsonl"
    
    # Write output files
    print("\nWriting output files...")
    write_jsonl(train_data, train_file)
    write_jsonl(val_data, val_file)
    write_jsonl(test_data, test_file)
    
    # Print summary
    print_split_summary(train_data, val_data, test_data, category_groups)
    
    print("✓ Training data setup complete!\n")


if __name__ == "__main__":
    main()
