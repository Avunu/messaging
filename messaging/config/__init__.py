# Copyright (c) 2024, Avunu LLC and contributors
# For license information, please see license.txt

from typing import Any, cast

import frappe
from frappe.types import DF
from frappe.types.frappedict import _dict


class PropertySetterValue(_dict):
	"""Dict-like object for sales quote rule data that exposes keys as attributes"""

	def __init__(self, data: dict[str, Any] | None = None):
		super().__init__(data or {})

	name: DF.Data
	value: DF.SmallText


# DocType View for Chat audit trail
DOCVIEW = ["Chat"]


def after_install():
	"""Run after esign app is installed."""
	add_doctype_views()


def after_migrate():
	"""Run after migrations to ensure DocType Views exist."""
	add_doctype_views()


def after_uninstall():
	"""Clean up DocType Views on uninstall."""
	remove_doctype_views()


def add_doctype_views():
	"""Add Chat as a valid doctype view option."""
	add_field_options("DocType", "default_view", DOCVIEW)
	add_field_options("Workspace Shortcut", "doc_view", DOCVIEW)


def remove_doctype_views():
	"""Remove Chat doctype view option."""
	revert_field_options("DocType", "default_view", DOCVIEW)
	revert_field_options("Workspace Shortcut", "doc_view", DOCVIEW)


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
