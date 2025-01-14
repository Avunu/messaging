import frappe
from frappe import _
import phonenumbers
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

def validate(doc, method=None):
    settings = frappe.get_doc("Messaging Settings")
    country = ""
    if doc.address:
        country = frappe.get_value("Address", doc.address, "country")
    if not country:
        country = frappe.db.get_single_value("System Settings", "country")
    country_code = frappe.get_value("Country", country, "code").upper()

    # Only proceed with Twilio validation if enabled in settings
    validate_numbers = settings.enable_number_validation and settings.twilio_account_sid and settings.twilio_auth_token

    if validate_numbers:
        client = Client(settings.twilio_account_sid, settings.get_password("twilio_auth_token"))

    # convert all phone numbers to E.164 format and validate if enabled
    for phone_entry in doc.phone_nos:
        try:
            no = phonenumbers.parse(phone_entry.phone, country_code)
            phone_entry.phone = phonenumbers.format_number(no, phonenumbers.PhoneNumberFormat.E164)
            
            # Only validate mobile numbers with Twilio
            if validate_numbers and phone_entry.is_primary_mobile_no:
                try:
                    lookup = client.lookups.v2.phone_numbers(phone_entry.phone).fetch(fields=['line_type_intelligence'])
                    # debug
                    frappe.log_error("Twilio line_type_intelligence", lookup.line_type_intelligence)
                    phone_entry.is_valid_mobile = lookup.line_type_intelligence.get("type", "") in ['mobile']
                    phone_entry.carrier_type = lookup.line_type_intelligence.get("type", "")
                except TwilioRestException as e:
                    if e.code == 20404:  # Number not found
                        phone_entry.is_valid_mobile = 0
                    else:
                        frappe.log_error(f"Twilio Lookup Error: {str(e)}")
                except Exception as e:
                    frappe.log_error(f"Phone validation error: {str(e)}")
        except:
            frappe.throw(_("Invalid phone number: {0}").format(phone_entry.phone))