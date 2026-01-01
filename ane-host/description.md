# ANE Host - Swift Core ML Wrapper Library 

You are designing a Swift library that exposes a clean, C‑compatible API for .NET applications to load, run, and manage Core ML models on Apple Silicon. The library must support text‑generation models, prompt‑based inference, and a tool‑calling mechanism.
Primary Goals
1. Load or create Core ML models (.mlmodel or .mlmodelc).
2. Run text‑generation prompts through the model.
3. Allow the .NET host to pass in a list of tools (name + description + schema).
4. Allow the model to request tool calls via structured output.
5. Return generated text or tool‑call requests back to .NET.
6. Expose a stable C API so .NET can call into the Swift library via P/Invoke.

## High‑Level Architecture
Design a Swift module with three layers:
1. CoreMLModelManager
• Loads and compiles Core ML models.
• Manages model lifecycle.
• Handles compute unit selection (CPU/GPU/ANE).
• Supports prewarming and caching.
2. TextGenerationEngine
• Accepts a prompt string.
• Runs inference using the Core ML model.
• Streams or returns generated tokens.
• Detects tool‑call patterns in model output (e.g., JSON or special tokens).
• Returns:
	◦ GeneratedText
	◦ or ToolCallRequest
3. C‑Compatible Interop Layer
Expose a minimal C API:
    void* CreateModel(const char* modelPath);
    void FreeModel(void* handle);

    void SetTools(void* handle, const char* toolsJson);

    char* RunPrompt(void* handle, const char* promptJson);
    void FreeString(char* str);

Where:
• toolsJson is a JSON array describing available tools.
• promptJson contains the user prompt and optional conversation history.
• RunPrompt returns a JSON object containing either:
	◦ "response": "text..."
	◦ or "tool_call": { name, arguments }

Tool Calling Requirements
The library must support a tool‑calling workflow:
Input from .NET
A JSON array of tools:
    [
        {
            "name": "search_web",
            "description": "Search the internet for information.",
            "schema": {
            "type": "object",
            "properties": {
                "query": { "type": "string" }
            },
            "required": ["query"]
            }
        }
    ]

Output from Swift
If the model requests a tool call, return:
    {
        "tool_call": {
            "name": "search_web",
            "arguments": { "query": "apple silicon neural engine" }
        }
    }

If the model produces normal text, return:
    {
    "response": "Here is the answer..."
    }

## Model Execution Requirements
• Use Core ML’s text generation APIs when available.
• For custom models, implement tokenization + decoding in Swift.
• Support:
	◦ greedy decoding
	◦ top‑k
	◦ top‑p
	◦ temperature
• Allow streaming (optional future extension).

## Streaming Support Requirements

The library must support real-time streaming of generated tokens to enable responsive user experiences:

### Core Streaming Features
• **Token-by-token streaming**: Return individual tokens as they're generated rather than waiting for complete response
• **Streaming C API**: Extend the C interface to support streaming callbacks:
    ```c
    typedef void (*StreamCallback)(void* context, const char* token, int isComplete);
    int StartStreamingPrompt(void* handle, const char* promptJson, StreamCallback callback, void* context);
    void StopStreaming(void* handle);
    ```

### Streaming Behavior
• **Incremental delivery**: Each callback should deliver the next generated token
• **Completion signaling**: Final callback must indicate stream completion (`isComplete = 1`)
• **Tool call detection during streaming**: Monitor output for tool call patterns and interrupt streaming when detected
• **Error handling**: Stream errors through callback with special error tokens

### Stream Management
• **Cancellation**: Support mid-stream cancellation via `StopStreaming`
• **Buffering**: Implement configurable token buffering to reduce callback frequency
• **Thread safety**: Ensure callbacks can be safely invoked from background threads
• **Resource cleanup**: Automatic cleanup if streaming is interrupted or cancelled

### Integration with Tool Calling
• **Pattern detection**: Monitor streaming output for tool call JSON patterns
• **Early termination**: Stop streaming and return structured tool call when pattern is complete
• **Partial detection**: Handle incomplete tool calls at stream boundaries
• **Fallback behavior**: If tool call pattern is malformed, continue streaming as regular text

### Performance Considerations
• **Callback overhead**: Minimize latency between token generation and callback invocation
• **Memory efficiency**: Avoid accumulating full response in memory during streaming
• **ANE optimization**: Leverage Apple Neural Engine batch processing while maintaining streaming responsiveness

## Model text generation validation
1. It has an input named "input_ids" or "prompt"
2. It has an output named "logits" or "generated_tokens"
3. The logits output is a 3‑dimensional MLMultiArray
4. Optional: tokenizer metadata exists
### Swift pseudo‑implementation
    func modelSupportsTextGeneration(_ model: MLModel) -> Bool {
        let spec = model.modelDescription
        
        let inputs = spec.inputDescriptionsByName
        let outputs = spec.outputDescriptionsByName
        
        // 1. Check for common text-gen input names
        let inputNames = inputs.keys
        let hasTextInput = inputNames.contains("input_ids") ||
                        inputNames.contains("prompt")
        
        // 2. Check for common text-gen output names
        let outputNames = outputs.keys
        let hasTextOutput = outputNames.contains("logits") ||
                            outputNames.contains("generated_tokens")
        
        // 3. Check logits shape
        if let logits = outputs["logits"],
        logits.type == .multiArray,
        let shape = logits.multiArrayConstraint?.shape,
        shape.count == 3 {
            return true
        }
        
        // 4. Fallback heuristic
        return hasTextInput && hasTextOutput
    }

## ANE Fallback behavior

Apple's Core ML automatically handles routing models to be run either on ANE, GPU or CPU.
If ANE is unavailable for any reason, Core ML will automatically fall back to GPU or CPU.
The library should allow the host to specify compute unit preference:
    - aneOnly
    - anePreferred
    - gpuPreferred
    - cpuOnly
In swift, this would map to:
    modelConfig.computeUnits = .all // ANE + GPU + CPU
    modelConfig.computeUnits = .cpuOnly
    modelConfig.computeUnits = .cpuAndGPU
    modelConfig.computeUnits = .cpuAndNeuralEngine
this way the .net host will be able to choose how the model will run.

## Text Generation API Requirements
The library must support two Core ML text‑generation execution paths and automatically select the most capable option based on the loaded model:
1. ML Program–Based Autoregressive Generation (Preferred Path)
	◦ If the loaded model is an MLProgram model that supports incremental state updates, the library must use Core ML’s optimized autoregressive execution pattern.
	◦ This includes:
		▪︎ feeding token sequences
		▪︎ retrieving logits
		▪︎ sampling next tokens
		▪︎ updating model state efficiently
	◦ This path provides the highest performance and should be used whenever the model supports it.
2. Classic Core ML Prediction Loop (Fallback Path)
	◦ If the model does not support MLProgram‑based generation, the library must fall back to the standard Core ML prediction API.
	◦ This includes:
		▪︎ constructing MLMultiArray inputs
		▪︎ calling model.prediction(...)
		▪︎ reading logits from the output
		▪︎ performing token sampling in Swift
	◦ This path must work for all Core ML models converted from Hugging Face or MLX.
The library must automatically detect which generation path is supported by inspecting the model’s description, inputs, outputs, and metadata.

## ---
Tokenizer Capability Detection Requirements
The library must automatically determine whether a loaded Core ML model provides sufficient tokenizer information for built‑in tokenization, or whether the hosting .NET application must supply an external tokenizer. Detection must follow these rules:
1. Tokenizer Metadata Inspection
	◦ The library must inspect model.modelDescription.metadata[.creatorDefinedKey] for tokenizer‑related fields.
	◦ If any of the following keys are present, the model is considered to have built‑in tokenizer metadata:
		▪︎ "tokenizer_class"
		▪︎ "tokenizer_type"
		▪︎ "tokenizer_json"
		▪︎ "vocab"
		▪︎ "merges"
		▪︎ "vocab_size"
		▪︎ "eos_token_id", "bos_token_id", "pad_token_id"
	◦ Presence of any of these keys indicates that the wrapper can perform tokenization internally.
2. Tokenizer File Detection
	◦ The library must inspect the compiled model directory (.mlmodelc) for tokenizer files.
	◦ If any of the following files exist, the model is considered to include a built‑in tokenizer:
		▪︎ tokenizer.json
		▪︎ vocab.json
		▪︎ merges.txt
		▪︎ special_tokens_map.json
3. String‑Based Model Interfaces
	◦ If any model input is of type .string, the model must be treated as having built‑in tokenization, since it expects raw text rather than token IDs.
4. Token‑ID‑Based Interfaces (External Tokenizer Required)
	◦ If the model expects tokenized inputs (e.g., "input_ids", "attention_mask", "token_ids"), and no tokenizer metadata or tokenizer files are present, the library must classify the model as requiring an external tokenizer.
	◦ In this case, the .NET host must provide tokenization and detokenization functions.
5. Capability Reporting
	◦ After loading a model, the library must return a JSON capability descriptor to the .NET host indicating:
		▪︎ "has_builtin_tokenizer": true | false
		▪︎ "reason": a short explanation (e.g., "metadata_present", "tokenizer_files_found", "string_input", "token_ids_required")
The library must not attempt text generation until tokenizer capability has been determined and either the built‑in tokenizer is available or an external tokenizer has been supplied by the .NET host.

## Context Window, Token Limits, and Truncation Requirements
The library must enforce model‑specific token limits and manage context windows in a predictable, deterministic manner. The following rules define how token limits, context handling, and truncation must operate:
1. Model Token Limit Detection
- After loading a model, the library must determine the maximum supported sequence length (“context window”).
- The context window must be detected using one or more of the following:
    - metadata fields such as "max_position_embeddings"
    - "sequence_length" or "max_length" in creator‑defined metadata
    - input tensor shape constraints (e.g., input_ids shape [1, N])
- The detected limit must be returned to the .NET host in the model capability descriptor:
    {
        "max_context_tokens": 4096
    }
2. Input Token Length Validation
• Before running inference, the library must validate that the combined tokenized input (prompt + conversation history + system instructions + tool descriptions) does not exceed the model’s maximum context window.
• If the input exceeds the limit, the library must apply truncation according to the rules below.
3. Truncation Behavior
The library must support two truncation modes, selectable by the .NET host:
a. Front‑Truncation (default)
• Remove tokens from the oldest part of the conversation history first.
• Preserve:
	◦ system prompt
	◦ tool descriptions
	◦ the most recent user and assistant turns
• This mode prioritizes recency and is suitable for chat applications.
b. Hard‑Error Mode
- If truncation is disabled and the input exceeds the model’s limit, the library must return an error:
    {
    "error": "input_too_long",
    "max_context_tokens": 4096,
    "input_tokens": 5120
    }
4. Tool Description Token Accounting
• Tool descriptions must be included in the token count.
• If tool descriptions alone exceed the model’s context window, the library must return an error indicating that the model cannot support the provided tool set.
5. Output Token Limits
- The .NET host may specify a maximum number of output tokens.
- The library must enforce this limit during generation.
- If the model reaches the output limit, the library must return:
    {
    "response": "...",
    "truncated": true
    }
6. Streaming Compatibility (Future Extension)
• The truncation and context‑window rules must be compatible with both:
	◦ full‑response generation
	◦ token‑streaming generation (if implemented later)
7. Capability Reporting
   After loading a model, the library must report:
    {
        "max_context_tokens": 4096,
        "supports_truncation": true,
        "default_truncation_mode": "front",
        "supports_output_token_limit": true
    }

## Tool Call Detection Requirements
The library must detect tool‑call requests in model output using a structured, JSON‑based protocol. The following rules define how tool‑call detection must operate:
1. Prompt-side enforcement
    - Before running inference, the library must inject a system‑level instruction that requires the model to output tool calls in a strict JSON format.
    - Tool‑call responses must follow this structure:
    {
        "tool_call": {
            "name": "<tool_name>",
            "arguments": { ... }
        }
    }
    - Normal assistant responses must follow this structure:
    {
        "response": "<assistant text>"
    }
    - The model must be instructed not to include any text outside of the JSON object.
2. JSON Extraction
    - After generation, the library must extract the first valid JSON object from the model’s output
    - Extraction must tolerate whitespace, newlines, and minor formatting inconsistencies.
    - If multiple JSON objects appear, only the first complete object must be used.
3. Tool Call Identification
    - If the extracted JSON contains a "tool_call" key, the library must classify the output as a tool‑call request and return the JSON object unchanged to the .NET host.
    - If the JSON contains a "response" key, the library must classify the output as normal assistant text.
4. Malformed Output Handling
    - If the model produces invalid or incomplete JSON, the library must attempt minimal, safe repairs (e.g., trimming trailing commas, removing unmatched braces).
    - If repair is not possible, the library must treat the entire output as normal assistant text and return it in the "response" field.
5. Safety and Determinism
    - The library must never execute tools directly.
    - The .NET host is solely responsible for executing tool calls and returning results to the model.
    - The library must not infer tool calls from unstructured text; only valid JSON with a "tool_call" key qualifies.
6. The library must enforce a strict rule that each model response may contain at most one tool‑call request. The following rules define how the library must handle cases where multiple tool calls appear in a single model output:
    - Single Tool Call Contract
        - The model must be instructed (via system prompt injection) to produce at most one tool call per response.
        - The required output format must only contain one "tool_call" object.
    - Multiple Tool Calls Detected
        - If the model output contains more than one "tool_call" object, the library must:
            - extract the first valid tool‑call JSON object
            - ignore all subsequent tool‑call objects
            - return a warning to the .NET host in the response metadata
            - Example warning:
                {
                    "warning": "multiple_tool_calls_detected",
                    "handled": "first_only"
                }
    - Malformed or Nested Tool Calls
        - If the model produces nested tool‑call structures or invalid JSON containing multiple tool‑call patterns, the library must attempt minimal safe repair.
        - If repair is not possible, the library must treat the entire output as normal assistant text.
    - No Parallel or Batch Tool Execution
        - The library must not attempt to execute multiple tools in parallel or sequence
        - Only the .NET host may execute tools, and only one tool call may be returned per model turn.




## Error Handling
All C API functions must return:
• nullptr on failure
• or a JSON error object:
    {
        "error": "Model failed to load",
        "details": "File not found"
    }

## Memory Management
• All strings returned to .NET must be heap‑allocated.
• .NET will call FreeString to release memory.
• Model handles must be freed via FreeModel.

## Deliverables
Generate:
1. Swift source code for the library.
2. The C‑compatible header file.
3. A description of the internal architecture.
4. Example .NET P/Invoke bindings.
5. Example usage from .NET.

## Clarifications
 - Compute unit select - the hosting application will pass a value indicating how it wants the model to execute
 - concurrent request handling - requests will not be concurrent.  they will be serialized one at a time.
 - thread safety - these should be thread-safe operations, but we do not plan to perform concurrent operations.
 - platform support - this library and the host application will ONLY run on Apple Silicon running on MacOS 14+
