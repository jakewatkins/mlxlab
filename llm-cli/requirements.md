# LLM CLI

llm-cli is a command line version of llm-host.  llm-cli lets scripts send a prompt to an llm and either captures the response on stdio or have the response written to a file.
llm-cli is a python application that uses Apple's MLX framework to integrate LLMs.  It will use the mcp-host libary to integrate MCP servers to provide tools to the LLMs.  llm-cli like llm-host will have tool support through mcp integration.
Here are some examples of llm-cli usage:
    llm-cli ibm-granite/granite-4.0-1b -p "what is today's weather forecast" > weather.txt
In this example llm-cli will use the ibm-granite llm to answer the prompt passed in after -p.  the response on stdio will be redirected to a file called weather.txt
another example:
    llm-cli ibm-granite/granite-4.0-1b -p "what is today's weather forecast" -o weather.txt
The only difference in this example is that the response will be directly written to a file called weather.txt.
another example:
    llm-cli ibm-granite/granite-4.0-1b -pf prompt.txt -o news-headlines.txt
In this example the tool will read the entire file prompt.txt and use the contents as the prompt for the llm.
llm-cli will use the same mcp.json file to configure mcp servers.  it will use the mcp-host library to integrate mcp servers.
In general this is the same as llm-host, except that it is not interactive.  If the user does not provide a prompt a usage message will be displayed.  


# tool calling
When a tool calls are detected, llm-cli will automatically execute them and continue until the llm provides its final answer.

# configuration files
llm-cli will use the same config.json and mcp.json as as llm-host.  Both will be expected to be in the current working directory.  
llm-cli will also support the same variable expansion as llm-host does and be able to use .env files to hide secrets.

# output format
The output will just be the assistant's output with not additional markup or formatting

# error handling when writing files
llm-cli will overwrite files if they exist
errors will be written to stderr.
the exit code will indicate success or failure

# streaming
llm-cli will stream tokens as they're generated

# model loading
llm-cli will be using MLX which handles caching models 

# additional options
temperature and other sampling parameters will be configurable through config.json
--max-tokens can be added to the command line to limit the response length
--no-tools will disable the MCP integration