import frappe
from frappe import _
import phonenumbers
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException


def validate(doc, method=None):
	settings = frappe.get_doc("Messaging Settings")
	country_code = get_country_code(doc)

	# Process and deduplicate email addresses
	deduplicate_emails(doc)

	# Process and deduplicate phone numbers
	deduplicate_phone_numbers(doc, country_code)

	# Only proceed with Twilio validation if enabled in settings
	validate_numbers = (
		settings.enable_number_validation
		and settings.twilio_account_sid
		and settings.twilio_auth_token
	)

	if validate_numbers:
		client = Client(
			settings.twilio_account_sid, settings.get_password("twilio_auth_token")
		)
		validate_phone_numbers(doc, client)

		set_primary_numbers(doc)


def deduplicate_emails(doc):
	seen_emails = {}
	to_remove = []

	for i, email_entry in enumerate(doc.email_ids):
		email = email_entry.email_id.lower().strip()
		if email in seen_emails:
			to_remove.append(i)
		else:
			seen_emails[email] = i
			email_entry.email_id = email

	for i in reversed(to_remove):
		doc.email_ids.pop(i)


def deduplicate_phone_numbers(doc, country_code):
	seen_numbers = {}
	to_remove = []

	for i, phone_entry in enumerate(doc.phone_nos):
		if not is_valid_E164_number(phone_entry.phone):
			e164_number = convert_to_e164(phone_entry.phone, country_code)
			if e164_number:
				phone_entry.phone = e164_number
			else:
				continue  # Skip invalid numbers

		if phone_entry.phone in seen_numbers:
			to_remove.append(i)
		else:
			seen_numbers[phone_entry.phone] = i

	for i in reversed(to_remove):
		doc.phone_nos.pop(i)


def validate_phone_numbers(doc, client):
	for phone_entry in doc.phone_nos:
		# Only validate if number changed or not yet validated
		if (
			not phone_entry.validated_number
			or phone_entry.validated_number != phone_entry.phone
		):

			phone_entry.is_valid, phone_entry.carrier_type = validate_number(
				phone_entry.phone, client
			)
			if phone_entry.is_valid:
				phone_entry.validated_number = phone_entry.phone
				if (
					phone_entry.is_primary_mobile_no
					and phone_entry.carrier_type != "mobile"
				):
					phone_entry.is_primary_mobile_no = 0
			else:
				phone_entry.validated_number = None
				phone_entry.carrier_type = ""


def set_primary_numbers(doc):
	valid_numbers = [p for p in doc.phone_nos if p.is_valid]
	if not valid_numbers:
		return

	# Handle primary phone
	current_primary = next((p for p in doc.phone_nos if p.is_primary_phone), None)
	if not current_primary or not current_primary.is_valid:
		# Reset all primary phone flags
		for phone in doc.phone_nos:
			phone.is_primary_phone = 0
		# Set first valid number as primary
		valid_numbers[0].is_primary_phone = 1

	# Handle primary mobile
	current_mobile = next((p for p in doc.phone_nos if p.is_primary_mobile_no), None)
	valid_mobiles = [p for p in valid_numbers if p.carrier_type == 'mobile']
	
	if current_mobile:
		if not current_mobile.is_valid or current_mobile.carrier_type != 'mobile':
			# Reset mobile flags if current primary is invalid/not mobile
			for phone in doc.phone_nos:
				phone.is_primary_mobile_no = 0
			# Set first valid mobile as primary if available
			if valid_mobiles:
				valid_mobiles[0].is_primary_mobile_no = 1
	elif valid_mobiles:  # No current primary mobile, but valid mobiles exist
		valid_mobiles[0].is_primary_mobile_no = 1


def get_country_code(doc):
	country = ""
	if doc.address:
		country = frappe.get_value("Address", doc.address, "country")
	if not country:
		country = frappe.db.get_single_value("System Settings", "country")
	country_code = frappe.get_value("Country", country, "code").upper()
	return country_code


def is_valid_E164_number(number):
	# if the number does not begin with a +, it is not E.164
	if not number.startswith("+"):
		return False
	try:
		numobj = phonenumbers.parse(number, "")
	except:
		return False
	if phonenumbers.is_valid_number(numobj):
		return (
			phonenumbers.format_number(numobj, phonenumbers.PhoneNumberFormat.E164)
			== number
		)
	return False


def convert_to_e164(number, country_code):
	if not number:
		return None
	try:
		numobj = phonenumbers.parse(number, country_code)
	except:
		return None
	if phonenumbers.is_valid_number(numobj):
		return phonenumbers.format_number(numobj, phonenumbers.PhoneNumberFormat.E164)
	return None


def validate_number(e164_number, client):
	is_valid = False
	carrier_type = ""
	try:
		lookup = client.lookups.v2.phone_numbers(e164_number).fetch(
			fields=["line_type_intelligence"]
		)
		carrier_type = str(lookup.get("line_type_intelligence",{}).get("type", ""))
		is_valid = len(carrier_type) > 0
	except TwilioRestException as e:
		if e.code == 20404:  # Number not found
			is_valid = 0
		else:
			frappe.log_error("Twilio Lookup Error", str(e))
	except Exception as e:
		frappe.log_error("Phone Validation Error", str(e))
	return is_valid, carrier_type
