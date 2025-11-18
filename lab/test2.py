from mlx_lm import load, generate

model, tokenizer = load(
    "./model/llama",  # or your local path to the base model
    adapter_path="./adapters"             # path to your LoRA adapters
)
prompt = "hello"

if tokenizer.chat_template is not None:
    messages = [{"role": "user", "content": prompt}]
    prompt = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True
    )

response = generate(model, tokenizer, prompt=prompt, verbose=True)