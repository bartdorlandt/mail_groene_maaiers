import os

import pytest

import groene_maaiers as gm

contacts = {
    "Name1 LastName1": {
        "name": "Name1 LastName1",
        "email": "name1.lastname1@domain.nl",
        "extra": "other name",
    },
    "Name2 LastName2": {
        "name": "Name2 LastName2",
        "email": "name2.lastname2@domain.nl",
        "extra": "",
    },
    "Name3 LastName3": {
        "name": "Name3 LastName3",
        "email": "name3.lastname3@domain.nl",
        "extra": "Name2 LastName2",
    },
}


@pytest.fixture(autouse=True)
def set_os_environment():
    os.environ["SMTP_USR"] = "testuser@domain.nl"
    os.environ["REPLY_TO"] = "testfrom@domain.nl"
    os.environ["SMTP_PORT"] = "465"
    os.environ["SMTP_SRV"] = "smtp.gmail.com"
    os.environ["SMTP_PWD"] = "boguspassword"
    os.environ["ADM_EMAIL"] = "admin@domain.nl"
    os.environ["GROEN_CONTACT"] = "groencontact"
    os.environ["GROEN_MOBIEL"] = "groenmobiel"
    os.environ["EMAIL_ON"] = "False"


def test_extract_contacts_info():
    contacts_gmail = [
        ["Name1 LastName1", "name1.lastname1@domain.nl", "adres 1", "other name"],
        ["Name2 LastName2", "name2.lastname2@domain.nl", "adres 5"],
        ["Name3 LastName3", "name3.lastname3@domain.nl", "adres 7", "Name2 LastName2"],
    ]
    c = gm.extract_contacts_info(contacts_gmail)
    assert c == contacts


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("29-05", ["29-05", "x", "  ", "", "2 bewoners", "Name4, Name5 "]),
        ("05-06", ["05-06", "x", "x", "", "2 bewoners", "Name6 en Name7"]),
        ("12-06", ["12-06", "x", "", "", "2 bewoners"]),
    ],
)
def test_get_sheet_row(test_input, expected):
    sheet_list = [
        ["Datum", "Activiteit", "", "", "Namen", "Emails"],
        ["", "Grasmaaien + kanten", "Onkruid wieden", "Groot onderhoud*"],
        ["29-05", "x", "  ", "", "2 bewoners", "Name4, Name5 "],
        ["05-06", "x", "x", "", "2 bewoners", "Name6 en Name7"],
        ["12-06", "x", "", "", "2 bewoners"],
    ]
    s, _ = gm.get_sheet_row(sheet_list=sheet_list, short_date=test_input)
    assert s == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (["29-05", "x", "  ", "", "2 bewoners", "Name4, Name5 "], "Name4, Name5 "),
        (["05-06", "x", "x", "", "2 bewoners", "Name6 en Name7"], "Name6 en Name7"),
        (["12-06", "x", "", "", "2 bewoners"], ""),
    ],
)
def test_get_sheet_row_names(test_input, expected):
    s = gm.get_sheet_row_names(test_input)
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
def test_get_names_list(test_input, expected):
    assert gm.get_names_list(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("Name1", {"name1.lastname1@domain.nl"}),
        ("Name2", {"name2.lastname2@domain.nl"}),
        ("Name3", {"name3.lastname3@domain.nl"}),
        # ("Name4", None),
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
def test_find_email_based_on_name_list(test_input, expected):
    s = gm.find_email_based_on_name_list(name=test_input, contact_dict=contacts)
    assert s == expected


def test_standard_email_message():
    groen_contact = "GROEN_CONTACT"
    groen_mobiel = "GROEN_MOBIEL"
    smtp_usr = "from@domain.nl"
    os.environ["SMTP_USR"] = smtp_usr
    os.environ[groen_contact] = groen_contact
    os.environ[groen_mobiel] = groen_mobiel
    os.environ["ADM_EMAIL"] = "adm@domain.nl"

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
    mail_message = gm.standard_email_message(names, emails)
    mail_dict = dict(mail_message.items())

    assert mail_dict["From"] == smtp_usr
    assert mail_dict["To"] == ", ".join(emails)
    assert mail_dict["Subject"] == subject
    assert mail_message.get_content() == body


def test_admin_email_message():
    os.environ["SMTP_USR"] = "from@domain.nl"
    os.environ["ADM_EMAIL"] = "to@domain.nl"
    subject = "Groen email script issue"
    body = "body"
    mail_message = gm.admin_email_message(body)
    mail_dict = dict(mail_message.items())

    assert mail_dict["From"] == "from@domain.nl"
    assert mail_dict["To"] == "to@domain.nl"
    assert mail_dict["Subject"] == subject
    assert mail_message.get_content().strip("\n") == body


def test_make_mail_message():
    base_test = {
        "mail_from": os.environ["SMTP_USR"],
        "mail_to": "to@domain.nl",
        "subject": "subject",
        "body": "body",
        "reply_to": os.environ["REPLY_TO"],
    }
    mail_message = gm.make_mail_message(**base_test)
    mail_dict = dict(mail_message.items())

    assert mail_dict["From"] == base_test["mail_from"]
    assert mail_dict["To"] == base_test["mail_to"]
    assert mail_dict["Subject"] == base_test["subject"]
    assert mail_dict["Reply-to"] == os.environ["REPLY_TO"]
    assert mail_message.get_content().strip("\n") == base_test["body"]

    base_test["cc"] = "cc@domain.nl"
    base_test["bcc"] = "bcc@domain.nl"
    mail_message = gm.make_mail_message(**base_test)
    mail_dict = dict(mail_message.items())

    assert mail_dict["Cc"] == base_test["cc"]
    assert mail_dict["Bcc"] == base_test["bcc"]
    assert mail_dict["Reply-to"] == os.environ["REPLY_TO"]
