# weather_bot
Emails weather updates to those who are subscribed using Python <br/>
Subscribe [here](https://morningdew437318790.wordpress.com/2021/01/04/project-weather-email-bot/)
## How it works
 - Subscribed users are stored on a Google Sheet (which is connected to a Google Form)
 - Google sheet information mapped to internal_users.csv with more relevant information
	- Selenium used to generate link from which weather forecasts are taken
 - Daily, main.py is run to send emails to those who are subscribed 
	- Information obtained using Selenium, BeautifulSoup, and an API visualized with Seaborn
 
## How to run on personal machine
 - Download credentials.json from Google API and put in directory
 - Download geckodriver so Selenium can run on Firefox
 - Change ADMIN_ and EMAIL_ constants in main.py
	- Also modify credentials.csv to have your email_sender account password
 

 
