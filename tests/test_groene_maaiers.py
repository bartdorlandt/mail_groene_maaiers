"""pytest groene_maaiers."""
import json
import os

import pytest

import mail_groene_maaiers.groene_maaiers as gm


@pytest.fixture
def notify():
    class Notification:
        @staticmethod
        def admin_message(msg):
            pass

        @staticmethod
        def send_message():
            pass

    return Notification()


@pytest.fixture
def expected_contacts() -> dict[str, gm.Person]:
    return {
        "Name1 LastName1": gm.Person(
            name="Name1 LastName1",
            email="name1.lastname1@domain.nl",
            extra="other name",
        ),
        "Name2 LastName2": gm.Person(
            name="Name2 LastName2", email="name2.lastname2@domain.nl", extra=""
        ),
        "Name3 LastName3": gm.Person(
            name="Name3 LastName3",
            email="name3.lastname3@domain.nl",
            extra="Name4 LastName4",
        ),
    }


@pytest.fixture(autouse=True)
def set_os_environment() -> None:
    os.environ["SMTP_USR"] = "testuser@domain.nl"
    os.environ["REPLY_TO"] = "testfrom@domain.nl"
    os.environ["SMTP_PORT"] = "465"
    os.environ["SMTP_SRV"] = "smtp.gmail.com"
    os.environ["SMTP_PWD"] = "boguspassword"
    os.environ["ADM_EMAIL"] = "admin@domain.nl"
    os.environ["GROEN_CONTACT"] = "groencontact"
    os.environ["GROEN_MOBIEL"] = "groenmobiel"
    os.environ["EMAIL_ON"] = "False"
    os.environ["CONTACTS_SHEET_ID"] = "SomeContactsSheetID"
    os.environ["CONTACTS_SHEET_RANGE"] = "2:40"
    os.environ["SCHEMA_SHEET_ID"] = "SomeSchemaSheetID"
    os.environ["SCHEMA_SHEET_RANGE"] = "3:27"


@pytest.fixture(scope="session")
def credentials(tmpdir_factory) -> str:
    creds = {
        "type": "service_account",
        "project_id": "mail-groene-maaiers",
        "private_key_id": "none",
        "private_key": "none\n",
        "client_email": "none",
        "client_id": "none",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/"
        "some.iam.gserviceaccount.com",
    }
    fp = tmpdir_factory.mktemp("data").join("creds.json")
    fp.write(json.dumps(creds))
    return fp.strpath


@pytest.fixture
def contacts(notify: gm.Notification, credentials: gm.Credentials):
    return gm.Contacts(credentials=credentials, notification=notify)


@pytest.fixture()
def schedule_sheet(notify: gm.Notification, credentials: gm.Credentials):
    return gm.ScheduleSheet(credentials=credentials, notification=notify)


@pytest.fixture
def notification_dict(set_os_environment) -> dict[str, str]:
    """Return a notification dictionary based on the OS environment variables."""
    return {
        "SMTP_USR": os.environ["SMTP_USR"],
        "ADM_EMAIL": os.environ["ADM_EMAIL"],
        "EMAIL_ON": os.environ["EMAIL_ON"],
        "SMTP_SRV": os.environ["SMTP_SRV"],
        "SMTP_PORT": os.environ["SMTP_PORT"],
        "SMTP_PWD": os.environ["SMTP_PWD"],
        "REPLY_TO": os.environ["REPLY_TO"],
    }


@pytest.fixture
def notification(notification_dict: dict[str, str]) -> gm.EmailNotification:
    g = gm.EmailNotification()
    for k, v in notification_dict.items():
        setattr(g, k.lower(), v)
    return g


def test_extract_contacts_info(contacts: gm.Contacts, expected_contacts: dict[str, gm.Person]):
    contacts_gmail = [
        ["Name1 LastName1", "name1.lastname1@domain.nl", "adres 1", "other name"],
        ["Name2 LastName2", "name2.lastname2@domain.nl", "adres 5"],
        ["Name3 LastName3", "name3.lastname3@domain.nl", "adres 7", "Name4 LastName4"],
    ]
    contacts.sheet = contacts_gmail
    contacts.get_contact_name_email()
    assert contacts.contacts_name_email == expected_contacts


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("29-05", ["29-05", "x", "  ", "", "2 bewoners", "Name4, Name5 "]),
        ("05-06", ["05-06", "x", "x", "", "2 bewoners", "Name6 en Name7"]),
        ("12-06", ["12-06", "x", "", "", "2 bewoners"]),
        ("14-06", [""]),
    ],
)
def test_get_sheet_row(test_input: str, expected: list[str], schedule_sheet: gm.ScheduleSheet):
    sheet_list = [
        ["Datum", "Activiteit", "", "", "Namen", "Emails"],
        ["", "Grasmaaien + kanten", "Onkruid wieden", "Groot onderhoud*"],
        ["29-05", "x", "  ", "", "2 bewoners", "Name4, Name5 "],
        ["05-06", "x", "x", "", "2 bewoners", "Name6 en Name7"],
        ["12-06", "x", "", "", "2 bewoners"],
    ]
    schedule_sheet.sheet = sheet_list
    schedule_sheet.short_date = test_input
    s, _ = schedule_sheet._get_sheet_row()
    assert s == expected


def test_names_next_date_date_not_found(schedule_sheet: gm.ScheduleSheet):
    sheet_list = [
        ["Datum", "Activiteit", "", "", "Namen", "Emails"],
        ["", "Grasmaaien + kanten", "Onkruid wieden", "Groot onderhoud*"],
        ["29-05", "x", "  ", "", "2 bewoners", "Name4, Name5 "],
        ["05-06", "x", "x", "", "2 bewoners", "Name6 en Name7"],
        ["12-06", "x", "", "", "2 bewoners"],
    ]
    date = "14-06"
    schedule_sheet.sheet = sheet_list
    schedule_sheet.short_date = date
    s, _ = schedule_sheet.names_next_date()
    assert schedule_sheet.date_not_found is True
    assert s == []


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (["29-05", "x", "  ", "", "2 bewoners", "Name4, Name5 "], "Name4, Name5 "),
        (["05-06", "x", "x", "", "2 bewoners", "Name6 en Name7"], "Name6 en Name7"),
        (["12-06", "x", "", "", "2 bewoners"], ""),
    ],
)
def test_get_sheet_row_names(
    test_input: list[str], expected: str, schedule_sheet: gm.ScheduleSheet
):
    s = schedule_sheet._get_sheet_row_names(test_input)
    assert s == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("Name4, Name5 ", ["Name4", "Name5"]),
        ("Name4 en Name5 ", ["Name4", "Name5"]),
        ("Name4. Name5 ", ["Name4", "Name5"]),
        ("Name1., Name2, Name3", ["Name1", "Name2", "Name3"]),
        ("Name4, Name5 en Name6 / Name7", ["Name4", "Name5", "Name6", "Name7"]),
    ],
)
def test_get_names_list(test_input: str, expected: list[str], schedule_sheet: gm.ScheduleSheet):
    s = schedule_sheet._get_names_list(test_input)
    assert s == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("Name1", {"name1.lastname1@domain.nl"}),
        ("Name2", {"name2.lastname2@domain.nl"}),
        ("Name3", {"name3.lastname3@domain.nl"}),
        ("Name4", {"name3.lastname3@domain.nl"}),
        (
            "Name",
            {
                "name1.lastname1@domain.nl",
                "name2.lastname2@domain.nl",
                "name3.lastname3@domain.nl",
            },
        ),
    ],
)
def test_find_email_based_on_name_list(
    test_input: str,
    expected: set[str],
    contacts: gm.Contacts,
    expected_contacts: dict[str, gm.Person],
):
    # contacts.contacts_name_email = expected_contacts
    s = contacts._find_email_based_on_name_list(name=test_input, contacts=expected_contacts)
    assert s == expected


def test_notifications(notification: gm.Notification, notification_dict: dict[str, str]):
    # sourcery skip: no-loop-in-tests
    for k in notification_dict:
        g = getattr(notification, k.lower())
        assert g == notification_dict[k]


def test_standard_email_message(notification: gm.EmailNotification):
    groen_contact = "groencontact"
    groen_mobiel = "groenmobiel"
    names = ["name1", "name2"]
    emails = {"to@domain.nl", "to2@domain.nl"}
    subject = f"Groen onderhoud herinnering voor {gm.get_next_saturday_datetime()}"
    body = (
        f"Beste {', '.join(names)},\n\n"
        "Voor aanstaand weekend sta je aangemeld voor het onderhoud aan de binnentuin.\n"
        f"Via {groen_contact} ({groen_mobiel}) kan het gereedschap "
        "geregeld worden.\n"
        "Stem het aub tijdig af zodat je niet voor een dichte deur staat.\n\n"
        "Mocht het onverhoopt niet door kunnen gaan, regel even iemand anders of "
        "laat het de groencommissie even weten."
        "\n\n"
        f"Stuur een antwoord naar email: {os.environ['REPLY_TO']}\n"
    )
    notification.standard_message(names, emails)
    mail_dict = dict(notification.message.items())

    assert mail_dict["To"] == ", ".join(emails)
    assert mail_dict["Subject"] == subject
    assert notification.message.get_content() == body


def test_admin_message(notification: gm.EmailNotification):
    subject = "Groen email script issue"
    body = "body"
    notification.admin_message(body)
    mail_dict = dict(notification.message.items())

    assert mail_dict["From"] == notification.smtp_usr
    assert mail_dict["To"] == notification.message["To"]
    assert mail_dict["Subject"] == subject
    assert notification.message.get_content().strip("\n") == body


def test_generate_message(notification: gm.EmailNotification):
    mail = "to@domain.nl"
    mail_to = {mail}
    subject = "subject"
    body = "body"
    notification.generate_message(mail_to=mail_to, subject=subject, body=body)
    mail_dict = dict(notification.message.items())

    assert mail_dict["From"] == os.environ["SMTP_USR"]
    assert mail_dict["To"] == mail
    assert mail_dict["Subject"] == subject
    assert mail_dict["Reply-to"] == os.environ["REPLY_TO"]
    assert notification.message.get_content().strip("\n") == body

    bcc = "bcc@domain.nl"
    notification.generate_message(mail_to=mail_to, subject=subject, body=body, bcc=bcc)
    mail_dict = dict(notification.message.items())

    assert mail_dict["Bcc"] == bcc
    assert mail_dict["Reply-to"] == os.environ["REPLY_TO"]
