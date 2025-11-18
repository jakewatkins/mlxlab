from mlx_lm import load, generate

# Load base model and apply LoRA adapters
model, tokenizer = load(
    "./model/llama",  # or your local path to the base model
    adapter_path="./adapters"             # path to your LoRA adapters
)

# Run a test prompt
prompt = "User: What is Tie No when Away Team is 'Millwall'?\nAssistant:"
response = generate(model, tokenizer, prompt=prompt, max_tokens=100)

print(response)