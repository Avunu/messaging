# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

"""Twilio: the inbound webhook (a signed request, no network) and outbound sending (Client mocked)."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, cast
from unittest.mock import MagicMock, patch

import frappe
from frappe.core.doctype.communication.communication import Communication
from frappe.tests.classes import IntegrationTestCase
from twilio.base.exceptions import TwilioRestException
from twilio.request_validator import RequestValidator
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from messaging.messaging.api import twilio_sms, twilio_webhook
from messaging.tests.utils import make_contact, messaging_settings, unique_phone

TOKEN = "test-auth-token"
URL = "https://messaging.example.com/api/method/messaging.messaging.api.twilio_webhook.sms"


@contextmanager
def twilio_request(
	params: dict[str, str], signature: str | None = None, method: str = "POST"
) -> Generator[None]:
	"""Make frappe.request the POST Twilio would send, signed with TOKEN unless told otherwise."""
	if signature is None:
		signature = RequestValidator(TOKEN).compute_signature(URL, params)
	environ = EnvironBuilder(
		method=method,
		base_url="http://messaging.example.com",
		path="/api/method/messaging.messaging.api.twilio_webhook.sms",
		data=params,
		headers=[("X-Twilio-Signature", signature), ("Cf-Visitor", '{"scheme":"https"}')],
	).get_environ()
	old = getattr(frappe.local, "request", None)
	frappe.local.request = Request(environ)
	try:
		yield
	finally:
		frappe.local.request = old


class TestWebhook(IntegrationTestCase):
	def setUp(self) -> None:
		frappe.set_user("Guest")
		self.phone = unique_phone()

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def params(self, body: str = "Running late") -> dict[str, str]:
		return {
			"From": self.phone,
			"To": "+12025550000",
			"Body": body,
			"MessageSid": f"SM{frappe.generate_hash()}",
		}

	def test_a_signed_message_becomes_a_received_communication(self) -> None:
		frappe.set_user("Administrator")
		contact = make_contact(phone=self.phone)
		frappe.set_user("Guest")
		params = self.params()
		with messaging_settings(twilio_auth_token=TOKEN), twilio_request(params):
			self.assertIsNone(twilio_webhook.sms())
		self.assertEqual(frappe.response.http_status_code, 204)
		comm = cast(
			Communication,
			frappe.get_doc(
				"Communication",
				str(frappe.db.get_value("Communication", {"message_id": params["MessageSid"]})),
			),
		)
		self.assertEqual(
			(comm.phone_no, comm.sent_or_received, comm.status), (self.phone, "Received", "Open")
		)
		self.assertEqual(comm.sender_full_name, contact.full_name)

	def test_a_bad_signature_is_refused(self) -> None:
		with (
			messaging_settings(twilio_auth_token=TOKEN),
			twilio_request(self.params(), signature="forged"),
			self.assertRaises(frappe.ValidationError),
		):
			twilio_webhook.sms()

	def test_without_a_token_nothing_is_accepted(self) -> None:
		frappe.db.delete("__Auth", {"doctype": "Messaging Settings", "fieldname": "twilio_auth_token"})
		with twilio_request(self.params()), self.assertRaises(frappe.ValidationError):
			twilio_webhook.sms()

	def test_a_get_is_refused(self) -> None:
		with twilio_request(self.params(), method="GET"), self.assertRaises(frappe.ValidationError):
			twilio_webhook.sms()

	def test_stop_and_start_change_the_contacts_consent(self) -> None:
		frappe.set_user("Administrator")
		contact = make_contact(phone=self.phone, consent_sms=1)
		frappe.set_user("Guest")
		with messaging_settings(twilio_auth_token=TOKEN):
			with twilio_request(self.params(" stop ")):
				twilio_webhook.sms()
			self.assertEqual(
				frappe.db.get_value("Contact", contact.name, ["consent_sms", "unsubscribed"]), (0, 1)
			)
			with twilio_request(self.params("Start")):
				twilio_webhook.sms()
			self.assertEqual(
				frappe.db.get_value("Contact", contact.name, ["consent_sms", "unsubscribed"]), (1, 0)
			)
		comments = frappe.get_all(
			"Comment", filters={"reference_name": contact.name, "comment_type": "Info"}, pluck="content"
		)
		self.assertEqual(len(comments), 2)


def twilio_error(code: int) -> TwilioRestException:
	return TwilioRestException(status=400, uri="/Messages", msg=f"error {code}", code=code)


class TestSendSms(IntegrationTestCase):
	def setUp(self) -> None:
		frappe.set_user("Administrator")

	def tearDown(self) -> None:
		frappe.db.rollback()

	@contextmanager
	def twilio(self, create: Any) -> Generator[MagicMock]:
		client = MagicMock()
		client.messages.create.side_effect = create
		with (
			messaging_settings(
				send_via_twilio=1,
				twilio_account_sid="AC123",
				twilio_auth_token=TOKEN,
				twilio_phone_no="+12025550000",
			),
			patch.object(twilio_sms, "Client", return_value=client),
		):
			yield client

	def test_each_number_is_sent_and_logged(self) -> None:
		numbers = [unique_phone(), unique_phone()]
		with (
			self.twilio(lambda **kw: MagicMock(sid=f"SM-{kw['to']}")) as client,
			patch("frappe.msgprint") as msgprint,
		):
			result = twilio_sms.send_sms(frappe.as_json(numbers), "Hello")
		self.assertEqual(result, {"success": numbers, "errors": []})
		self.assertEqual(client.messages.create.call_args.kwargs["from_"], "+12025550000")
		msgprint.assert_called_once()
		log = frappe.get_last_doc("SMS Log")
		self.assertEqual((log.no_of_requested_sms, log.no_of_sent_sms), (2, 2))

	def test_twilio_errors_correct_the_contact(self) -> None:
		unsubscribed, invalid, unreachable, other, crashed = (unique_phone() for _ in range(5))
		contact = make_contact(phone=unsubscribed, consent_sms=1)
		bad = make_contact(phone=invalid)
		errors = {
			unsubscribed: twilio_error(twilio_sms.UNSUBSCRIBED_RECIPIENT),
			invalid: twilio_error(twilio_sms.INVALID_TO_NUMBER),
			unreachable: twilio_error(twilio_sms.UNREACHABLE_HANDSET),
			other: twilio_error(99999),
			crashed: RuntimeError("socket closed"),
		}

		def create(**kw: Any) -> Any:
			raise errors[kw["to"]]

		with self.twilio(create), patch("frappe.log_error") as log_error:
			result = twilio_sms.send_sms(list(errors), "Hello", success_msg=False)

		self.assertEqual(result["success"], [])
		self.assertEqual([e["code"] for e in result["errors"]], [21610, 21211, 30003, 99999, None])
		self.assertEqual(frappe.db.get_value("Contact", contact.name, "consent_sms"), 0)
		self.assertEqual(frappe.db.get_value("Contact Phone", {"parent": bad.name}, "is_valid"), 0)
		self.assertEqual(log_error.call_count, 5)

	def test_an_unsubscribe_without_a_contact_is_logged(self) -> None:
		with patch("frappe.log_error") as log_error:
			twilio_sms.handle_twilio_error(twilio_error(twilio_sms.UNSUBSCRIBED_RECIPIENT), unique_phone())
		log_error.assert_called_once()

	def test_missing_credentials_are_reported(self) -> None:
		with (
			messaging_settings(send_via_twilio=1, twilio_account_sid=None, twilio_phone_no=None),
			self.assertRaises(frappe.ValidationError),
		):
			twilio_sms.send_sms([unique_phone()], "Hello")

	def test_without_twilio_the_core_gateway_is_used(self) -> None:
		number = unique_phone()
		with messaging_settings(send_via_twilio=0):
			with patch("frappe.msgprint") as msgprint:
				self.assertEqual(twilio_sms.send_sms([number], "Hello"), {"success": [], "errors": []})
			msgprint.assert_called_once()

			frappe.db.set_single_value("SMS Settings", "sms_gateway_url", "https://sms.example.com/send")
			with patch("frappe.core.doctype.sms_settings.sms_settings.send_via_gateway") as gateway:
				result = twilio_sms.send_sms([number], "Hello")
			self.assertEqual(result, {"success": [number], "errors": []})
			self.assertEqual(gateway.call_args.args[0]["receiver_list"], [number])
