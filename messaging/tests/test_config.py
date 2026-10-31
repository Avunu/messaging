# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

"""The install, migrate and uninstall hooks: the Chat view option and the app's property setters."""

import frappe
from frappe.custom.doctype.customize_form.customize_form import reset_customization
from frappe.tests.classes import IntegrationTestCase

from messaging import config


def options(doctype: str, fieldname: str) -> list[str]:
	"""The field's options as its property setter has them (DocType's own meta comes from its file)."""
	value = frappe.db.get_value(
		"Property Setter", {"doc_type": doctype, "field_name": fieldname, "property": "options"}, "value"
	)
	return str(value or "").split("\n")


def setter(doctype: str, fieldname: str | None, prop: str) -> frappe._dict | None:
	return frappe.db.get_value(
		"Property Setter",
		{"doc_type": doctype, "field_name": fieldname or ("is", "not set"), "property": prop},
		["name", "value", "is_system_generated"],
		as_dict=True,
	)


class TestConfig(IntegrationTestCase):
	def tearDown(self) -> None:
		frappe.db.rollback()
		frappe.clear_cache()

	def test_install_and_migrate_offer_the_chat_view(self) -> None:
		config.after_install()
		config.after_migrate()
		self.assertIn("Chat", options("DocType", "default_view"))
		self.assertIn("Chat", options("Workspace Shortcut", "doc_view"))

	def test_the_property_setters_are_made_once_and_survive_a_reset(self) -> None:
		config.after_migrate()
		for doctype, fieldname, prop, value, _type in config.PROPERTY_SETTERS:
			ps = setter(doctype, fieldname, prop)
			assert ps is not None, (doctype, fieldname, prop)
			self.assertEqual((ps.value or "", ps.is_system_generated), (value, 1))
		self.assertEqual(frappe.get_meta("Communication").default_view, "Chat")
		self.assertEqual(frappe.get_meta("Newsletter").get_field("newsletter_content").hide_border, 1)

		before = setter("Communication", "subject", "read_only")
		config.ensure_property_setters()
		self.assertEqual(setter("Communication", "subject", "read_only"), before)

		reset_customization("Communication")
		self.assertEqual(setter("Communication", "subject", "read_only"), before)

	def test_a_changed_setter_is_set_back(self) -> None:
		config.ensure_property_setters()
		ps = setter("Communication", "cc", "length")
		assert ps is not None
		frappe.db.set_value("Property Setter", ps.name, {"value": "50", "is_system_generated": 0})
		config.ensure_property_setters()
		after = setter("Communication", "cc", "length")
		assert after is not None
		self.assertEqual(after.value, "1000")

	def test_uninstall_removes_the_chat_view(self) -> None:
		config.after_install()
		config.after_uninstall()
		self.assertNotIn("Chat", options("DocType", "default_view"))
		config.after_install()
