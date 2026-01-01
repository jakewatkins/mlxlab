# Gmail agent

This tool will download all email from my Gmail account and store the emails in a json file called gmail-email.json.

- the application will be written in C# using the .net framework
- it will use EmailAgent.emailServices nuget library to connect to Gmail

# GmailService 
- Use the EmailAgent.emailServices library's GmailService to retrieve email from Gmail
- try to retrieve 100 emails with each request and keep looping until there are no more emails returned.
- we're only retrieving email from the inbox, no subfolders. 
- The source code for the emailServices can be found here: /Users/jakewatkins/source/projects/Share/emailAgent/emailServices

# Error handling
- if an error occurs, print a helpful error message indacating where the error occured and exit the application with an error code.
- if possible save any partial work before exiting.

# Configuration
- use EmailAgent.Core 
- the config file (settings.json) will contain the initial configuration
- use Microsoft.Extension.Configuration to load the configuration file
- the class AgentConfiguration handles loading the configuration information

# Output schema
- Use the EmailEntity structure
- these are the fields that will be save for each email:
    - Id
    - Service
    - SentDateTime
    - From
    - To
    - Subject
    - Body
- we don't need to store attachments
- The Service property will be hardcoded to "Gmail"
- the output will be a json array of email objects

# Existing vs. New Emails
- the service will simply fetch ALL email in the account
- a separate tool will be created to clear out the accout, but it will be created later.

# Authentication
- use Google's web authorization broker
- AgentConfiguration has google client id and google secret

# Project type
- console application

# Attachments
- Skip attachments entirely

# Partial Work
- save the emails retrieved at the point the error occurs.

# Spam/Junk emails
- skip spam/junk email entirely. 
- only retrieve email in the inbox.

# CC and BCC fields
- skip these fields.

# SentDateTime
- oops, I missed that field.  I've added it to the schema.

# Error Exit Code
- just return the standard exit code that indicates an error.

# Pagination Logic
- check the number of emails returned.  If it is less than the number requested, then we've fetched all of the emails.

# Configuration Value
- I fixed it manually.

# Logging
- Use Microsoft.Extensions.Logging to setup a logger that writes logging to a text file.
- Update settings.json as needed

