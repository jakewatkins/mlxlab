# 
# model - meta-llama/Llama-3.2-3B-Instruct
# model - mistralai/Mistral-7B-Instruct-v0.2
python -m mlx_lm convert \
  --hf-path meta-llama/Llama-3.2-3B-Instruct \
  --mlx-path ./model/llama \
  --q-bits 4 \
  --q-group-size 64
