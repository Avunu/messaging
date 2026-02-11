# Copyright (c) 2025, Avunu LLC
# License: MIT. See LICENSE

from frappe.model.document import Document


class PushSubscription(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		auth_key: DF.Data | None
		endpoint: DF.SmallText
		p256dh_key: DF.Data | None
		subscription_json: DF.LongText
		user: DF.Link
	# end: auto-generated types

	pass
