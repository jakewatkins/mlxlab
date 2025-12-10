# Setup training data

I need a python script that uses /Users/jakewatkins/source/projects/local-ai/training-data/classified-email-data.json to create training, validation, and testing files to use for model fine tuning.
The script will take 2 parameters: the input data file and the folder to store the output in:
    python setup-training-data.py --input /Users/jakewatkins/source/projects/local-ai/training-data/classified-email-data.json --output /Users/jakewatkins/source/projects/local-ai/training-data/

the script will append -training, -validation, -testing to input file name.  So in the example above there will be two files:
    - classified-email-data.jsonl
    - classified-email-data.jsonl
    - classified-email-data.jsonl

# Input schema
- the input file will have the following json schema:
    [
        {
            "Content": "Use Same-Day Delivery and get what you need today without leaving the house. ͏‌ ͏Jake’s pet family, get closer to your next reward. Shop Now  20% OFF Your FirstSame-Day Delivery Save on the fastest way to get your pet’s essentials delivered straight to your door. SHOP NOW Must be logged in. Offer valid 9/10–9/16/23. Exclusions apply. See Details  Your neighborhood Petco  HIGHLAND VILLAGE PETCO 3194 Fm 407, Highland Village TX 75077 972-317-3268 View Map  |  Find Another Location   SERVICES AT HIGHLAND VILLAGE PETCO: • Product Demos • Self-Service Dog Wash • Full-Service Grooming • Aquatics • Dog Training • Hospital   STORE HOURS: Monday 9:00 AM - 8:00 PM Tuesday 9:00 AM - 8:00 PM Wednesday 9:00 AM - 8:00 PM Thursday 9:00 AM - 8:00 PM Friday 9:00 AM - 8:00 PM Saturday 9:00 AM - 8:00 PM Sunday 10:00 AM - 7:00 PM    Memberships and programs Shop Book appointment What your pet needs, your way DOWNLOAD THE PETCO APP An easier way to manage your services andorders in one convenient place. Product prices displayed in our emails may not match the final price on our website. To view the exact price of a product, please refer to petco.com or the Petco app at checkout. Exclusions may apply to Vital Care nutrition perks and benefits. This email was sent to: runsincirclesscreaming@msn.com. You have received this email because you asked to be included in petco.com mailings. Please add Petco (petco@e.petco.com) to your email address book. Questions About Orders? Comments or Concerns? Please contact us. This message is from: Petco Animal Supplies, Inc., 10850 Via Frontera, San Diego, CA 92127View in Browser    |     Privacy Policy    |     Unsubscribe",
            "Classification": "promotional"
        },
        {
            "Content": "Dear runsincirclesscreaming,FYI, attached file. The complete version of this receipt has been attached to this e-mail:runsincirclesscreaming@msn.com,--------------------------------- Thank you for the business.",
            "Classification": "transactional"
        }
    ]

# Split rations
- Use a split ratio of 80/10/10 (train/valid/test)

# Random seed
- Use a fixed random seed
- Generate the seed value when the script is generated (surprise me)

# Stratification
- The script should maintain the same distribution of email categories across categories

# Minimum sample per category
- Warn the user about the low-sample categories, showing the name of the category
- Include them only in thr training set. 
- A category is considered 'low' if it has fewer than 10 samples.

# Output directory 
- if the output directory doesnt exist, print an error and exit the script.

# Output schema
- use the 'simple' training scheam for the training file where the email body and the classification are concatenated like they are in email-training.jsonl.

# Validation
- Validate that all fo the categories are represented in the training data
