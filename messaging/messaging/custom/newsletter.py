import frappe
from frappe.utils import get_formatted_email, md_to_html
from newsletter.newsletter.doctype.newsletter.newsletter import (
	Newsletter as BaseNewsletter,
)


class Newsletter(BaseNewsletter):
	def send_newsletter(self, emails: list[str], test_email: bool = False):
		"""Trigger email generation for `emails` and add it in Email Queue with contact mailmerge."""
		attachments = self.get_newsletter_attachments()
		sender = self.send_from or get_formatted_email(self.owner)
		args = self.as_dict()

		is_auto_commit_set = bool(frappe.db.auto_commit_on_many_writes)
		frappe.db.auto_commit_on_many_writes = not frappe.flags.in_test

		if isinstance(emails, str):
			emails = [e.strip() for e in emails.split(",") if e.strip()]

		# Remove duplicate emails
		emails = list(set(emails))

		# Fetch contact information for mailmerge (even for test emails)
		contact_map = self.get_contact_map(emails)

		# get email_read_tracker_url method
		if test_email:
			email_read_tracker_url = None
		else:
			email_read_tracker_url = (
				"/api/method/newsletter.newsletter.doctype.newsletter.newsletter.newsletter_email_read"
			)

		for email in emails:
			# Get contact-specific context
			email_args = args.copy()
			# Always provide a contact dict, even if empty or not found
			contact_info = contact_map.get(email) or self._get_default_contact(email)
			email_args["message"] = self.get_message(medium="email", contact=contact_info)

			frappe.sendmail(
				subject=self.subject,
				sender=sender,
				recipients=[email],
				attachments=attachments,
				template="newsletter",
				add_unsubscribe_link=self.send_unsubscribe_link,
				unsubscribe_method="/unsubscribe",
				unsubscribe_params={"name": self.name},
				reference_doctype=self.doctype,
				reference_name=self.name,
				queue_separately=True,
				send_priority=0,
				args=email_args,
				email_read_tracker_url=email_read_tracker_url,
			)

		frappe.db.auto_commit_on_many_writes = is_auto_commit_set

	def _get_default_contact(self, email: str) -> dict:
		"""Return default contact dict for emails not in Contact database"""
		return {
			"first_name": "",
			"last_name": "",
			"full_name": email.split("@")[0] if email else "",
			"company_name": "",
			"designation": "",
			"gender": "",
			"salutation": "",
		}

	def get_contact_map(self, emails: list[str]) -> dict[str, dict]:
		"""Get contact information for mailmerge fields using Query Builder"""
		if not emails:
			return {}

		# Use Query Builder to fetch contact data
		ContactEmails = frappe.qb.DocType("Contact Email")
		Contacts = frappe.qb.DocType("Contact")

		contact_data = (
			frappe.qb.from_(Contacts)
			.left_join(ContactEmails)
			.on(ContactEmails.parent == Contacts.name)
			.select(
				ContactEmails.email_id.as_("email"),
				Contacts.first_name,
				Contacts.last_name,
				Contacts.full_name,
				Contacts.company_name,
				Contacts.designation,
				Contacts.gender,
				Contacts.salutation,
			)
			.where(ContactEmails.email_id.isin(emails))
		).run(as_dict=True)

		contact_map = {}
		for row in contact_data:
			email = row.pop("email")
			contact_map[email] = row

		return contact_map

	def get_message(self, medium="", contact=None) -> str:
		"""Get newsletter message with optional contact context for mailmerge"""
		message = self.message
		if self.content_type == "Markdown":
			message = md_to_html(str(self.message_md))
		if self.content_type == "HTML":
			message = self.message_html

		template_context = {"doc": self.as_dict()}

		# Add contact fields directly to template context for direct merge tags
		if contact:
			template_context.update(contact)

		html = str(frappe.render_template(message, template_context))

		return self.add_source(html, medium=medium)
