
import smtplib, ssl
import sys

import json
import seaborn as sns
import matplotlib.pyplot as plt
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
import csv
import requests
from PIL import Image
from datetime import date
from selenium.webdriver.common.action_chains import ActionChains


import pandas as pd
from selenium import webdriver
import time
#Need third column to specify path to the area to monitor
from bs4 import BeautifulSoup
#for google api
# from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from selenium.webdriver.common.keys import Keys


def main():
    #constants, fill these in
    ADMIN_EMAIL = 'youremail@gmail.com' #where the error messages will be emailed to
    ADMIN_SPREADSHEET_ID = 'SAFDHSAHJ52424HJKHFDS' #should be able to find using https://stackoverflow.com/questions/36061433/how-to-do-i-locate-a-google-spreadsheet-id
    EMAIL_SENDER = "someotheremail@gmail.com" #the address that sends the emails, it's password should go in credentials.csv

    # check if internal csv and google drive same height
    #if not, find new emails and add
    if not check_if_ran_today(): #add back after testing
    # if True: #for testing
        csv_aligned_res = csvs_aligned() #list: index 0 is if same or not, 1 is 2d list of rows to update, [r][c]
        print(csv_aligned_res)
        if not csv_aligned_res[0]:
            print('out of synch')
            get_csvs_synched(csv_aligned_res[1])
        #read from csv and prep the loop
        df = pd.read_csv('internal_users.csv')
        df = df.apply(unfix_zip,axis='columns')
        # 'email', 'wunderground_link', 'zip', 'forecast', 'aqi', 'uv'

        #wrap in a for loop, cant use apply because selenium takes too long
        df_as_list=df.values.tolist()
        for row in df_as_list:
            should_continue=0
            try:
                get_uv_rating(row[2])  # uv.png
                should_continue = 1
            except:
                print('invalid zip, later once I can edit let user know, for now emails me and user')
                htmlToSend = """\
                                            <html>
                                              <head></head>
                                              <h1>Invalid Zip: """+str(row[2])+' remove this person</h1></html>'
                send(htmlToSend, ADMIN_EMAIL)
                htmlForUser = """\
                                            <html>
                                              <head></head>
                                              <h1>You entered the invalid zip: """+str(row[2])+'</h1><h1>Your email subscription will be terminated, please re-register at <a href="https://morningdew437318790.wordpress.com/2021/01/04/project-weather-email-bot/">this link</a></h1></html>'
                send(htmlForUser, row[0])
            if should_continue: #no error in zip code validation
                try:
                    get_weather_info(row[1]) #weather.png
                    aqi = get_aqi(row[1]) #note that interpretation not given, snag a chart
                    htmlToSend = """\
                                <html>
                                  <head></head>
                                  """ + '<h2>Zip Code: '+str(row[2])+ '<br/></h2><img src="cid:weather"/>' + '<br/><h2>AQI: '+ aqi + '</h2><img src="http://www.sparetheair.com/assets/aqi/PM2017.png"/><br/> ' + 'UV Index: <br/><img src="cid:uv"/> <br/> ' + """\
                                <img src="https://utilitycontractoronline.com/wp-content/uploads/2017/07/uv-index-chart.jpg"/><br/></html>
                                """
                    send(htmlToSend, row[0])
                except: #fill in with some error message once get all running
                    htmlToSend = '<html><head></head><h1>A general error occured in weather scraping app</h1></html>'
                    send(htmlToSend, ADMIN_EMAIL)



def check_if_ran_today():
    today = date.today().strftime("%m/%d/%y")
    file = open('last_run_date.txt', 'r', encoding='utf-8')
    text_in_file = file.read()
    file.close()
    if text_in_file != today:
        file = open('last_run_date.txt', 'w', encoding='utf-8')
        file.write(today)
        file.close()
        return False
    return True


def get_aqi(url_weather):
    url = url_weather.replace('weather','health') #accu is protected
    response = requests.get(url)  # , headers=headers
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup.find('div',{'class':'aqi-value'}).text

def send(htmlMsg, target_email):
#     #if decide want to have fancy emails or display changes in html
#     #https://realpython.com/python-send-email/
#https://stackoverflow.com/questions/3362600/how-to-send-email-attachments      also good
    me = EMAIL_SENDER
    you = target_email
    password = get_pw()
    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    today = date.today()

    msg['Subject'] = 'Weather Alert: '+today.strftime("%m/%d/%y")
    msg['From'] = me
    msg['To'] = you

    # Create the body of the message (a plain-text and an HTML version).
    text = "plain text - html failed"

    # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(htmlMsg, 'html')


    msg.attach(part1)
    msg.attach(part2)

    fp = open('weather.png', 'rb')
    image = MIMEImage(fp.read())
    fp.close()

    # Specify the  ID according to the img src in the HTML part
    image.add_header('Content-ID', '<weather>')
    msg.attach(image)

    fp = open('uv.png', 'rb')
    image = MIMEImage(fp.read())
    fp.close()

    # Specify the  ID according to the img src in the HTML part
    image.add_header('Content-ID', '<uv>')
    msg.attach(image)

    context = ssl.create_default_context()
    port = 465
    s = smtplib.SMTP_SSL("smtp.gmail.com", port, context=context)

    s.login("manisalertsystem@gmail.com", password)
    s.sendmail(me, you, msg.as_string())
    print('sent')
    print(msg['Subject'])
    s.quit()

def get_pw():
    with open('credentials.csv', mode='r')as file:
        csvFile = csv.reader(file)
        tmp = list(csvFile)
        return str(tmp[0][0])

def get_uv_rating(zip_code): #note it is not forecast, just one day
    #make based on api calls
    URL = f'https://enviro.epa.gov/enviro/efservice/getEnvirofactsUVHOURLY/ZIP/{zip_code}/json'  # documentation https://www.epa.gov/enviro/web-services#hourlyzip
    response = requests.get(URL)
    print(response)
    result = response.json()
    if result:  # if result is not empty
        plt.figure()
        df2 = pd.read_json(json.dumps(result))
        df2 = df2.apply(get_hour, axis='columns')
        df2.rename(columns={'UV_VALUE': 'UV Index Value'}, inplace=True)
        ax = sns.barplot(x='Hour', y='UV Index Value',hue='UV Index Value',data=df2.loc[(df2['Hour'] >= 6) & (df2.Hour <= 18)]) #add color palette mby later
        ax.set(ylim=(0, 12), title='UV')
        plt.legend().remove()
        plt.savefig('UV.png')
        plt.clf() #wipes canvas equivalent so can redo
    else:
        raise Exception('Invalid ZIP code given')

def get_hour(row):
    row['Hour'] = int(str(row.DATE_TIME).split()[1].split(':')[0])
    return row

#gives final image in weather.png
def get_weather_info(url_weather): # ['KNCCHAPE89']: #all 3 have roughly same ,'KNCCHAPE127','KNCCHAPE162']
    base = url_weather.replace('weather','forecast')
    driver = webdriver.Firefox()

    driver.get(base)
    time.sleep(1)
    driver.refresh()
    time.sleep(4)
    # ActionChains(driver).move_to_element(driver.find_element_by_xpath("//div[@class='legend-def preciphrlyliq']")).perform()
    # ActionChains(driver).move_to_element(driver.find_element_by_id("editMode")).perform()
    vert_scroll_dist = 430
    x_offset = 30
    bottom_offset = 255
    #from https://intellipaat.com/community/33193/how-can-i-scroll-a-web-page-using-selenium-webdriver-in-python
    driver.execute_script("window.scrollTo(0, "+str(vert_scroll_dist)+")") #found with javascript:alert(window.scrollY) on edge
    driver.save_screenshot("screenshot.png")
    #from https://pythonspot.com/selenium-take-screenshot/
    element = driver.find_element_by_xpath("//div[@class='canvas-bounds']")
    location = element.location;
    size = element.size;
    driver.save_screenshot("pageImage.png");

    # crop image
    x = location['x'] - x_offset;
    y = location['y'] - vert_scroll_dist;
    width = location['x'] + size['width'];
    height = y + size['height'] - bottom_offset;
    im = Image.open('pageImage.png')
    im = im.crop((int(x), int(y), int(width), int(height)))
    im.save('weather.png')

    driver.close()
def fix_zip(row): #to deal with dropping leading zreoes, from https://stackoverflow.com/questions/44011385/why-is-csv-writer-removing-leading-zeroes/44011617
    row['zip'] = "=\"" + row['zip'] + "\""
    return row

def unfix_zip(row):
    row['zip'] = str(row['zip']).replace('=','').replace('"','')
    return row

def get_csvs_synched(new_users_to_add):
    df = pd.DataFrame(new_users_to_add, columns=['timestamp', 'email', 'zip'])
    df.head(5)

    def map_settings_to_bin(row):
        row['forecast'] = 1
        row['aqi'] = 1
        row['uv'] = 1
        #had initially planned on giving users more options, elected to not implement this feature at this time
        # if 'Weather forecast' in row['settings']:
        #     row['forecast'] = 1
        # if 'Air quality' in row['settings']:
        #     row['aqi'] = 1
        # if 'UV levels' in row['settings']:
        #     row['uv'] = 1
        return row

    df = df.apply(map_settings_to_bin, axis="columns")
    print(df)
    # convert to list because apply does not work when selenium commands are involved
    df_as_list = df.values.tolist()
    # setting up, should be outside of for loop
    driver = webdriver.Firefox()
    driver.get('https://www.wunderground.com/')
    for row in df_as_list:
        item = driver.find_element_by_id('wuSearch')
        item.send_keys(str(row[2]))
        time.sleep(1)
        item.send_keys(Keys.ENTER)
        time.sleep(3)
        row.append(driver.current_url)
        time.sleep(2)
        item = 0
    driver.close()
    df_again = pd.DataFrame(df_as_list, columns=list(df.columns) + ['wunderground_link'])
    df_again = df_again.apply(fix_zip,axis="columns")
    df_subset = df_again.loc[:, ['email', 'wunderground_link','zip', 'forecast', 'aqi', 'uv']]
    df_s_as_list = df_subset.values.tolist()
    # source for structure: https://stackoverflow.com/questions/2363731/append-new-row-to-old-csv-file-python
    with open('internal_users.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        for row in df_s_as_list:
            writer.writerow(row)

def csvs_aligned(): #true if same length (meaning number of rows), false if not
    # code from google sheets api docs, modified for use with my google form
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    SAMPLE_RANGE_NAME = 'A2:C'  # goes as far as text goes
    """Shows basic usage of the Sheets API.
        Prints values from a sample spreadsheet.
        """
    number_of_users = -1
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=ADMIN_SPREADSHEET_ID,
                                range=SAMPLE_RANGE_NAME).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        raise Exception('No data found in Google API call')
    else:
        number_of_users = len(values)  # number of rows with content

    # our csv time
    with open('internal_users.csv', mode='r') as file:
        csvFile = csv.reader(file)
        tmp = list(csvFile)
        # print(tmp)
        internal_users = len(tmp) - 1  # since header is there
        # return str(tmp[0][0])
    print(internal_users, number_of_users)
    diff = number_of_users - internal_users
    # print(values[-diff:])  # gives relevant rows to add
    return [diff == 0, values[-diff:]]

main()