# get more email

I'd like to update outlookAgent to retrieve email from 5 folders in the account.  The folders are:
- Inbox
- Recruiters
- shopping
- social media
- junk email

We should be able to do this by setting the Folder property on the EmailRequest object.  The folder type will be Custom.
The updated outlookAgent will save the downloaded emails in files named after the folder they are downloaded from.  For example emails in the Recruiters folder will be saved in Recruiters.json

