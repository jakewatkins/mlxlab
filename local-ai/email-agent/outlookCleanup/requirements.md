# outlook Cleanup

This app will delete all of the email in the configured outlook email account.

- the application will be written in C# using the .net framework
- it will use EmailAgent.emailServices nuget library to connect to outlook.com

# OutlookService 
- ../examples/OutlookServiceExample.cs provides an example of how to use the EmailAgent.emailServices libary to retrieve email.
- try to retrieve 100 emails with each request and keep looping until there are no more emails returned.
- we're only retrieving email from the inbox, no subfolders. 
- The source code for the emailServices can be found here: /Users/jakewatkins/source/projects/Share/emailAgent/emailServices

# Delete email
- after retrieving a group of emails the service will then delete those emails before retrieving the next batch
- the tool will use the DeleteEmail function on the OutlookService.

# Error handling
- if an error occurs, print a helpful error message indacating where the error occured and exit the application with an error code.

# Configuration
- use EmailAgent.Core 
- the config file (settings.json) will contain the initial configuration
- use Microsoft.Extension.Configuration to load the configuration file
    - follow the example demonstrated in ../examples/OutlookServiceExample.cs lines 20 to 22
- the class AgentConfiguration handles loading the configration information
     - follow the example demonstrated in ../examples/OutlookServiceExample.cs lines 32

# Authentication
- interactice authentication is expected at this time.

# Project type
- console application

# Logging
- Use Microsoft.Extensions.Logging to setup a logger that writes logging to a text file.
- Update settings.json as needed

# Clarifications
- no confirmation is needed.
- show a progress indicator "deleted 77/5399"
- the log file will go in the current working directory
- Use a fixed batch size of 100
- exit with a 0 when success completed
- target framework is .NET 8
- is nothing to save, I've removed that requirement