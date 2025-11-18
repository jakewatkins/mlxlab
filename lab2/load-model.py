model_path = "ibm-granite/granite-4.0-1b"

from mlx_lm import load, generate

model, tokenizer = load(model_path)

prompt = "Write a story about Einstein"

messages = [{"role": "user", "content": prompt}]
prompt = tokenizer.apply_chat_template(
    messages, add_generation_prompt=True
)

text = generate(model, tokenizer, prompt=prompt, verbose=True)

print(text)
