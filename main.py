#!/usr/bin/env python3
"""Main execution script."""
import os

from google.oauth2 import service_account

from mail_groene_maaiers.groene_maaiers import (
    Contacts,
    EmailNotification,
    ScheduleSheet,
)


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
    if schedule_sheet.date_not_found:
        return
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
