#!/usr/bin/python3
import sys

# google sheet
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# google contacts
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# other
from rich import print
from datetime import timedelta, date
# from email.utils import parseaddr
import re
from decouple import config
import smtplib
import ssl
from email.message import EmailMessage

# def date_plus_days(days=4):
#     return date.today() + timedelta(days=days)


def get_contact_connection(scope):
    credentials = Credentials.from_authorized_user_file('token.json', scopes=scope)
    return build('people', 'v1', credentials=credentials)


def get_contact_name_email(service):
    name_mail_dict = {}
    results = service.people().connections().list(
        resourceName='people/me',
        pageSize=100,
        personFields='names,emailAddresses').execute()
    connections = results.get('connections', [])
    for person in connections:
        name = email = None
        names = person.get('names')
        emails = person.get('emailAddresses')
        if names:
            name = names[0].get('displayName', '')
        if emails:
            email = emails[0].get('value', '')

        if name and email:
            name_mail_dict[name] = email
    return name_mail_dict


def get_sheet_connection(scope):
    # use credentials to create a client to interact with the Google Drive API
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        'credentials.json', scope)
    client = gspread.authorize(credentials)
    # use the name of the sheet
    return client.open("binnentuin_schema").sheet1


# def get_datetime_of_string(string):
#     """input = 12-06"""
#     year = date.today().year
#     day, month = string.split('-')
#     return date(year, int(month), int(day))


def get_next_saturday_datetime():
    today = date.today()
    saturday = today + timedelta((5-today.weekday()) % 7)
    return saturday.strftime("%d-%m")


def get_index_number_of_datum_col(sheet):
    """Adding one, because of the header"""
    cols = sheet.col_values(1)
    return cols.index(get_next_saturday_datetime()) + 1


def get_names_cell(sheet, index):
    return sheet.cell(index, 6).value


def find_email_based_on_name_list(name, contact_dict):
    return [contact_dict[key] for key in contact_dict.keys()
            if key.lower().startswith(name.strip().lower())]

# def find_emails():
#     mail_string = get_names_cell()
#     mail_string = mail_string.replace(',', ' ')
#     mail_reg = r'\S+@\S+\.\S+'
#     match = re.findall(mail_reg, mail_string)
#     return set(match)


def make_mail_message(mail_from, mail_to):
    msg = EmailMessage()
    subject = "Groen onderhoud reminder %s" % get_next_saturday_datetime()
    # TODO make a nice body text
    body = 'test voor bart'
    msg.set_content(body)

    msg['Subject'] = subject
    msg['From'] = mail_from
    msg['To'] = mail_to
    return msg


def send_email(receiver):
    # Create a secure SSL context
    context = ssl.create_default_context()
    smtp_user = config('SMTP_USR')
    message = make_mail_message(mail_from=smtp_user, mail_to=receiver)

    try:
        with smtplib.SMTP_SSL(config('SMTP_SRV'), config('SMTP_PORT'), context=context) as server:
            server.login(smtp_user, config('SMTP_PWD'))
            server.send_message(message)
    except smtplib.SMTPException:
        print("Error: unable to send email")
        sys.exit(1)

    print("Successfully sent email")


def main():
    scope_sheet = (
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        # "https://spreadsheets.google.com/feeds",
        # "https://www.googleapis.com/auth/drive.file",
    )
    scope_contacts = ['https://www.googleapis.com/auth/contacts.readonly']

    sheet = get_sheet_connection(scope_sheet)
    contact_service = get_contact_connection(scope_contacts)
    contacts = get_contact_name_email(contact_service)

    # saturday = get_next_saturday_datetime()
    index = get_index_number_of_datum_col(sheet)
    who = get_names_cell(sheet, index)
    who_list = who.split(',')

    mailing_list = []
    for name in who_list:
        emails = find_email_based_on_name_list(name, contacts)
        if len(emails) != 1:
            print('Action Bart. Name: %r result is non-unique entry'
                  % name)
        else:
            mailing_list.extend(emails)

    # send email to list of people
    print(mailing_list)


if __name__ == '__main__':
    main()
    # row = sheet.row_values(3)
    # c1 = sheet.cell(10, 1).value

    # Extract and print all of the values
    # list_of_hashes = sheet.get_all_records()
    # pprint(list_of_hashes)
    # print(get_mail_cell())
