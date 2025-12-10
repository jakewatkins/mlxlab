# Training Setup

## Convert Training Data to JSONL

### Purpose
Convert the classified email training data from JSON format to JSONL format required for MLX-LM LoRA fine-tuning.

### Input
- **File**: `/Users/jakewatkins/source/projects/local-ai/training-data/classified-email-data.json`
- **Schema**:
  ```json
  [
    {
      "Content": "email body text",
      "Classification": "category"
    }
  ]
  ```

### Output
- **File**: `training-data.jsonl` (or configurable output name)
- **Format**: One JSON object per line (JSONL)
- **Schema Options** (script should support multiple formats):

#### Option 1: Simple Prompt-Completion (Recommended)
```jsonl
{"text": "Classify this email:\n\nemail body\n\nCategory: category"}
```

#### Option 2: Instruction Format
```jsonl
{"instruction": "Classify the following email into a category.", "input": "email body", "output": "category"}
```

#### Option 3: Conversational Format
```jsonl
{"messages": [{"role": "system", "content": "You are an email classification assistant."}, {"role": "user", "content": "Classify this email: email body"}, {"role": "assistant", "content": "category"}]}
```

### Script Requirements
- Python script that reads the JSON file
- Converts each entry to JSONL format
- Support command-line argument to choose output format (default: simple prompt-completion)
- Write output to JSONL file
- Show progress indicator
- Display summary statistics (total entries converted)
- Error handling with helpful messages

### Usage
```bash
python convert-to-jsonl.py <input.json> [--format simple|instruction|conversational] [--output output.jsonl]
```

### Notes
- The simple prompt-completion format is recommended as it matches the inference pattern
- Each line in JSONL must be a valid JSON object
- No trailing commas between lines
- UTF-8 encoding required

