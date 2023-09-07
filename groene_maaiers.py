#!/usr/bin/env python3
"""Groene maaiers script for sending emails to enlisted users on a Gsheet."""
import os
import re
import smtplib
import ssl
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, timedelta
from email.message import EmailMessage

from apiclient import discovery
from decouple import config
from google.oauth2 import service_account
from google.oauth2.service_account import Credentials
from rich import print as pprint


class SendMailError(Exception):
    """Send Email Error exception."""


@dataclass
class Person:
    """Person data class."""

    name: str
    email: str
    extra: str = ""


PersonInfo = dict[str, Person]
SHEET = list[list[str]]
ROW = list[str]
EMAILS = set[str]
ERR = str


def get_next_saturday_datetime() -> str:
    """Generate the upcoming saturday in format "%d-%m".

    Returns
        str: format "%d-%m" for the saturday to come
    """
    today = date.today()
    saturday = today + timedelta((5 - today.weekday()) % 7)
    return saturday.strftime("%d-%m")


class Notification(ABC):
    """Represent the abstract base class for Notifications."""

    @abstractmethod
    def send_message(self) -> None:
        """Send the message."""

    @abstractmethod
    def admin_message(self, body: str) -> None:
        """Generate a message for the admin."""

    @abstractmethod
    def generate_message(
        self,
        mail_to: EMAILS,
        subject: str,
        body: str,
        bcc: str,
    ) -> None:
        """Generate the message."""

    @abstractmethod
    def standard_message(self, names: list[str], emails: EMAILS) -> None:
        """Generate a standard message."""


class EmailNotification(Notification):
    """Class to send out an email notification."""

    message: EmailMessage

    def __init__(self) -> None:
        """Init EmailNotification."""
        self.email_on: bool = config("EMAIL_ON", default=False, cast=bool)
        self.smtp_srv: str = config("SMTP_SRV")
        self.smtp_port: int = config("SMTP_PORT", default=465, cast=int)
        self.smtp_usr: str = config("SMTP_USR")
        self.smtp_pwd: str = config("SMTP_PWD")
        self.reply_to: str = config("REPLY_TO")

    def send_message(self) -> None:
        """Send the email."""
        if not self.email_on:
            pprint(self.message)
            return

        # Create a secure SSL context
        context = ssl.create_default_context()

        try:
            with smtplib.SMTP_SSL(self.smtp_srv, self.smtp_port, context=context) as server:
                server.ehlo()  # Can be omitted
                server.login(self.smtp_usr, self.smtp_pwd)
                server.send_message(self.message)
        except smtplib.SMTPException as err:
            raise SendMailError from err

    def admin_message(self, body: str) -> None:
        """Create an admin email message.

        Args:
            body (str): The body content of the message
        """
        subject = "Groen email script issue"
        admin_address = config("ADM_EMAIL")
        self.generate_message(mail_to=admin_address, subject=subject, body=body)

    def generate_message(
        self,
        mail_to: EMAILS,
        subject: str,
        body: str,
        bcc: str = "",
    ) -> None:
        """Create the base for the email message.

        Args:
            mail_to (EMAILS): A set of email addresses
            subject (str): Subject of the message
            body (str): The body content of the message
            bcc (str, optional): BCC email addresses. Defaults to "".
        """
        msg = EmailMessage()
        msg["From"] = self.smtp_usr
        msg["Reply-to"] = self.reply_to
        msg["To"] = mail_to
        msg["Bcc"] = bcc
        msg["Subject"] = subject
        msg.set_content(body)
        self.message = msg

    def standard_message(self, names: list[str], emails: EMAILS) -> None:
        """Create a standard email message.

        Args:
            names (list[str]): Names to address the text to
            emails (EMAILS): a set of email addresses to send the mail to
        """
        subject = f"Groen onderhoud herinnering voor {get_next_saturday_datetime()}"
        body = (
            f"Beste {', '.join(names)},\n\n"
            "Voor aanstaand weekend sta je aangemeld voor het onderhoud aan de binnentuin.\n"
            f"Via {config('GROEN_CONTACT')} ({config('GROEN_MOBIEL')}) kan het "
            "gereedschap geregeld worden.\n"
            "Stem het aub tijdig af zodat je niet voor een dichte deur staat.\n\n"
            "Mocht het onverhoopt niet door kunnen gaan, regel even iemand anders of "
            "laat het de groencommissie even weten.\n\n"
            f"Stuur een antwoord naar email: {config('REPLY_TO')}\n"
        )
        self.generate_message(mail_to=emails, subject=subject, body=body, bcc=config("ADM_EMAIL"))


class GSheet:  # pylint: disable=too-few-public-methods
    """Defining the superclass to extract data from a Google Sheet."""

    sheet: SHEET
    notification: Notification
    sheet_id: str
    sheet_range: str

    def __init__(self, credentials: Credentials, notification: Notification):
        """Initialize Gsheet base class.

        Args:
            credentials (Credentials): Google credentials
            notification (Notification): Notification type class
        """
        self.credentials = credentials
        self.notification = notification

    def get_sheet(self):
        """Extract the contents of a Google Sheet."""
        service = discovery.build(
            serviceName="sheets",
            version="v4",
            credentials=self.credentials,
            num_retries=3,
        )
        sheet = service.spreadsheets()  # pylint: disable=no-member
        values = sheet.values()
        spreadsheet = values.get(spreadsheetId=self.sheet_id, range=self.sheet_range)
        result = spreadsheet.execute()
        self.sheet = result.get("values", [])


class Contacts(GSheet):
    """Class to extract and use contact data."""

    def __init__(self, credentials: Credentials, notification: Notification):
        """Initialize Contacts class.

        Args:
            credentials (Credentials): Google credentials
            notification (Notification): Notification type class
        """
        self.contacts_name_email: PersonInfo = {}
        self.mailing_list: EMAILS = set()
        self.sheet_id = config("CONTACTS_SHEET_ID")
        self.sheet_range = f"contacts!{config('CONTACTS_SHEET_RANGE')}"
        super().__init__(credentials, notification)

    def get_contact_name_email(self):
        """Extract contacts information."""
        name_mail_dict = {}

        for line in self.sheet:
            if len(line) == 4:
                name, email, _, extra_namen = line
            elif len(line) == 3:
                extra_namen = ""
                name, email, _ = line
            else:
                pprint(f"Could not process line: {line}")
                continue

            name_mail_dict[name] = Person(name=name, email=email, extra=extra_namen)
        self.contacts_name_email = name_mail_dict

    def generate_mailing_list(self, names: list[str]) -> EMAILS:
        """Generate the mailing list using the contact data.

        Args:
            names (list[str]): The email address is searched based on the provided names

        Returns:
            EMAILS (set[str]): a set of email addresses
        """
        for name in names:
            if name:
                self.mailing_list = self.mailing_list.union(
                    self._find_email_based_on_name_list(name, self.contacts_name_email)
                )
        return self.mailing_list

    def _find_email_based_on_name_list(self, name: str, contacts: PersonInfo) -> EMAILS:
        """Given the contact_dict find the email address based on the name field.

        If not found, the 'extra' field is used.

        Args:
            name (str): Persons name
            contacts: (PersonInfo): Dict of names (str and Person dataclass

        Returns:
            EMAILS (set[str]): a set of email addresses
        """
        name = name.lower()

        email_list = [data.email for key, data in contacts.items() if key.lower().startswith(name)]

        if not email_list:
            for data in contacts.values():
                regex = re.compile(pattern=r"\b{name}\b", flags=re.IGNORECASE)
                if data.extra and regex.search(data.extra):
                    email_list.append(data.email)

        if email_list:
            return set(email_list)

        msg = f"Action Bart.\nName: {name!r} not found in contacts."
        self.notification.admin_message(msg)
        self.notification.send_message()
        return set()


class ScheduleSheet(GSheet):
    """Class to extract and use planning data."""

    def __init__(self, credentials: Credentials, notification: Notification):
        """Initialize ScheduleSheet class.

        Args:
            credentials (Credentials): Google credentials
            notification (Notification): Notification type class
        """
        self.sheet_id = config("SCHEMA_SHEET_ID")
        self.sheet_range = f"{date.today().year}!{config('SCHEMA_SHEET_RANGE')}"
        self.short_date = get_next_saturday_datetime()
        super().__init__(credentials, notification)

    def _get_sheet_row(self) -> tuple[ROW, bool]:
        """Get the desired row within the sheet.

        Returns:
            tuple[ROW, bool]: the row data and a success result.
        """
        return next(
            ((line, True) for line in self.sheet if line[0] == self.short_date),
            ([""], False),
        )

    def _get_sheet_row_names(self, row: ROW) -> str:
        """Get the names from the row.

        Args:
            row (ROW): row data as list[str]

        Returns:
            str: Extracted names
        """
        index = 5
        try:
            return row[index]
        except IndexError:
            self.notification.admin_message(f"Names information not found in sheet. row: {row}")
        except TypeError:
            self.notification.admin_message(f"TypeError:\nrow: {row}\nindex: {index}")
        self.notification.send_message()
        return ""

    @staticmethod
    def _get_names_list(names: str) -> list[str]:
        """Extract the names from the string.

        Args:
            names (str): Provide the names

        Returns:
            list[str]: list of names
        """
        split_names = re.split(pattern=r",| en |/|\.", string=names)
        return [name.strip() for name in split_names if name]

    def names_next_date(self) -> tuple[list[str], ERR]:
        """Extract the names for the upcoming date.

        Returns:
            tuple[list[str], ERR]: list of names and the error state
        """
        row, date_found = self._get_sheet_row()
        if not date_found:
            return [], ""

        if names := self._get_sheet_row_names(row):
            return self._get_names_list(names), ""

        # Should send admin email
        return [], "No names found."


def main() -> None:
    """Call main function."""
    base_path = os.path.dirname(os.path.abspath(__file__))
    credentials_file = os.path.join(base_path, "credentials.json")
    scopes = [
        "https://www.googleapis.com/auth/contacts.readonly",
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    ]
    credentials = service_account.Credentials.from_service_account_file(
        credentials_file, scopes=scopes
    )
    notify = EmailNotification()
    schedule_sheet = ScheduleSheet(credentials=credentials, notification=notify)
    schedule_sheet.get_sheet()
    names, err = schedule_sheet.names_next_date()
    if err:
        notify.admin_message(err)
        notify.send_message()
        return

    # continue matching it with the contact information
    contacts = Contacts(credentials=credentials, notification=notify)
    contacts.get_sheet()
    contacts.get_contact_name_email()
    mailing_list = contacts.generate_mailing_list(names)

    notify.standard_message(names=names, emails=mailing_list)
    notify.send_message()


if __name__ == "__main__":
    main()
