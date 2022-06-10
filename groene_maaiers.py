#!/usr/bin/env python3
import os
import re
import smtplib
import ssl
import sys
from datetime import date, timedelta
from email.message import EmailMessage

from decouple import config
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from rich import print


def credentials_check_setup(scopes, credentials_file, token_file):
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
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, scopes)
            credentials = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_file, "w") as token:
            token.write(credentials.to_json())


def set_credentials_for_api(scope, file):
    return Credentials.from_authorized_user_file(file, scopes=scope)


def get_contact_name_email(credentials):
    service = build("people", "v1", credentials=credentials, num_retries=3)
    results = (
        service.people()
        .connections()
        .list(
            resourceName="people/me",
            pageSize=100,
            personFields="names,emailAddresses,phoneNumbers,biographies",
        )
        .execute()
    )
    connections = results.get("connections", [])
    return extract_contacts_info(connections)


def extract_contacts_info(contacts):
    name_mail_dict = {}

    for person in contacts:
        name = email = biography = phone = None
        names = person.get("names")
        emails = person.get("emailAddresses")
        biographies = person.get("biographies")
        phones = person.get("phoneNumbers")
        if names:
            name = names[0].get("displayName", "")
        if emails:
            email = emails[0].get("value", "")
        if biographies:
            biography = biographies[0].get("value", "")
        if phones:
            phone = phones[0].get("value", "")

        name_mail_dict[name] = {
            "name": name,
            "email": email,
            "notes": biography,
            "phone": phone,
        }
    return name_mail_dict


def get_sheet(credentials):
    sheet_id = "1VVlJBiXnuQ_kw56RgumIyCln3yQks5RyjMGLwy3nttE"
    sheet_range = "2022!3:26"
    service = build("sheets", "v4", credentials=credentials, num_retries=3)
    sheet = service.spreadsheets()
    values = sheet.values()
    spreadsheet = values.get(spreadsheetId=sheet_id, range=sheet_range)
    result = spreadsheet.execute()
    return result.get("values", [])


def get_sheet_row(sheet_list, short_date):
    for line in sheet_list:
        if line[0] == short_date:
            return line, True
    else:
        # The date is not found in the sheet.
        # message = admin_email_message(f"Date ({short_date}) not found in sheet.")
        # send_notification(message)
        return "", False


def get_sheet_row_names(row, index=5):
    try:
        return row[index]
    except IndexError:
        message = admin_email_message(f"Names information not found in sheet. row: {row}")
        send_notification(message)
    except TypeError:
        message = admin_email_message(f"TypeError:\nrow: {row}\nindex: {index}")
        send_notification(message)


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
        if key.lower().startswith(name):
            email_list.append(contact_dict[key]["email"])

        r = re.compile(rf"\b{name}\b", re.IGNORECASE)
        if contact_dict[key].get("notes") and r.search(contact_dict[key].get("notes", "")):
            email_list.append(contact_dict[key]["email"])

    if len(email_list) > 0:
        return set(email_list)
    elif len(email_list) == 0:
        msg = "Action Bart.\nName: %r not found in contacts." % name
    else:
        msg = "Unsure, Name: %r Found: %s" % (name, email_list)

    message = admin_email_message(msg)
    send_notification(message)


def standard_email_message(names, emails):
    subject = "Groen onderhoud herinnering voor %s" % get_next_saturday_datetime()
    body = (
        f"Beste {', '.join(names)},\n\n"
        "Voor aanstaand weekend sta je aangemeld voor het onderhoud aan de binnentuin.\n"
        f"Via {config('GROEN_CONTACT')} ({config('GROEN_MOBIEL')}) kan het "
        "gereedschap geregeld worden.\n"
        "Stem het aub tijdig af zodat je niet voor een dichte deur staat.\n\n"
        "Mocht het onverhoopt niet door kunnen gaan, regel even iemand anders of "
        "laat het de groencommissie even weten.\n\n"
        f"email: {config('FROM_USR')}\n"
    )

    return make_mail_message(
        From=config("FROM_USR"),
        To=emails,
        Subject=subject,
        body=body,
        Bcc=config("ADM_EMAIL"),
    )


def admin_email_message(body):
    subject = "Groen email script issue"
    return make_mail_message(
        From=config("FROM_USR"), To=config("ADM_EMAIL"), Subject=subject, body=body
    )


def make_mail_message(From, To, Subject, body="", Cc="", Bcc=""):
    msg = EmailMessage()
    msg["From"] = From
    msg["To"] = To
    msg["Cc"] = Cc
    msg["Bcc"] = Bcc
    msg["Subject"] = Subject
    msg.set_content(body)
    return msg


def send_email(message):
    # Create a secure SSL context
    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL(
            config("SMTP_SRV"), config("SMTP_PORT", default=465), context=context
        ) as server:
            server.ehlo()  # Can be omitted
            server.login(config("SMTP_USR"), config("SMTP_PWD"))
            server.send_message(message)
    except smtplib.SMTPException as e:
        print(f"Error: unable to send email. error: {e}")
        sys.exit(1)


def send_notification(message):
    email_on = config("EMAIL_ON", default=False, cast=bool)
    send_email(message) if email_on else print(message)


def main():
    base_path = os.path.dirname(os.path.abspath(__file__))
    credentials_file = os.path.join(base_path, "credentials.json")
    token_file = os.path.join(base_path, "token.json")
    scopes = [
        "https://www.googleapis.com/auth/contacts.readonly",
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    ]
    credentials_check_setup(scopes=scopes, credentials_file=credentials_file, token_file=token_file)
    credentials = set_credentials_for_api(scopes, file=token_file)

    # Get information from the sheet first
    sheet_list = get_sheet(credentials)
    sheet_row, date_found = get_sheet_row(
        sheet_list=sheet_list, short_date=get_next_saturday_datetime()
    )
    if not date_found:
        return

    names = get_sheet_row_names(row=sheet_row)
    if not names:
        return
    names_list = [name.strip() for name in names.split(",")]

    # continue matching it with the contact information
    contacts = get_contact_name_email(credentials)
    mailing_list = set()
    for name in names_list:
        if name:
            mailing_list = mailing_list.union(find_email_based_on_name_list(name, contacts))

    message = standard_email_message(names=names_list, emails=mailing_list)
    send_notification(message)


if __name__ == "__main__":
    main()
