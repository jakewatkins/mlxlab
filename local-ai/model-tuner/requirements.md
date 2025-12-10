# Model tuner

Model Tuner is a python script that uses Apple's MLX framework to perform fine tuning on models using LoRA.  The script will take the following parameters:
    - Model Path
    - data path
    - output path
the model will use a json file for configuration to store other tuning parameters.  the config file will be config.json.  It will have the following parameters:
    - iterations
    - steps per eval
    - value batches
    - learning rate
    - lora layers
The script will validate that the data file exists and then run mlx_lm.lora to perform the training using the provided configuration.
 
# data path
- path to where the training data is stored.  The script will validate that the directory exists and contains 3 jsonl files. 
- the 3 files are expected to have file names that end with the following endings:
    - "-training"
    - "-validation"
    - "-testing"
- if the files do not exist or are not named correctly: print an error message an exit

# error handling
- if an error occurs: print a helpful error message and exit

# output path
- the output directory is expected to exist.  If it does not print an error message and exit

# config file schema
- the config file will be in the same directory as model-tuner.py
- if the config file does not exit: print a helpful error message and exit.
- assume the user knows what they're doning with the values put in config.json
- the config file will have the following json schema:
    {
        "iters" : 699,
        "steps-per-eval" : 100,
        "val-batches" : 25,
        "learning-rate" : 1e-5,
        "lora-layers" : 16
    }

# usage
- example of how the script will be run:
    python model-tuner.py --Model "microsoft/Phi-3-mini-4k-instruct" --data "/Users/jakewatkins/source/projects/local-ai/training-data/email-classification" --output /Users/jakewatkins/source/projects/local-ai/trained-models/email-classifier

# MLX command constructions
- run mlx_lm.lora as a sybprocess command.