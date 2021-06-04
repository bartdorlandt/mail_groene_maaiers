#!/usr/bin/python3
import sys
import os

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

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
        email_message = admin_email_message('Names information not found in sheet. row: %s' % row)
        send_email(email_message) if not no_email else print(email_message)


def get_next_saturday_datetime():
    today = date.today()
    saturday = today + timedelta((5 - today.weekday()) % 7)
    return saturday.strftime("%d-%m")


def find_email_based_on_name_list(name, contact_dict):
    """given the contact_dict find the email address based on the name field.
    If not found, the notes (biography) field is used.
    """
    email_list = []
    name = name.lower()
    for key in contact_dict.keys():
        # print(contact_dict[key])
        if key.lower().startswith(name):
            email_list.append(contact_dict[key]['email'])
        elif contact_dict[key].get('notes') and name in contact_dict[key].get('notes').lower():
            # name not found in the key
            email_list.append(contact_dict[key]['email'])

    if len(email_list) == 0:
        msg = 'Action Bart.\nName: %r not found in contacts.' % name
    elif len(email_list) > 1:
        msg = 'Action Bart.\nName: %r result is a non-unique entry. Found: %s' % (name, email_list)
    else:
        return email_list[0]

    # print(msg)
    email_message = admin_email_message(msg)
    send_email(email_message) if not no_email else print(email_message)

# def find_emails():
#     mail_string = get_names_cell()
#     mail_string = mail_string.replace(',', ' ')
#     mail_reg = r'\S+@\S+\.\S+'
#     match = re.findall(mail_reg, mail_string)
#     return set(match)
# def get_index_number_of_datum_col(sheet):
#     """Adding one, because of the header"""
#     cols = sheet.col_values(1)
#     return cols.index(get_next_saturday_datetime()) + 1
# def get_names_cell(sheet, index):
#     return sheet.cell(index, 6).value
# def gen_email_list(names_list, contacts):
#     return {find_email_based_on_name_list(name, contacts) for name in names_list}


def standard_email_message(names, emails):
    subject = "Groen onderhoud herinnering voor %s" % get_next_saturday_datetime()
    body = f"Beste {', '.join(names)},\n\n" \
           "Voor aanstaand weekend sta je aangemeld voor het onderhoud aan de binnentuin.\n" \
           f"Via {config('GROEN_CONTACT')} ({config('GROEN_MOBIEL')}) kan het gereedschap " \
           "geregeld worden.\n\n" \
           "Mocht het onverhoopt niet door kunnen gaan, laat het de groencommissie even weten." \
           "\n\n" \
           "email: %s\n" % config('SMTP_USR')

    # return make_mail_message(mail_from=config('SMTP_USR'), mail_to=emails,
    return make_mail_message(mail_from=config('SMTP_USR'),
                             mail_to=emails,
                             subject=subject, body=body,
                             mail_bcc=config('ADM_EMAIL'))


def admin_email_message(body):
    subject = "Groen email script issue"
    return make_mail_message(mail_from=config('SMTP_USR'), mail_to=config('ADM_EMAIL'),
                             subject=subject, body=body)


def make_mail_message(mail_from, mail_to, subject, body='', mail_cc=None, mail_bcc=None):
    msg = EmailMessage()
    msg['From'] = mail_from
    msg['To'] = mail_to
    if mail_cc:
        msg['Cc'] = mail_cc
    if mail_bcc:
        msg['Bcc'] = mail_bcc
    msg['Subject'] = subject
    msg.set_content(body)
    return msg


def send_email(message):
    # Create a secure SSL context
    context = ssl.create_default_context()
    smtp_user = config('SMTP_USR')

    try:
        with smtplib.SMTP_SSL(config('SMTP_SRV'), config('SMTP_PORT', default=465),
                              context=context) as server:
            server.login(smtp_user, config('SMTP_PWD'))
            server.send_message(message)
    except smtplib.SMTPException:
        print("Error: unable to send email")
        sys.exit(1)

    print("Successfully sent email")


def main():
    no_email = config('EMAIL_OFF', default=False)

    scopes = [
        "https://www.googleapis.com/auth/contacts.readonly",
        "https://www.googleapis.com/auth/spreadsheets.readonly"
    ]
    credentials_check_setup(scopes)
    credentials = set_credentials_for_api(scopes)

    # Get information from the sheet first
    sheet_list = get_sheet(credentials)
    sheet_row = get_sheet_row(sheet_list=sheet_list, short_date=get_next_saturday_datetime())
    names = get_sheet_row_names(row=sheet_row)
    if not names:
        return
    names_list = [name.strip() for name in names.split(',')]

    # continue matching it with the contact information
    contacts = get_contact_name_email(credentials)
    mailing_list = {find_email_based_on_name_list(name, contacts) for name in names_list}
    # print(mailing_list)
    email_message = standard_email_message(names=names_list, emails=mailing_list)
    # print(email_message)
    send_email(email_message) if not no_email else print(email_message)


if __name__ == '__main__':
    main()
    # row = sheet.row_values(3)
    # c1 = sheet.cell(10, 1).value

    # Extract and print all of the values
    # list_of_hashes = sheet.get_all_records()
    # pprint(list_of_hashes)
    # print(get_mail_cell())
