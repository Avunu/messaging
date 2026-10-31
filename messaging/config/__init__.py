# Copyright (c) 2024, Avunu LLC and contributors
# For license information, please see license.txt

from typing import Any, cast

import frappe
from frappe.types import DF
from frappe.types.frappedict import _dict


class PropertySetterValue(_dict):
	"""Dict-like object for sales quote rule data that exposes keys as attributes"""

	name: DF.Data
	value: DF.SmallText

	def __init__(self, data: dict[str, Any] | None = None):
		super().__init__(data or {})


# DocType View for Chat audit trail
DOCVIEW = ["Chat"]

# The property setters the app owns, as (doctype, fieldname or None for the doctype itself,
# property, value, property type). They are made in code with frappe.make_property_setter, as
# frappe's own system customizations are, so they stay is_system_generated: Customize Form's
# "Reset to defaults" deletes only the setters a user made, and leaves these alone. A user's
# own change to one of these properties is replaced on the next migrate, as the customization
# files that held them used to do.
PROPERTY_SETTERS: list[tuple[str, str | None, str, str, str]] = [
	("Communication", None, "default_view", "Chat", "Data"),
	("Communication", "subject", "read_only", "1", "Check"),
	("Communication", "sender", "options", "", "Small Text"),
	("Communication", "recipients", "fieldtype", "Data", "Select"),
	("Communication", "recipients", "length", "512", "Int"),
	("Communication", "recipients", "options", "", "Small Text"),
	("Communication", "recipients", "read_only", "1", "Check"),
	("Communication", "cc", "fieldtype", "Data", "Select"),
	("Communication", "cc", "length", "1000", "Int"),
	("Communication", "cc", "read_only", "1", "Check"),
	("Communication", "bcc", "fieldtype", "Data", "Select"),
	("Communication", "bcc", "read_only", "1", "Check"),
	("Newsletter", "newsletter_content", "hide_border", "1", "Check"),
]


def add_field_options(doctype: str, field_name: str, options_to_add: list[str]):
	"""Add options to a Select field via Property Setter."""
	docfield = frappe.get_meta(doctype).get_field(field_name)
	if not docfield:
		return

	# Check if a property setter exists for the field's options
	existing_setter = cast(
		PropertySetterValue,
		frappe.db.get_value(
			"Property Setter",
			{
				"doc_type": doctype,
				"field_name": field_name,
				"property": "options",
			},
			["name", "value"],
			as_dict=True,
		),
	)

	if existing_setter:
		existing_options = set(existing_setter.value.split("\n"))
		new_options = existing_options.union(options_to_add)
		if new_options != existing_options:
			frappe.db.set_value(
				"Property Setter",
				existing_setter.name,
				"value",
				"\n".join(sorted(new_options)),
			)
	else:
		# Get the default options from the DocField
		docfield_options = set((docfield.options or "").split("\n"))
		new_options = docfield_options.union(options_to_add)
		if new_options != docfield_options:
			frappe.make_property_setter(
				{
					"doctype": doctype,
					"doctype_or_field": "DocField",
					"fieldname": field_name,
					"property": "options",
					"value": "\n".join(sorted(new_options)),
					"property_type": "Text",
				},
				is_system_generated=True,
			)


def ensure_property_setters():
	"""Create or correct the app's PROPERTY_SETTERS, leaving the ones already in place alone."""
	for doctype, fieldname, prop, value, property_type in PROPERTY_SETTERS:
		existing = frappe.db.get_value(
			"Property Setter",
			{"doc_type": doctype, "field_name": fieldname or ("is", "not set"), "property": prop},
			["value", "is_system_generated"],
			as_dict=True,
		)
		if existing and (existing.value or "") == value and existing.is_system_generated:
			continue
		# A new setter replaces any other on the same property (PropertySetter.validate).
		frappe.make_property_setter(
			{
				"doctype": doctype,
				"doctype_or_field": "DocField" if fieldname else "DocType",
				"fieldname": fieldname,
				"property": prop,
				"value": value,
				"property_type": property_type,
			},
			is_system_generated=True,
			module="Messaging",
		)


def add_doctype_views():
	"""Add Chat as a valid doctype view option."""
	add_field_options("DocType", "default_view", DOCVIEW)
	add_field_options("Workspace Shortcut", "doc_view", DOCVIEW)


def after_install():
	"""Run after the app is installed."""
	add_doctype_views()
	ensure_property_setters()


def after_migrate():
	"""Run after migrations to ensure DocType Views and the app's property setters exist."""
	add_doctype_views()
	ensure_property_setters()


def revert_field_options(doctype: str, field_name: str, options_to_remove: list[str]):
	"""Remove options from a Select field's Property Setter."""
	existing_setter = cast(
		PropertySetterValue,
		frappe.db.get_value(
			"Property Setter",
			{
				"doc_type": doctype,
				"field_name": field_name,
				"property": "options",
			},
			["name", "value"],
			as_dict=True,
		),
	)

	if existing_setter:
		existing_options = set(existing_setter.value.split("\n"))
		new_options = existing_options - set(options_to_remove)
		if new_options != existing_options:
			if new_options:
				frappe.db.set_value(
					"Property Setter",
					existing_setter.name,
					"value",
					"\n".join(sorted(new_options)),
				)
			else:
				# If no options left, delete the property setter
				frappe.delete_doc("Property Setter", existing_setter.name)


def remove_doctype_views():
	"""Remove Chat doctype view option."""
	revert_field_options("DocType", "default_view", DOCVIEW)
	revert_field_options("Workspace Shortcut", "doc_view", DOCVIEW)


def after_uninstall():
	"""Clean up DocType Views on uninstall."""
	remove_doctype_views()
