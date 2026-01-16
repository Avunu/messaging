# Copyright (c) 2025, Avunu LLC
# License: MIT. See LICENSE
"""
Type definitions for the Chat API.

These TypedDicts match the vue-advanced-chat component's expected data structures,
adapted for Frappe's Communication doctype.
"""

from datetime import datetime
from typing import Literal, TypedDict


class UserStatus(TypedDict):
	"""User online/offline status."""

	state: Literal["online", "offline"]
	lastChanged: str


class RoomUser(TypedDict):
	"""User representation within a chat room."""

	_id: str
	username: str
	avatar: str
	status: UserStatus


class MessageFile(TypedDict, total=False):
	"""File attachment on a message."""

	name: str
	type: str
	extension: str
	url: str
	localUrl: str
	preview: str
	size: int
	audio: bool
	duration: float
	progress: int


class LastMessage(TypedDict, total=False):
	"""Summary of the last message in a room."""

	content: str
	senderId: str
	username: str
	timestamp: str
	saved: bool
	distributed: bool
	seen: bool
	new: bool
	files: list[MessageFile]


class Room(TypedDict, total=False):
	"""
	Chat room representation.

	In our Frappe implementation, a "room" represents a conversation thread
	with a specific contact/phone number, grouping all related Communications.
	"""

	roomId: str
	roomName: str
	avatar: str
	users: list[RoomUser]
	unreadCount: int
	index: str | int | datetime
	lastMessage: LastMessage
	typingUsers: list[str]
	# Custom Frappe fields
	communicationMedium: Literal["Email", "SMS", "Phone", "Chat", "Other"]
	contactName: str | None
	phoneNo: str | None
	emailId: str | None
	referenceDoctype: str | None
	referenceName: str | None


class MessageReaction(TypedDict):
	"""Reaction to a message (emoji + user IDs)."""

	emoji: str
	userIds: list[str]


class ReplyMessage(TypedDict, total=False):
	"""Message being replied to."""

	_id: str
	content: str
	senderId: str
	files: list[MessageFile]


class Message(TypedDict, total=False):
	"""
	Individual message within a room.

	Maps to a Frappe Communication document.
	"""

	_id: str
	senderId: str
	indexId: str | int
	content: str
	username: str
	avatar: str
	date: str
	timestamp: str
	system: bool
	saved: bool
	distributed: bool
	seen: bool
	deleted: bool
	edited: bool
	failure: bool
	disableActions: bool
	disableReactions: bool
	files: list[MessageFile]
	reactions: dict[str, list[str]]
	replyMessage: ReplyMessage
	# Custom Frappe fields
	communicationName: str
	communicationMedium: Literal["Email", "SMS", "Phone", "Chat", "Other"]
	sentOrReceived: Literal["Sent", "Received"]
	subject: str | None
	referenceDoctype: str | None
	referenceName: str | None


class CurrentUser(TypedDict):
	"""Current logged-in user information."""

	_id: str
	username: str
	avatar: str
	email: str
	fullName: str
	status: UserStatus


class RoomQueryParams(TypedDict, total=False):
	"""Parameters for querying rooms."""

	page: int
	limit: int
	search: str
	medium: Literal["Email", "SMS", "Phone", "Chat", "Other", "All"]


class MessageQueryParams(TypedDict, total=False):
	"""Parameters for querying messages in a room."""

	room_id: str
	page: int
	limit: int
	before_id: str


class SendMessageParams(TypedDict, total=False):
	"""Parameters for sending a new message."""

	room_id: str
	content: str
	files: list[dict]
	reply_message_id: str
	medium: Literal["Email", "SMS"]


class RoomsResponse(TypedDict):
	"""Response structure for get_rooms API."""

	rooms: list[Room]
	total: int
	page: int
	hasMore: bool


class MessagesResponse(TypedDict):
	"""Response structure for get_messages API."""

	messages: list[Message]
	total: int
	page: int
	hasMore: bool


class SendMessageResponse(TypedDict):
	"""Response structure for send_message API."""

	success: bool
	message: Message | None
	error: str | None


class MarkSeenResponse(TypedDict):
	"""Response structure for mark_messages_seen API."""

	success: bool
	count: int
