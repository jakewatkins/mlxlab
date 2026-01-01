using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using EmailAgent.Core;
using EmailAgent.Services;
using EmailAgent.Entities;
using Serilog.Extensions.Logging.File;
using System.Text.Json;

namespace GmailAgent;

/// <summary>
/// Console application to download all emails from Gmail inbox
/// </summary>
class Program
{
    private static ILogger? _logger;
    private static IConfiguration? _configuration;
    private static ILoggerFactory? _loggerFactory;
    private const int START_INDEX = 190001; // Start from 190,001 to skip previously retrieved emails
    private const int BATCH_SIZE = 500;
    private const int SAVE_BATCH_SIZE = 10000;
    private const int RETRY_DELAY_SECONDS = 5;
    
    static async Task<int> Main(string[] args)
    {
        try
        {
            // Setup configuration
            _configuration = new ConfigurationBuilder()
                .AddJsonFile("settings.json")
                .Build();

            // Setup logging
            var logPath = _configuration["Logging:File:Path"] ?? "gmailAgent.log";
            _loggerFactory = LoggerFactory.Create(builder =>
            {
                builder.AddConsole();
                builder.SetMinimumLevel(LogLevel.Information);
            });
            
            // Add file logging
            _loggerFactory.AddFile(logPath);
            
            _logger = _loggerFactory.CreateLogger<Program>();
            _logger.LogInformation("GmailAgent started");

            // Initialize agent configuration
            var agentConfig = new AgentConfiguration(_configuration);
            _logger.LogInformation("AgentConfiguration initialized successfully");

            // Retrieve all emails from inbox
            _logger.LogInformation("Processing Gmail Inbox");
            Console.WriteLine("\n=== Processing Gmail Inbox ===");
            
            int totalEmailsRetrieved = await RetrieveEmailsFromInbox(agentConfig);

            _logger.LogInformation("GmailAgent completed successfully. Total emails retrieved: {EmailCount}", totalEmailsRetrieved);
            Console.WriteLine($"\nSuccessfully retrieved {totalEmailsRetrieved} emails from Gmail inbox");
            
            _loggerFactory?.Dispose();
            
            return 0;
        }
        catch (Exception ex)
        {
            var errorMessage = $"An error occurred in GmailAgent: {ex.Message}";
            
            if (_logger != null)
            {
                _logger.LogError(ex, "Fatal error in GmailAgent");
            }
            
            Console.WriteLine($"ERROR: {errorMessage}");
            Console.WriteLine($"Location: {ex.TargetSite?.Name ?? "Unknown"}");
            
            // Save any partial work if we have a logger
            if (_logger != null)
            {
                _logger.LogInformation("Attempting to save partial work before exit");
            }
            
            _loggerFactory?.Dispose();
            
            return 1;
        }
    }

    /// <summary>
    /// Creates a new Gmail service instance
    /// </summary>
    private static GmailService CreateGmailService(AgentConfiguration agentConfig)
    {
        if (_loggerFactory == null)
        {
            throw new InvalidOperationException("Logger factory not initialized");
        }

        var gmailServiceLogger = _loggerFactory.CreateLogger<GmailService>();
        var gmailService = new GmailService(agentConfig, gmailServiceLogger);
        _logger?.LogInformation("GmailService initialized successfully");
        
        return gmailService;
    }

    /// <summary>
    /// Retrieves all emails from Gmail inbox by paginating through batches
    /// Saves emails in chunks of 10,000 to separate files
    /// Handles service exceptions by reconnecting after a delay
    /// </summary>
    private static async Task<int> RetrieveEmailsFromInbox(AgentConfiguration agentConfig)
    {
        var retrievedEmails = new List<Email>();
        int startIndex = START_INDEX; // Start from 80,001 to skip previously retrieved emails
        int totalEmailsRetrieved = 0;
        int fileIndex = 19;
        bool hasMoreEmails = true;
        GmailService? gmailService = null;

        try
        {
            // Initialize Gmail service
            gmailService = CreateGmailService(agentConfig);

            while (hasMoreEmails)
            {
                try
                {
                    _logger?.LogInformation("Retrieving emails from Gmail inbox starting at index {StartIndex}, batch size {BatchSize}", 
                        startIndex, BATCH_SIZE);
                    Console.WriteLine($"  Fetching emails {startIndex} to {startIndex + BATCH_SIZE - 1}...");

                    var folder = new EmailAgent.Entities.EmailFolder(
                        "Inbox",
                        FolderType.Inbox,
                        EmailService.Gmail,
                        "INBOX"  // Gmail's inbox label
                    );

                    // Create email request with folder specification
                    var request = new GetEmailRequest
                    {
                        StartIndex = startIndex,
                        NumberOfEmails = BATCH_SIZE,
                        Folder = folder
                    };

                    // Retrieve emails
                    var response = await gmailService.GetEmail(request);

                    if (!response.Success)
                    {
                        throw new Exception($"Failed to retrieve emails from Gmail inbox at index {startIndex}: {response.Message}");
                    }

                    if (response.Emails == null || response.Emails.Count == 0)
                    {
                        _logger?.LogInformation("No more emails to retrieve from Gmail inbox");
                        hasMoreEmails = false;
                        break;
                    }

                    // Add retrieved emails to our collection
                    retrievedEmails.AddRange(response.Emails);
                    totalEmailsRetrieved += response.Emails.Count;
                    _logger?.LogInformation("Retrieved {EmailCount} emails from Gmail inbox in this batch. Total so far: {TotalCount}", 
                        response.Emails.Count, totalEmailsRetrieved);

                    // Save in batches of 10,000 emails
                    if (retrievedEmails.Count >= SAVE_BATCH_SIZE)
                    {
                        SaveEmailsToJson(retrievedEmails, fileIndex);
                        Console.WriteLine($"Saved {retrievedEmails.Count} emails to gmail-email-{fileIndex}.json");
                        retrievedEmails.Clear();
                        fileIndex++;
                    }

                    // Check if we've retrieved all emails (fewer than requested means we're done)
                    if (response.Emails.Count < BATCH_SIZE)
                    {
                        _logger?.LogInformation("Retrieved fewer emails than requested ({Count} < {BatchSize}) from Gmail inbox, all emails fetched", 
                            response.Emails.Count, BATCH_SIZE);
                        hasMoreEmails = false;
                    }
                    else
                    {
                        startIndex += BATCH_SIZE;
                    }
                }
                catch (Exception ex)
                {
                    _logger?.LogWarning(ex, "Gmail service threw an exception at index {StartIndex}. Closing connection and retrying in {Delay} seconds...", 
                        startIndex, RETRY_DELAY_SECONDS);
                    Console.WriteLine($"  Service error at index {startIndex}: {ex.Message}");
                    Console.WriteLine($"  Waiting {RETRY_DELAY_SECONDS} seconds before reconnecting...");

                    // Dispose the current service
                    if (gmailService is IDisposable disposable)
                    {
                        try
                        {
                            disposable.Dispose();
                        }
                        catch (Exception disposeEx)
                        {
                            _logger?.LogWarning(disposeEx, "Error disposing Gmail service");
                        }
                    }
                    gmailService = null;

                    // Wait before reconnecting
                    await Task.Delay(TimeSpan.FromSeconds(RETRY_DELAY_SECONDS));

                    // Create new service instance
                    _logger?.LogInformation("Reconnecting to Gmail service...");
                    Console.WriteLine("  Reconnecting to Gmail service...");
                    gmailService = CreateGmailService(agentConfig);
                    
                    // Don't increment startIndex - retry the same batch
                    _logger?.LogInformation("Retrying from index {StartIndex}", startIndex);
                }
            }

            // Save any remaining emails
            if (retrievedEmails.Count > 0)
            {
                SaveEmailsToJson(retrievedEmails, fileIndex);
                Console.WriteLine($"Saved {retrievedEmails.Count} emails to gmail-email-{fileIndex}.json");
            }
        }
        catch (Exception ex)
        {
            // Save partial work before re-throwing
            _logger?.LogError(ex, "Fatal error occurred during email retrieval. Saving {Count} emails retrieved so far.", retrievedEmails.Count);
            
            if (retrievedEmails.Count > 0)
            {
                SaveEmailsToJson(retrievedEmails, fileIndex);
                Console.WriteLine($"Saved {retrievedEmails.Count} emails to gmail-email-{fileIndex}.json before error occurred");
            }
            
            throw;
        }
        finally
        {
            // Clean up service
            if (gmailService is IDisposable disposable)
            {
                try
                {
                    disposable.Dispose();
                }
                catch (Exception disposeEx)
                {
                    _logger?.LogWarning(disposeEx, "Error disposing Gmail service in finally block");
                }
            }
        }
        
        return totalEmailsRetrieved;
    }

    /// <summary>
    /// Saves the retrieved emails to a JSON file with only the required fields
    /// </summary>
    private static void SaveEmailsToJson(List<Email> emails, int fileIndex)
    {
        var outputFile = $"gmail-email-{fileIndex}.json";
        _logger?.LogInformation("Saving {EmailCount} emails to {OutputFile}", emails.Count, outputFile);

        // Create simplified email objects with only required fields
        var emailsToSave = emails.Select(email => new
        {
            Id = email.Id,
            Service = EmailService.Gmail.ToString(),
            SentDateTime = email.SentDateTime,
            From = email.From,
            To = email.To,
            Subject = email.Subject,
            Body = email.Body
        }).ToList();

        // Serialize to JSON with formatting
        var jsonOptions = new JsonSerializerOptions
        {
            WriteIndented = true
        };

        var json = JsonSerializer.Serialize(emailsToSave, jsonOptions);
        File.WriteAllText(outputFile, json);

        _logger?.LogInformation("Successfully saved emails to {OutputFile}", outputFile);
    }
}
