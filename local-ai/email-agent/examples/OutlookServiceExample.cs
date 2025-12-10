using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using EmailAgent.Core;
using EmailAgent.Services;
using EmailAgent.Entities;

namespace EmailAgent.Examples;

/// <summary>
/// Example usage of the OutlookService
/// </summary>
public class OutlookServiceExample
{
    /// <summary>
    /// Demonstrates how to use the OutlookService to retrieve emails
    /// </summary>
    public static async Task RunExample()
    {
        // Setup configuration
        var configuration = new ConfigurationBuilder()
            .AddJsonFile("settings.json")
            .Build();

        // Setup logging
        using var loggerFactory = Microsoft.Extensions.Logging.LoggerFactory.Create(builder =>
            builder.AddConsole().SetMinimumLevel(LogLevel.Information));
        var logger = loggerFactory.CreateLogger<OutlookServiceExample>();

        try
        {
            // Initialize agent configuration
            var agentConfig = new AgentConfiguration(configuration);
            logger.LogInformation("AgentConfiguration initialized successfully");

            // Initialize Outlook service
            var outlookService = new OutlookService(agentConfig, logger);
            logger.LogInformation("OutlookService initialized successfully");

            // Create email request
            var request = new GetEmailRequest
            {
                StartIndex = 0,
                NumberOfEmails = 5  // Retrieve 5 oldest emails
            };

            logger.LogInformation("Retrieving {EmailCount} emails from Outlook", request.NumberOfEmails);

            // Retrieve emails (this will prompt for interactive authentication)
            var response = await outlookService.GetEmail(request);

            // Process response
            if (response.Success)
            {
                logger.LogInformation("Successfully retrieved {EmailCount} emails", response.Count);

                foreach (var email in response.Emails)
                {
                    Console.WriteLine($"Email ID: {email.Id}");
                    Console.WriteLine($"Service: {email.Service}");
                    Console.WriteLine($"From: {email.From}");
                    Console.WriteLine($"Subject: {email.Subject}");
                    Console.WriteLine($"Sent: {email.SentDateTime:yyyy-MM-dd HH:mm:ss}");
                    Console.WriteLine($"To: {string.Join(", ", email.To)}");
                    
                    if (email.CC.Any())
                        Console.WriteLine($"CC: {string.Join(", ", email.CC)}");
                    
                    if (email.BCC.Any())
                        Console.WriteLine($"BCC: {string.Join(", ", email.BCC)}");
                    
                    Console.WriteLine($"Body Length: {email.Body.Length} characters");
                    Console.WriteLine($"Attachments: {email.Attachments.Count}");

                    // Display attachment details
                    foreach (var attachment in email.Attachments)
                    {
                        Console.WriteLine($"  - {attachment.Name} ({attachment.Type}, {attachment.Size} bytes)");
                    }

                    Console.WriteLine(new string('-', 50));
                }
            }
            else
            {
                logger.LogError("Failed to retrieve emails: {ErrorMessage}", response.Message);
                Console.WriteLine($"Error: {response.Message}");
            }
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "An error occurred while running the Outlook example");
            Console.WriteLine($"Exception: {ex.Message}");
        }
    }
}
