# Copyright (c) 2025, Avunu LLC
# License: MIT. See LICENSE
"""
Content formatting utilities for the Chat API.

Functions for parsing and formatting email/message content for display.
"""

import re

from email_reply_parser import EmailReplyParser


def strip_quoted_replies(content: str) -> str:
	"""
	Strip quoted reply text from email content for cleaner chat display.

	Handles multiple patterns:
	1. Standard ">" prefix quoting
	2. "---On [date], [sender] wrote:" pattern
	3. "On [date], [sender] wrote:" pattern
	4. "From: ... Sent: ... To: ... Subject:" Outlook-style headers
	5. Email signature separators

	Args:
	    content: Raw email content (plain text)

	Returns:
	    Content with quoted replies stripped
	"""
	if not content:
		return content

	# First, try EmailReplyParser
	try:
		parsed = EmailReplyParser.parse_reply(content)
		if parsed and parsed.strip():
			content = parsed.strip()
	except Exception:
		pass

	# Pattern 1: "---On [date], [sender] wrote:"
	pattern_dashes = re.compile(r"\s*-{2,3}\s*On\s+.+?\s+wrote:\s*.*", re.IGNORECASE | re.DOTALL)
	match = pattern_dashes.search(content)
	if match:
		content = content[: match.start()].strip()

	# Pattern 2: "On [date/time], [sender] wrote:"
	pattern_on_wrote = re.compile(
		r"On\s+"
		r"(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*[,]?\s+)?"
		r"(?:"
		r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}"
		r"|"
		r"\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
		r")"
		r"[^<]*?"
		r"wrote:\s*",
		re.IGNORECASE | re.DOTALL,
	)
	match = pattern_on_wrote.search(content)
	if match:
		content = content[: match.start()].strip()

	# Pattern 3: Simpler fallback - any "On ... wrote:" pattern
	pattern_on_wrote_simple = re.compile(
		r"On\s+[A-Za-z]{3}[^w]{0,100}wrote:\s*",
		re.IGNORECASE | re.DOTALL,
	)
	match = pattern_on_wrote_simple.search(content)
	if match:
		content = content[: match.start()].strip()

	# Pattern 4: Lines starting with ">" (standard email quoting)
	lines = content.split("\n")
	while lines and lines[-1].strip().startswith(">"):
		lines.pop()
	content = "\n".join(lines).strip()

	# Pattern 5: Outlook-style headers
	pattern_outlook = re.compile(r"^\s*From:\s+.+$", re.IGNORECASE | re.MULTILINE)
	match = pattern_outlook.search(content)
	if match:
		remaining = content[match.start() :]
		if re.search(r"^Sent:\s+", remaining, re.IGNORECASE | re.MULTILINE):
			content = content[: match.start()].strip()

	# Pattern 6: Clean up artifacts
	content = content.replace("\ufeff", "").replace("\u200b", "")

	lines = [line.rstrip() for line in content.split("\n")]
	while lines and not lines[-1]:
		lines.pop()
	content = "\n".join(lines)

	# Pattern 7: "Leave this conversation" footer
	pattern_unsubscribe = re.compile(r"\s*Leave this conversation.*$", re.IGNORECASE | re.DOTALL)
	content = pattern_unsubscribe.sub("", content).strip()

	# Pattern 8: Email signature separator
	pattern_signature = re.compile(r"^--\s*$", re.MULTILINE)
	match = pattern_signature.search(content)
	if match:
		content = content[: match.start()].strip()

	return content


def html_to_plain_text(html_content: str) -> str:
	"""
	Convert HTML content to plain text, preserving line breaks.

	Args:
	    html_content: HTML string

	Returns:
	    Plain text with newlines preserved
	"""
	if not html_content:
		return ""

	text = html_content
	# Replace <br> and block-level closings with newlines
	text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
	text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
	text = re.sub(r"</div>", "\n", text, flags=re.IGNORECASE)
	# Remove remaining HTML tags
	text = re.sub(r"<[^>]+>", "", text)
	# Clean up multiple consecutive newlines
	text = re.sub(r"\n{3,}", "\n\n", text)
	return text.strip()


def plain_text_to_html(text: str) -> str:
	"""
	Convert plain text to simple HTML, converting newlines to <br>.

	Args:
	    text: Plain text string

	Returns:
	    HTML string with <br> tags
	"""
	if not text:
		return ""
	return text.replace("\n", "<br>\n")


def build_quoted_reply(
	content: str,
	reply_content: str,
	reply_sender: str,
	reply_date_str: str,
) -> str:
	"""
	Build email content with a quoted reply block.

	Args:
	    content: The new message content
	    reply_content: The content being replied to
	    reply_sender: The sender of the original message
	    reply_date_str: Formatted date string

	Returns:
	    Full email content with quoted reply at bottom
	"""
	# Strip HTML from quoted content
	quoted_text = reply_content
	if "<" in quoted_text and ">" in quoted_text:
		quoted_text = html_to_plain_text(quoted_text)

	# Add ">" prefix to each line for email quoting
	quoted_lines = [f"> {line}" for line in quoted_text.split("\n")]
	quoted_block = "\n".join(quoted_lines)

	# Build the full email content
	return f"{content}\n\nOn {reply_date_str}, {reply_sender} wrote:\n{quoted_block}"
