#!/usr/bin/env python3
"""Groene maaiers script for sending emails to enlisted users on a Gsheet."""
import os
import re
import smtplib
import ssl
import sys
import typing
from datetime import date, timedelta
from email.message import EmailMessage

from apiclient import discovery
from decouple import config
from google.oauth2 import service_account
from rich import print as pprint

CONTACTS_INFO = dict[str, dict[str, str]]
SHEET = list[list[str]]
ROW = list[str]
EMAILS = typing.Set[str]


def get_contact_name_email(credentials) -> CONTACTS_INFO:
    """Get contact name and email."""
    sheet_id = config("CONTACTS_SHEET_ID")
    sheet_range = f"contacts!{config('CONTACTS_SHEET_RANGE')}"
    service = discovery.build("sheets", "v4", credentials=credentials, num_retries=3)
    sheet = service.spreadsheets()
    values = sheet.values()
    spreadsheet = values.get(spreadsheetId=sheet_id, range=sheet_range)
    result = spreadsheet.execute()
    return extract_contacts_info(result.get("values", []))


def extract_contacts_info(contacts: SHEET) -> CONTACTS_INFO:
    """Extract contacts information."""
    name_mail_dict = {}

    for line in contacts:
        if len(line) == 4:
            name, email, _, extra_namen = line
        elif len(line) == 3:
            extra_namen = ""
            name, email, _ = line
        else:
            pprint(f"Could not process line: {line}")
            continue

        name_mail_dict[name] = {
            "name": name,
            "email": email,
            "extra": extra_namen,
        }
    return name_mail_dict


def get_sheet(credentials) -> SHEET:
    """Get the desired Google sheet."""
    sheet_id = config("SCHEMA_SHEET_ID")
    sheet_range = f"{date.today().year}!{config('SCHEMA_SHEET_RANGE')}"
    service = discovery.build("sheets", "v4", credentials=credentials, num_retries=3)
    sheet = service.spreadsheets()
    values = sheet.values()
    spreadsheet = values.get(spreadsheetId=sheet_id, range=sheet_range)
    result = spreadsheet.execute()
    return result.get("values", [])


def get_sheet_row(sheet_list: SHEET, short_date: str) -> tuple[ROW, bool]:
    """Get the desired row within the sheet."""
    return next(
        ((line, True) for line in sheet_list if line[0] == short_date),
        ([""], False),
    )


def get_sheet_row_names(row: ROW, index: int = 5) -> str:
    """Get the names from the row."""
    try:
        return row[index]
    except IndexError:
        message = admin_email_message(f"Names information not found in sheet. row: {row}")
    except TypeError:
        message = admin_email_message(f"TypeError:\nrow: {row}\nindex: {index}")
    send_notification(message)
    return ""


def get_next_saturday_datetime():
    """Get the upcoming Saturday."""
    today = date.today()
    saturday = today + timedelta((5 - today.weekday()) % 7)
    return saturday.strftime("%d-%m")


def find_email_based_on_name_list(name, contact_dict):
    """given the contact_dict find the email address based on the name field.
    If not found, the 'extra' field is used.
    """
    name = name.lower()

    email_list = [
        contact_dict[key]["email"] for key in contact_dict.keys() if key.lower().startswith(name)
    ]

    if not email_list:
        for key in contact_dict.keys():
            r = re.compile(rf"\b{name}\b", re.IGNORECASE)
            if contact_dict[key].get("extra") and r.search(contact_dict[key].get("extra", "")):
                email_list.append(contact_dict[key]["email"])

    if email_list:
        return set(email_list)
    else:
        msg = f"Action Bart.\nName: {name!r} not found in contacts."
    message = admin_email_message(msg)
    send_notification(message)


def standard_email_message(names: list[str], emails: EMAILS) -> EmailMessage:
    """Create a standard email message."""
    subject = f"Groen onderhoud herinnering voor {get_next_saturday_datetime()}"
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
        from_=config("FROM_USR"),
        to=emails,
        subject=subject,
        body=body,
        bcc=config("ADM_EMAIL"),
    )


def admin_email_message(body: str) -> EmailMessage:
    """Create an admin email message."""
    subject = "Groen email script issue"
    return make_mail_message(
        from_=config("FROM_USR"), to=config("ADM_EMAIL"), subject=subject, body=body
    )


def make_mail_message(
    from_: str, to: EMAILS, subject: str, body: str = "", cc: str = "", bcc: str = ""
) -> EmailMessage:
    """Create the base for the email message."""
    msg = EmailMessage()
    msg["From"] = from_
    msg["To"] = to
    msg["Cc"] = cc
    msg["Bcc"] = bcc
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


def send_email(message: EmailMessage) -> None:
    """Send the email."""
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
        pprint(f"Error: unable to send email. error: {e}")
        sys.exit(1)


def send_notification(message: EmailMessage) -> None:
    """Send the notification, either email or print."""
    email_on = config("EMAIL_ON", default=False, cast=bool)
    send_email(message) if email_on else pprint(message)


def get_names_list(names: str) -> list[str]:
    """Extract the names from the string."""
    split_names = re.split(r",| en |/|\.", names)
    return [name.strip() for name in split_names if name]


def main() -> None:
    """main."""
    base_path = os.path.dirname(os.path.abspath(__file__))
    credentials_file = os.path.join(base_path, "credentials.json")
    scopes = [
        "https://www.googleapis.com/auth/contacts.readonly",
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    ]
    credentials = service_account.Credentials.from_service_account_file(
        credentials_file, scopes=scopes
    )

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
    names_list = get_names_list(names)

    # continue matching it with the contact information
    contacts = get_contact_name_email(credentials)
    mailing_list: EMAILS = set()
    for name in names_list:
        if name:
            mailing_list = mailing_list.union(find_email_based_on_name_list(name, contacts))

    message = standard_email_message(names=names_list, emails=mailing_list)
    send_notification(message)


if __name__ == "__main__":
    main()
