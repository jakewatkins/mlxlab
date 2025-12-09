# LLM Server

LLM-Server is an LLM host that listens for HTTP POST requests on a configured port.  The incoming request is processed by the LLM and the results are returned to the client.  LLM-Server is a python application that uses Apple's MLX framework to integrate LLMs.  It will use the mcp-host libary to integrate MCP servers to provide tools to the LLMs.  LLM-Server like llm-host will have tool support through mcp integration.
LLM-Server will use config.json to configure itself upon startup.  The config file will provide the following settings:
    - model name
        - this will a Hugging Face model name
    - listening port
    - list of MCP servers
        - will have the same schema as mcp.json used in other tools:
            "servers": {
                "filesystem": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem@latest", "/Users/jakewatkins/source/trashcode/local-llm/mlx-lab/chat-mcp/"]
                },
                "brave-search": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "brave-search-mcp"],
                    "env": {
                        "BRAVE_API_KEY": "${BRAVE_API_KEY}"
                    }
                }
            }
    - system prompt
    - temperature
    - top_p
    - min_p
    - min_tokens_to_keep
    - log level
    - log filename
        - this will be the fullpath to the log file

LLM-Server will maintain a log file to help with debugging.  It will log incoming requests, responses, errors and information written to stderr.

If an unrecoverable error occurs LLM-Server will write whatever information it can to the log file and exit

# request format
- only accepts POST
- the incoming message body will be in json with this schema:
    {
        "prompt" : "what is the temperature in Dallas, TX"
    }
- if validation of the incoming request fails return an HTTP 400 with {"Error": "error message"} as the payload
# response format
- the response will be in json format:
    {
        "response" : "It is really blasted cold!"
    }
- successful requests will have the standard HTTP 200 response code
- If an error occurs a standard HTTP 500 and the body of the response will be a JSON message with the error message:
    {
        "Error" : "error message"
    }

# Model loading
- the model will be loaded before LLM-Server starts to listen on the port
- MCP servers will also be started before listening on the port
- The MLX framework handles loading and caching models
- No idea where MLX caches downloaded models.  I don't think it is configurable.
- No limit on model size or memory limits, we assume the user knows what they're doing
- if the model fails to load, log the failure and exit
- the server does not need to reload the model.  The user will restart the service if needed.

# MCP Integration
- the server will load all of the servers listed in config.json
- if an MCP server is not available, log the unavailability and continue
- the MCP servers will be loaded on startup
- if an MCP server crashes or becomes unavailable during a request - log an error and continue processing requests and let the llm continue to work with the remaining tools.


# Configuration
- All configuration values are required.  The "servers" property can be empty.
- if "listening port" is missing log an error and exit
- if "log filename" is missing print an error and exit
- the config.json file will be in current working directory when the server is launched
- Secrets in config.json will be substitued with either environment variables or .env files in the current working directory (same directory as config.json)
    - if a config values is ${BRAVE_API_KEY} the program will first check for an environment variable, if that isnt available then see if the value is in a .env file. If there is no .env file and no environment variable: log an error and exit.

# Concurrency & state
- the server will be able to handle multiple simultaneous requests
- there is not conversation state/history.  It is stateless

# Logging
- the config file will set the log level (trace, warning, error)
- Logs will be rotated daily.
- the log file name when rotatd will have the data appended to the end.  Use the format of -YYYYMMdd
- just keep log files indefinately.

# Unrecoverable errors
- Unrecoverable errors are things like bad model name, missing configuration values, unable to start listening on a port.

# startup & lifecycle
- startup sequence:
    - setup the MCP Host and servers
    - load the LLM
    - start listening for requests
- no healthcheck endpoint for now
- there should be a graceful shutdown
    - unload the model
    - shutdown the mcp servers
- handle SIGTERM to start the shutdown process
- if SIGTERM is received while requests are being processed:
    - stop accepting new requests
    - wait for the inflight requests to complete and then shutdown

# Security & validation
- no authentication or authorization for requests
- no rate limiting
- validate that the incoming request is in json and has a field called "prompt"
- requests should be less than 10mb in size

# Dependencies
- the mcp-host library can be found here: /Users/jakewatkins/source/projects/mlx-lab/mcp-host
- the package info can be found here: /Users/jakewatkins/source/projects/mlx-lab/mcp-host/mcp_host.egg-info
- you can see usage example here: /Users/jakewatkins/source/projects/mlx-lab/mcp-host/examples/simple_host.py

