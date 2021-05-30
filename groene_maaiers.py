#!/usr/bin/python3
import sys

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from rich import print
from pprint import pprint
from datetime import timedelta, date
from email.utils import parseaddr
import re
from decouple import config
import smtplib
import ssl
from email.message import EmailMessage

# def date_plus_days(days=4):
#     return date.today() + timedelta(days=days)


def get_sheet():
    # use creds to create a client to interact with the Google Drive API
    scope = (
        "https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
        "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive")
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)

    # use the name of the sheet
    return client.open("binnentuin_schema").sheet1


def get_datetime_of_string(string):
    """input = 12-06"""
    year = date.today().year
    day, month = string.split('-')
    return date(year, int(month), int(day))


def get_next_saturday_datetime():
    today = date.today()
    saturday = today + timedelta((5-today.weekday()) % 7)
    return saturday.strftime("%d-%m")


def get_index_number_of_datum_col():
    """Adding one, because of the header"""
    cols = sheet.col_values(1)
    return cols.index(get_next_saturday_datetime()) + 1


def get_mail_cell():
    # TODO, change it to 6
    return sheet.cell(get_index_number_of_datum_col(), 7).value


def find_emails():
    mail_string = get_mail_cell()
    mail_string = mail_string.replace(',', ' ')
    mail_reg = r'\S+@\S+\.\S+'
    match = re.findall(mail_reg, mail_string)
    return set(match)


def make_message(mail_from, mail_to, subject, body):
    msg = EmailMessage()
    msg.set_content(body)

    msg['Subject'] = subject
    msg['From'] = mail_from
    msg['To'] = mail_to
    return msg


def send_email(receiver):
    # Create a secure SSL context
    context = ssl.create_default_context()
    smtp_user = config('SMTP_USR')
    subject = "Groen onderhoud reminder %s" % get_next_saturday_datetime()
    message_body = 'test voor bart'
    msg = make_message(mail_from=smtp_user, mail_to=receiver, subject=subject, body=message_body)

    # try:
    with smtplib.SMTP_SSL(config('SMTP_SRV'), config('SMTP_PORT'), context=context) as server:
        server.login(smtp_user, config('SMTP_PWD'))
        server.send_message(msg)
    # except smtplib.SMTPException:
        # print("Error: unable to send email")
        # sys.exit(1)
    print("Successfully sent email")


if __name__ == '__main__':
    sheet = get_sheet()

    # row = sheet.row_values(3)
    # c1 = sheet.cell(10, 1).value

    # Extract and print all of the values
    # list_of_hashes = sheet.get_all_records()
    # pprint(list_of_hashes)
    print(get_mail_cell())
