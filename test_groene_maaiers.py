import pytest
import os
import groene_maaiers as gm


contacts = {
    'Name1 LastName1': {
        'name': 'Name1 LastName1',
        'email': 'name1.lastname1@domain.nl',
        'notes': None,
        'phone': None
    },
    'Name2 LastName2': {
        'name': 'Name2 LastName2',
        'email': 'name2.lastname2@domain.nl',
        'notes': None,
        'phone': None
    },
    'Name3 LastName3': {
        'name': 'Name3 LastName3',
        'email': 'name3.lastname3@domain.nl',
        'notes': None,
        'phone': None
    }
}

os.environ['SMTP_USR'] = 'testuser@domain.nl'
os.environ['SMTP_PORT'] = '465'
os.environ['SMTP_SRV'] = 'smtp.gmail.com'
os.environ['SMTP_PWD'] = 'boguspassword'
os.environ['ADM_EMAIL'] = 'admin@domain.nl'
os.environ['GROEN_CONTACT'] = 'groencontact'
os.environ['GROEN_MOBIEL'] = 'groenmobiel'
os.environ['EMAIL_ON'] = 'False'

def test_extract_contacts_info():
    contacts_gmail = [
        {
            'names': [
                {
                    'displayName': 'Name1 LastName1',
                }
            ],
            'emailAddresses': [
                {
                    'value': 'name1.lastname1@domain.nl',
                }
            ]
        },
        {
            'names': [
                {
                    'displayName': 'Name2 LastName2',
                }
            ],
            'emailAddresses': [
                {
                    'value': 'name2.lastname2@domain.nl',
                }
            ]
        },
        {
            'names': [
                {
                    'displayName': 'Name3 LastName3',
                }
            ],
            'emailAddresses': [
                {
                    'value': 'name3.lastname3@domain.nl',
                }
            ]
        },
    ]
    c = gm.extract_contacts_info(contacts_gmail)
    assert c == contacts


def test_get_sheet_row():
    sheet_list = [
        ['Datum', 'Activiteit', '', '', 'Namen', 'Emails'],
        ['', 'Grasmaaien + kanten', 'Onkruid wieden', 'Groot onderhoud*'],
        ['29-05', 'x', '  ', '', '2 bewoners', 'Name4, Name5 '],
        ['05-06', 'x', 'x', '', '2 bewoners', 'Name6, Name7'],
        ['12-06', 'x', '', '', '2 bewoners']
    ]
    s = gm.get_sheet_row(sheet_list=sheet_list, short_date='29-05')
    expected = ['29-05', 'x', '  ', '', '2 bewoners', 'Name4, Name5 ']
    assert expected == s
    s = gm.get_sheet_row(sheet_list=sheet_list, short_date='05-06')
    expected = ['05-06', 'x', 'x', '', '2 bewoners', 'Name6, Name7']
    assert expected == s
    s = gm.get_sheet_row(sheet_list=sheet_list, short_date='12-06')
    expected = ['12-06', 'x', '', '', '2 bewoners']
    assert expected == s


def test_get_sheet_row_names():
    a = ['29-05', 'x', '  ', '', '2 bewoners', 'Name4, Name5 ']
    b = ['05-06', 'x', 'x', '', '2 bewoners', 'Name6, Name7']
    c = ['12-06', 'x', '', '', '2 bewoners']
    s = gm.get_sheet_row_names(a)
    expected = 'Name4, Name5 '
    assert s == expected
    s = gm.get_sheet_row_names(b)
    expected = 'Name6, Name7'
    assert s == expected
    s = gm.get_sheet_row_names(c)
    assert s is None


def test_find_email_based_on_name_list():
    s = gm.find_email_based_on_name_list(name='Name1', contact_dict=contacts)
    expected = 'name1.lastname1@domain.nl'
    assert s == expected
    s = gm.find_email_based_on_name_list(name='Name2', contact_dict=contacts)
    expected = 'name2.lastname2@domain.nl'
    assert s == expected
    s = gm.find_email_based_on_name_list(name='Name3', contact_dict=contacts)
    expected = 'name3.lastname3@domain.nl'
    assert s == expected
    s = gm.find_email_based_on_name_list(name='Unknown', contact_dict=contacts)
    expected = None
    assert s is expected


def test_standard_email_message():
    groen_contact = 'GROEN_CONTACT'
    groen_mobiel = 'GROEN_MOBIEL'
    smtp_usr = 'from@domain.nl'
    os.environ['SMTP_USR'] = smtp_usr
    os.environ[groen_contact] = groen_contact
    os.environ[groen_mobiel] = groen_mobiel
    os.environ['ADM_EMAIL'] = 'adm@domain.nl'

    names = ('name1', 'name2')
    emails = ('to@domain.nl', 'to2@domain.nl')
    subject = "Groen onderhoud herinnering voor %s" % gm.get_next_saturday_datetime()
    body = f"Beste {', '.join(names)},\n\n" \
           "Voor aanstaand weekend sta je aangemeld voor het onderhoud aan de binnentuin.\n" \
           f"Via {groen_contact} ({groen_mobiel}) kan het gereedschap " \
           "geregeld worden.\n\n" \
           "Mocht het onverhoopt niet door kunnen gaan, laat het de groencommissie even weten." \
           "\n\n" \
           f"email: {smtp_usr}\n"
    mail_message = gm.standard_email_message(names, emails)
    mail_dict = {k: v for k, v in mail_message.items()}

    assert mail_dict['From'] == 'from@domain.nl'
    assert mail_dict['To'] == ', '.join(emails)
    assert mail_dict['Subject'] == subject
    assert mail_message.get_content() == body


def test_admin_email_message():
    os.environ['SMTP_USR'] = 'from@domain.nl'
    os.environ['ADM_EMAIL'] = 'to@domain.nl'
    subject = 'Groen email script issue'
    body = 'body'
    mail_message = gm.admin_email_message(body)
    mail_dict = {k: v for k, v in mail_message.items()}

    assert mail_dict['From'] == 'from@domain.nl'
    assert mail_dict['To'] == 'to@domain.nl'
    assert mail_dict['Subject'] == subject
    assert mail_message.get_content().strip('\n') == body


def test_make_mail_message():
    base_test = {
        'mail_from': 'from@domain.nl',
        'mail_to': 'to@domain.nl',
        'subject': 'subject',
        'body': 'body'
    }
    mail_message = gm.make_mail_message(**base_test)
    mail_dict = {k: v for k, v in mail_message.items()}

    assert mail_dict['From'] == base_test['mail_from']
    assert mail_dict['To'] == base_test['mail_to']
    assert mail_dict['Subject'] == base_test['subject']
    assert mail_message.get_content().strip('\n') == base_test['body']

    base_test['mail_cc'] = 'cc@domain.nl'
    base_test['mail_bcc'] = 'bcc@domain.nl'
    mail_message = gm.make_mail_message(**base_test)
    mail_dict = {k: v for k, v in mail_message.items()}

    assert mail_dict['Cc'] == base_test['mail_cc']
    assert mail_dict['Bcc'] == base_test['mail_bcc']
