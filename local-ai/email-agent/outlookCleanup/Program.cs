using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using EmailAgent.Core;
using EmailAgent.Services;
using EmailAgent.Entities;
using Serilog.Extensions.Logging.File;

namespace OutlookCleanup;

/// <summary>
/// Console application to delete all emails from Outlook inbox
/// </summary>
class Program
{
    private static ILogger? _logger;
    private const int BATCH_SIZE = 100;

    static async Task<int> Main(string[] args)
    {
        try
        {
            // Setup configuration
            var configuration = new ConfigurationBuilder()
                .AddJsonFile("settings.json")
                .Build();

            // Setup logging
            var logPath = configuration["Logging:File:Path"] ?? "outlookCleanup.log";
            using var loggerFactory = LoggerFactory.Create(builder =>
            {
                builder.AddConsole();
                builder.SetMinimumLevel(LogLevel.Information);
            });
            
            // Add file logging
            loggerFactory.AddFile(logPath);
            
            _logger = loggerFactory.CreateLogger<Program>();
            _logger.LogInformation("OutlookCleanup started");

            // Initialize agent configuration
            var agentConfig = new AgentConfiguration(configuration);
            _logger.LogInformation("AgentConfiguration initialized successfully");

            // Initialize Outlook service
            var outlookService = new OutlookService(agentConfig, _logger);
            _logger.LogInformation("OutlookService initialized successfully");

            // Delete all emails from inbox
            await DeleteAllEmails(outlookService);

            _logger.LogInformation("OutlookCleanup completed successfully");
            Console.WriteLine("All emails have been deleted successfully.");
            
            return 0;
        }
        catch (Exception ex)
        {
            var errorMessage = $"An error occurred in OutlookCleanup: {ex.Message}";
            
            if (_logger != null)
            {
                _logger.LogError(ex, "Fatal error in OutlookCleanup");
            }
            
            Console.WriteLine($"ERROR: {errorMessage}");
            Console.WriteLine($"Location: {ex.TargetSite?.Name ?? "Unknown"}");
            
            return 1;
        }
    }

    /// <summary>
    /// Deletes all emails from the Outlook inbox by retrieving and deleting in batches
    /// </summary>
    private static async Task DeleteAllEmails(OutlookService outlookService)
    {
        int totalDeleted = 0;
        bool hasMoreEmails = true;

        _logger?.LogInformation("Starting email deletion process with batch size {BatchSize}", BATCH_SIZE);

        while (hasMoreEmails)
        {
            _logger?.LogInformation("Retrieving batch of emails for deletion");

            // Create email request - always start from index 0 since we're deleting
            var request = new GetEmailRequest
            {
                StartIndex = 0,
                NumberOfEmails = BATCH_SIZE
            };

            // Retrieve emails
            var response = await outlookService.GetEmail(request);

            if (!response.Success)
            {
                throw new Exception($"Failed to retrieve emails: {response.Message}");
            }

            if (response.Emails == null || response.Emails.Count == 0)
            {
                _logger?.LogInformation("No more emails to delete");
                hasMoreEmails = false;
                break;
            }

            int batchCount = response.Emails.Count;
            _logger?.LogInformation("Retrieved {EmailCount} emails in this batch", batchCount);

            // Delete each email in the batch
            foreach (var email in response.Emails)
            {
                try
                {
                    _logger?.LogDebug("Deleting email ID: {EmailId}, Subject: {Subject}", email.Id, email.Subject);
                    
                    await outlookService.DeleteEmail(email);
                    
                    totalDeleted++;
                    
                    // Display progress
                    Console.Write($"\rDeleted {totalDeleted} emails...");
                }
                catch (Exception ex)
                {
                    throw new Exception($"Failed to delete email ID {email.Id}: {ex.Message}", ex);
                }
            }

            _logger?.LogInformation("Deleted {BatchCount} emails in this batch. Total deleted: {TotalDeleted}", 
                batchCount, totalDeleted);

            // Check if we've deleted all emails (fewer than requested means we're done)
            if (batchCount < BATCH_SIZE)
            {
                _logger?.LogInformation("Retrieved fewer emails than requested ({Count} < {BatchSize}), all emails deleted", 
                    batchCount, BATCH_SIZE);
                hasMoreEmails = false;
            }
        }

        Console.WriteLine(); // New line after progress indicator
        _logger?.LogInformation("Email deletion completed. Total emails deleted: {TotalDeleted}", totalDeleted);
    }
}
