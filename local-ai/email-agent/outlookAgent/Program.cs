using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using EmailAgent.Core;
using EmailAgent.Services;
using EmailAgent.Entities;
using Serilog.Extensions.Logging.File;
using System.Text.Json;

namespace OutlookAgent;

/// <summary>
/// Console application to download all emails from Outlook folders
/// </summary>
class Program
{
    private static ILogger? _logger;
    private const int BATCH_SIZE = 100;
    
    // Define folders to retrieve emails from
    private static readonly List<string> FOLDERS = new List<string>
    {
        "Inbox"
    };

    static async Task<int> Main(string[] args)
    {
        try
        {
            // Setup configuration
            var configuration = new ConfigurationBuilder()
                .AddJsonFile("settings.json")
                .Build();

            // Setup logging
            var logPath = configuration["Logging:File:Path"] ?? "outlookAgent.log";
            using var loggerFactory = LoggerFactory.Create(builder =>
            {
                builder.AddConsole();
                builder.SetMinimumLevel(LogLevel.Information);
            });
            
            // Add file logging
            loggerFactory.AddFile(logPath);
            
            _logger = loggerFactory.CreateLogger<Program>();
            _logger.LogInformation("OutlookAgent started");

            // Initialize agent configuration
            var agentConfig = new AgentConfiguration(configuration);
            _logger.LogInformation("AgentConfiguration initialized successfully");

            // Initialize Outlook service
            var outlookService = new OutlookService(agentConfig, _logger);
            _logger.LogInformation("OutlookService initialized successfully");

            // Retrieve all emails from all folders
            int totalEmailsRetrieved = 0;
            foreach (var folderName in FOLDERS)
            {
                _logger.LogInformation("Processing folder: {FolderName}", folderName);
                Console.WriteLine($"\n=== Processing folder: {folderName} ===");
                
                var emails = await RetrieveEmailsFromFolder(outlookService, folderName);
                
                if (emails.Count > 0)
                {
                    SaveEmailsToJson(emails, folderName);
                    totalEmailsRetrieved += emails.Count;
                    _logger.LogInformation("Saved {EmailCount} emails from {FolderName}", emails.Count, folderName);
                    Console.WriteLine($"Saved {emails.Count} emails from {folderName} to {GetOutputFileName(folderName)}");
                }
                else
                {
                    _logger.LogInformation("No emails found in {FolderName}", folderName);
                    Console.WriteLine($"No emails found in {folderName}");
                }
            }

            _logger.LogInformation("OutlookAgent completed successfully. Total emails retrieved: {EmailCount}", totalEmailsRetrieved);
            Console.WriteLine($"\nSuccessfully retrieved {totalEmailsRetrieved} emails from {FOLDERS.Count} folders");
            
            return 0;
        }
        catch (Exception ex)
        {
            var errorMessage = $"An error occurred in OutlookAgent: {ex.Message}";
            
            if (_logger != null)
            {
                _logger.LogError(ex, "Fatal error in OutlookAgent");
            }
            
            Console.WriteLine($"ERROR: {errorMessage}");
            Console.WriteLine($"Location: {ex.TargetSite?.Name ?? "Unknown"}");
            
            return 1;
        }
    }

    /// <summary>
    /// Gets the output filename for a given folder
    /// </summary>
    private static string GetOutputFileName(string folderName)
    {
        return $"{folderName}.json";
    }

    private static FolderType GetFolderType(string folderName)
    {
        return folderName.ToLower() switch
        {
            "inbox" => FolderType.Inbox,
            "junk email" => FolderType.Spam,
            _ => FolderType.Custom
        };
    }

    /// <summary>
    /// Retrieves all emails from a specific Outlook folder by paginating through batches
    /// </summary>
    private static async Task<List<Email>> RetrieveEmailsFromFolder(OutlookService outlookService, string folderName)
    {
        var retrievedEmails = new List<Email>();
        int startIndex = 0;
        bool hasMoreEmails = true;

        while (hasMoreEmails)
        {
            _logger?.LogInformation("Retrieving emails from {FolderName} starting at index {StartIndex}, batch size {BatchSize}", 
                folderName, startIndex, BATCH_SIZE);
            Console.WriteLine($"  Fetching emails {startIndex} to {startIndex + BATCH_SIZE - 1}...");



            var folder = new EmailAgent.Entities.EmailFolder(
                folderName,
                GetFolderType(folderName),
                EmailService.Outlook,
                folderName  // Service-specific folder name
            );

            // Create email request with folder specification
            var request = new GetEmailRequest
            {
                StartIndex = startIndex,
                NumberOfEmails = BATCH_SIZE,
                Folder = folder
            };

            // Retrieve emails
            var response = await outlookService.GetEmail(request);

            if (!response.Success)
            {
                throw new Exception($"Failed to retrieve emails from {folderName} at index {startIndex}: {response.Message}");
            }

            if (response.Emails == null || response.Emails.Count == 0)
            {
                _logger?.LogInformation("No more emails to retrieve from {FolderName}", folderName);
                hasMoreEmails = false;
                break;
            }

            // Add retrieved emails to our collection
            retrievedEmails.AddRange(response.Emails);
            _logger?.LogInformation("Retrieved {EmailCount} emails from {FolderName} in this batch. Total so far: {TotalCount}", 
                response.Emails.Count, folderName, retrievedEmails.Count);

            // Check if we've retrieved all emails (fewer than requested means we're done)
            if (response.Emails.Count < BATCH_SIZE)
            {
                _logger?.LogInformation("Retrieved fewer emails than requested ({Count} < {BatchSize}) from {FolderName}, all emails fetched", 
                    response.Emails.Count, BATCH_SIZE, folderName);
                hasMoreEmails = false;
            }
            else
            {
                startIndex += BATCH_SIZE;
            }
        }
        
        return retrievedEmails;
    }

    /// <summary>
    /// Saves the retrieved emails to a JSON file with only the required fields
    /// </summary>
    private static void SaveEmailsToJson(List<Email> emails, string folderName)
    {
        var outputFile = GetOutputFileName(folderName);
        _logger?.LogInformation("Saving {EmailCount} emails from {FolderName} to {OutputFile}", emails.Count, folderName, outputFile);

        // Create simplified email objects with only required fields
        var emailsToSave = emails.Select(email => new
        {
            Id = email.Id,
            Service = EmailService.Outlook.ToString(),
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
