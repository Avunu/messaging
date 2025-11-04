# Messaging App

Lightweight messaging extension for Frappe/ERPNext providing SMS delivery, contact enrichment, and mail-merge capable newsletters.

## Features
- Twilio SMS inbound webhook (creates Communication records).
- Group Text Message doctype (broadcast to validated primary mobile numbers with SMS consent).
- Automatic phone number normalization (E.164), deduplication, and optional Twilio carrier/type validation.
- Contact consent flag (consent_sms) to control outbound SMS eligibility.
- Messaging Groups with automatic dynamic linking to Contacts and optional synchronization to an Email Group.
- Newsletter override supporting merge tags: {{first_name}}, {{last_name}}, {{full_name}}, {{company_name}}, {{designation}}, {{gender}}, {{salutation}}.
- Workspace shortcuts for rapid access.

## Installation
1. Fetch app into your bench:
   bench get-app messaging <repository_url>
2. Install:
   bench --site <yoursite> install-app messaging
3. Migrate:
   bench migrate

## Configuration
1. Open Messaging Settings:
   - Set "Messaging Group for All Contacts" (optional auto-enroll on creation).
   - (Optional) Enable Phone Number Validation.
   - Enter Twilio Account SID, Auth Token (Password field), and Twilio Phone Number.
2. Ensure System Settings country is set (used for number parsing).
3. Create Messaging Groups (optionally link an Email Group).
4. Grant appropriate roles (System Manager / Newsletter Manager).

## Twilio Inbound Webhook
Endpoint: /api/method/messaging.messaging.messaging.api.twilio_webhook.sms
- Validates X-Twilio-Signature.
- Creates a Communication (sent_or_received = Received).
- Returns HTTP 204 on success.

## Outbound Group SMS
1. Create Group Text Message.
2. Select target Messaging Groups; optionally exclude groups.
3. (Optional) Schedule with future Delivery Date/Time.
4. Submit:
   - If scheduled: status = Scheduled.
   - Else: message sent immediately via SMS Settings (send_sms).

Sending logic filters:
- Contact in included groups.
- Not in excluded groups.
- consent_sms == 1.
- Has a primary mobile (is_primary_mobile_no == 1) that is validated (is_valid == 1).

## Phone Number Processing
Hook: messaging.messaging.messaging.hooks.contact.validate
- Deduplicate emails and phones.
- Convert to E.164 using phonenumbers library (country fallback: Address country → System Settings).
- Optional Twilio Lookup (line_type_intelligence) sets is_valid + carrier_type.
- Auto-select primary phone/mobile if missing or invalid.

## Newsletter Merge
Override class adds contact-aware rendering:
- Each recipient resolved through Contact Email → Contact.
- If no contact, falls back to inferred full_name (local-part of email).
- Merge tags inserted via Jinja evaluation.

## Data Models (Highlights)
- Messaging Group: members (Table MultiSelect of Messaging Group Member).
- Group Text Message: target groups + exclude groups.
- Contact custom fields: consent_sms.
- Contact Phone custom fields: is_valid, validated_number, carrier_type.

## Workflows
Contact creation:
- Optionally added to “All Contacts” Messaging Group.
Inbound SMS:
- Creates Communication marked Open.
Group broadcast:
- Adds descriptive comment listing recipient count.

## Developer Notes
- Dynamic Link used to associate Messaging Groups to Contacts.
- Email Group synchronization ensures parity with messaging membership.
- Validation commits only when necessary; avoids redundant Twilio lookups.
- Error handling logs Twilio lookup issues without blocking save.

## Security
- Twilio webhook enforces signature validation.
- Auth Token stored as Password (masked).
- SMS sending restricted to consented + validated contacts.

## Extensibility
- Add new merge tags by extending Newsletter.get_contact_map or template context.
- Integrate alternative SMS providers by replacing send_sms in GroupTextMessage.

## Troubleshooting
- No SMS sent: verify consent_sms, primary mobile flag, validation enabled, correct Twilio credentials.
- Numbers not validated: ensure enable_number_validation is checked and credentials valid.
- Merge tags blank: recipient not matched to a Contact record.

## License
mit
