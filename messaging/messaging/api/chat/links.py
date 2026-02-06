# Copyright (c) 2025, Avunu LLC
# License: MIT. See LICENSE
"""
API endpoints for fetching linked documents.
"""

from typing import Any

import frappe
from frappe import _
from frappe.query_builder import DocType, Order


@frappe.whitelist()
def get_linked_documents(doctype: str, docname: str) -> dict[str, list[dict[str, Any]]]:
	"""
	Get all documents linked to a specific document.

	Uses the DocType Link configuration to find linked documents.

	Args:
	    doctype: The doctype of the document (e.g., "Contact")
	    docname: The name of the document

	Returns:
	    Dictionary grouped by group name, containing lists of linked documents
	"""
	if not doctype or not docname:
		return {}

	# Check if the document exists
	if not frappe.db.exists(doctype, docname):
		return {}

	# Get all DocType Links for this doctype
	DocTypeLink = DocType("DocType Link")
	links = (
		frappe.qb.from_(DocTypeLink)
		.select(
			DocTypeLink.link_doctype,
			DocTypeLink.link_fieldname,
			DocTypeLink.parent_doctype,
			DocTypeLink.table_fieldname,
			DocTypeLink.group,
			DocTypeLink.is_child_table,
			DocTypeLink.hidden,
		)
		.where(DocTypeLink.parent == doctype)
		.where(DocTypeLink.hidden == 0)
		.orderby(DocTypeLink.group, order=Order.asc)
		.orderby(DocTypeLink.parent_doctype, order=Order.desc)
		.run(as_dict=True)
	)

	result: dict[str, list[dict[str, Any]]] = {}

	for link in links:
		link_doctype = link.get("link_doctype")
		link_fieldname = link.get("link_fieldname")
		is_child_table = link.get("is_child_table")
		parent_doctype = link.get("parent_doctype")
		group = link.get("group") or "Related"

		if not link_doctype or not link_fieldname:
			continue

		try:
			linked_docs = []

			if is_child_table and parent_doctype:
				# For child tables, we need to find parent documents
				# that have this document in their child table
				ChildTable = DocType(link_doctype)

				# Get parent names from the child table
				child_results = (
					frappe.qb.from_(ChildTable)
					.select(ChildTable.parent)
					.where(getattr(ChildTable, link_fieldname) == docname)
					.orderby(ChildTable.creation, order=Order.desc)
					.distinct()
					.run(as_dict=True)
				)

				for child in child_results:
					parent_name = child.get("parent")
					if parent_name and frappe.db.exists(parent_doctype, parent_name):
						# Get title field for display
						title = get_document_title(parent_doctype, parent_name)
						linked_docs.append(
							{
								"doctype": parent_doctype,
								"name": parent_name,
								"title": title,
							}
						)
			else:
				# Regular link - query the linked doctype directly
				LinkedDocType = DocType(link_doctype)

				# Check if the field exists on the doctype
				if not frappe.get_meta(link_doctype).has_field(link_fieldname):
					continue

				results = (
					frappe.qb.from_(LinkedDocType)
					.select(LinkedDocType.name)
					.where(getattr(LinkedDocType, link_fieldname) == docname)
					.orderby(LinkedDocType.creation, order=Order.desc)
					.run(as_dict=True)
				)

				for row in results:
					doc_name = row.get("name")
					if doc_name:
						title = get_document_title(link_doctype, doc_name)
						linked_docs.append(
							{
								"doctype": link_doctype,
								"name": doc_name,
								"title": title,
							}
						)

			if linked_docs:
				if group not in result:
					result[group] = []
				result[group].extend(linked_docs)

		except Exception as e:
			# Log but don't fail for individual link queries
			frappe.log_error(f"Error fetching linked documents for {link_doctype}: {e}")
			continue

	return result


def get_document_title(doctype: str, name: str) -> str:
	"""
	Get a display title for a document.

	Uses the title field if defined, otherwise falls back to name.
	"""
	try:
		meta = frappe.get_meta(doctype)
		title_field = meta.title_field

		if title_field and title_field != "name":
			title = frappe.db.get_value(doctype, name, title_field)
			if title:
				return str(title)

		return name
	except Exception:
		return name
