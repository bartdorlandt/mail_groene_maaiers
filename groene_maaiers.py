#!/usr/bin/python3
import sys
import os

# google sheet
# import gspread
# from oauth2client.service_account import ServiceAccountCredentials

# google contacts
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# other
from rich import print
from datetime import timedelta, date
import re
from decouple import config
import smtplib
import ssl
from email.message import EmailMessage
# from email.utils import parseaddr


def credentials_check_setup(scopes, credentials_file='credentials.json', token_file='token.json'):
    credentials = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_file):
        credentials = Credentials.from_authorized_user_file(token_file, scopes)
    # If there are no (valid) credentials available, let the user log in.
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file, scopes)
            credentials = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_file, 'w') as token:
            token.write(credentials.to_json())


def set_credentials_for_api(scope, file='token.json'):
    return Credentials.from_authorized_user_file(file, scopes=scope)


def get_contact_name_email(credentials):
    service = build('people', 'v1', credentials=credentials)
    results = service.people().connections().list(
        resourceName='people/me',
        pageSize=100,
        personFields='names,emailAddresses,phoneNumbers,biographies').execute()
    # personFields='names,emailAddresses').execute()
    connections = results.get('connections', [])
    return extract_contacts_info(connections)


def extract_contacts_info(contacts):
    name_mail_dict = {}

    for person in contacts:
        name = email = biography = phone = None
        names = person.get('names')
        emails = person.get('emailAddresses')
        biographies = person.get('biographies')
        phones = person.get('phoneNumbers')
        if names:
            name = names[0].get('displayName', '')
        if emails:
            email = emails[0].get('value', '')
        if biographies:
            biography = biographies[0].get('value', '')
        if phones:
            phone = phones[0].get('value', '')

        name_mail_dict[name] = {
            'name': name,
            'email': email,
            'notes': biography,
            'phone': phone,
        }
    return name_mail_dict


def get_sheet(credentials):
    sheet_id = '1VVlJBiXnuQ_kw56RgumIyCln3yQks5RyjMGLwy3nttE'
    sheet_range = 'Blad1!1:26'
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=sheet_id,
                                range=sheet_range).execute()
    return result.get('values', [])


def get_sheet_row(sheet_list, short_date):
    for line in sheet_list:
        if line[0] == short_date:
            return line


def get_sheet_row_names(row, index=5):
    try:
        return row[index]
    except IndexError:
        # todo, email bart
        print('Names not found. row: %s' % row)


def get_next_saturday_datetime():
    today = date.today()
    saturday = today + timedelta((5 - today.weekday()) % 7)
    return saturday.strftime("%d-%m")


# def get_index_number_of_datum_col(sheet):
#     """Adding one, because of the header"""
#     cols = sheet.col_values(1)
#     return cols.index(get_next_saturday_datetime()) + 1
# def get_names_cell(sheet, index):
#     return sheet.cell(index, 6).value


def find_email_based_on_name_list(name, contact_dict):
    return [contact_dict[key]['email'] for key in contact_dict.keys()
            if key.lower().startswith(name.strip().lower())]

# def find_emails():
#     mail_string = get_names_cell()
#     mail_string = mail_string.replace(',', ' ')
#     mail_reg = r'\S+@\S+\.\S+'
#     match = re.findall(mail_reg, mail_string)
#     return set(match)


def gen_email_list(names_list, contacts):
    mailing_list = []
    for name in names_list:
        emails = find_email_based_on_name_list(name, contacts)
        if len(emails) != 1:
            print('Action Bart. Name: %r result is a non-unique entry. Found: %s' % (name, emails))
        else:
            mailing_list.extend(emails)
    return mailing_list


def make_mail_message(mail_from, mail_to):
    msg = EmailMessage()
    subject = "Groen onderhoud reminder %s" % get_next_saturday_datetime()
    # TODO make a nice body text
    body = 'test for Bart'
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
    scopes = [
        "https://www.googleapis.com/auth/contacts.readonly",
        "https://www.googleapis.com/auth/spreadsheets.readonly"
    ]
    credentials_check_setup(scopes)
    credentials = set_credentials_for_api(scopes)
    contacts = get_contact_name_email(credentials)

    sheet_list = get_sheet(credentials)
    sheet_row = get_sheet_row(sheet_list=sheet_list, short_date=get_next_saturday_datetime())
    names = get_sheet_row_names(row=sheet_row)
    names_list = names.split(',')

    mailing_list = gen_email_list(names_list=names_list, contacts=contacts)
    # send email to list of people
    print(set(mailing_list))


if __name__ == '__main__':
    main()
    # row = sheet.row_values(3)
    # c1 = sheet.cell(10, 1).value

    # Extract and print all of the values
    # list_of_hashes = sheet.get_all_records()
    # pprint(list_of_hashes)
    # print(get_mail_cell())
