<template>
	<div class="chat-container" :class="{ 'chat-dark': isDarkMode }">
		<!-- Filter toolbar -->
		<div class="chat-toolbar">
			<div class="toolbar-left">
				<h3 class="toolbar-title">{{ __("Messages") }}</h3>
				<span v-if="unreadCount > 0" class="unread-badge">{{
					unreadCount
				}}</span>
			</div>
			<div class="toolbar-right">
				<select
					v-model="selectedMedium"
					class="medium-filter"
					@change="onMediumChange"
				>
					<option value="All">{{ __("All Messages") }}</option>
					<option value="Email">{{ __("Email") }}</option>
					<option value="SMS">{{ __("SMS") }}</option>
					<option value="Phone">{{ __("Phone") }}</option>
				</select>
			</div>
		</div>

		<!-- Main chat layout: composes upstream RoomsList + Room with our custom TextEditor footer -->
		<ChatWindow
			class="chat-window"
			:current-user-id="currentUserId"
			:rooms="rooms"
			:rooms-loaded="roomsLoaded"
			:loading-rooms="loadingRooms"
			:messages="messages"
			:messages-loaded="messagesLoaded"
			:room-id="currentRoomId"
			:show-search="true"
			:show-add-room="false"
			:show-reaction-emojis="false"
			:show-new-messages-divider="true"
			:text-messages="textMessages"
			:room-info-enabled="true"
			:menu-actions="menuActions"
			:message-actions="messageActions"
			:theme="theme"
			:styles="customStyles"
			:reply-message="replyToMessage"
			:custom-search-room-enabled="true"
			@fetch-messages="onFetchMessages"
			@send-message="onSendMessage"
			@room-info="onRoomInfo"
			@menu-action-handler="onMenuAction"
			@message-action-handler="onMessageAction"
			@search-room="onSearchRoom"
			@fetch-more-rooms="onFetchMoreRooms"
			@open-file="onOpenFile"
			@typing-message="onTypingMessage"
			@clear-reply="replyToMessage = null"
		/>

		<!-- Side panel for Communication details -->
		<Teleport to="body">
			<div
				v-if="showCommPanel"
				class="comm-panel-overlay"
				@click="closeCommPanel"
			>
				<div class="comm-panel" @click.stop>
					<div class="comm-panel-header">
						<h4>{{ __("Communication Details") }}</h4>
						<button class="close-btn" @click="closeCommPanel">
							&times;
						</button>
					</div>
					<div class="comm-panel-body">
						<div v-if="selectedMessage" class="comm-details">
							<div class="detail-row">
								<label>{{ __("Type") }}:</label>
								<span>{{
									selectedMessage.communicationMedium
								}}</span>
							</div>
							<div class="detail-row">
								<label>{{ __("Direction") }}:</label>
								<span>{{
									selectedMessage.sentOrReceived
								}}</span>
							</div>
							<div
								v-if="selectedMessage.subject"
								class="detail-row"
							>
								<label>{{ __("Subject") }}:</label>
								<span>{{ selectedMessage.subject }}</span>
							</div>
							<div class="detail-row">
								<label>{{ __("Date") }}:</label>
								<span
									>{{ selectedMessage.date }}
									{{ selectedMessage.timestamp }}</span
								>
							</div>
							<div
								v-if="selectedMessage.referenceDoctype"
								class="detail-row"
							>
								<label>{{ __("Reference") }}:</label>
								<a
									:href="`/app/${encodeDoctype(
										selectedMessage.referenceDoctype,
									)}/${selectedMessage.referenceName}`"
									target="_blank"
								>
									{{ selectedMessage.referenceDoctype }}:
									{{ selectedMessage.referenceName }}
								</a>
							</div>
							<div class="detail-row actions">
								<a
									:href="`/app/communication/${selectedMessage.communicationName}`"
									class="btn btn-default btn-sm"
									target="_blank"
								>
									{{ __("Open Communication") }}
								</a>
							</div>
						</div>
					</div>
				</div>
			</div>
		</Teleport>

		<!-- Contact Details Panel -->
		<ContactPanel
			:show="showContactPanel"
			:room="selectedContactRoom"
			@close="closeContactPanel"
		/>
	</div>
</template>

<script lang="ts">
import { defineComponent, ref, computed, onMounted } from "vue";
import { useChat } from "./useChat";
import ContactPanel from "./ContactPanel.vue";
import ChatWindow from "./ChatWindow.vue";

import type {
	Room,
	Message,
	ReplyMessage,
	FetchMessagesEvent,
	SendMessageEvent,
	CustomAction,
	MessageAction,
	CommunicationMedium,
} from "./types";

// Frappe globals
declare const frappe: {
	_: (text: string) => string;
	set_route: (...args: string[]) => void;
	show_alert: (options: { message: string; indicator?: string }) => void;
	utils: {
		escape_html: (text: string) => string;
	};
};

declare const __: (text: string, args?: unknown[], context?: string) => string;

export default defineComponent({
	name: "ChatView",
	components: {
		ContactPanel,
		ChatWindow,
	},

	props: {
		initialRoomId: {
			type: String,
			default: "",
		},
	},

	setup(props) {
		// Initialize chat composable
		const {
			currentUser,
			rooms,
			currentRoom,
			messages,
			loadingRooms,
			loadingMessages,
			roomsLoaded,
			messagesLoaded,
			error,
			searchQuery,
			mediumFilter,
			unreadCount,
			filteredRooms,
			currentRoomId,
			initialize,
			fetchRooms,
			fetchMessages,
			handleSendMessage,
			selectRoom,
			setSearchQuery,
			setMediumFilter,
			handleUploadFile,
			refreshUnreadCount,
			removeRoom,
		} = useChat();

		// Local state
		const selectedMedium = ref<CommunicationMedium | "All">("All");
		const showCommPanel = ref(false);
		const selectedMessage = ref<Message | null>(null);
		const showContactPanel = ref(false);
		const selectedContactRoom = ref<Room | null>(null);

		// Theme handling
		const isDarkMode = ref(false);
		const theme = computed(() => (isDarkMode.value ? "dark" : "light"));

		// Reply-to-message state (managed here, passed to ChatWindow)
		const replyToMessage = ref<ReplyMessage | null>(null);

		// Current user ID
		const currentUserId = computed(() => currentUser.value?._id ?? "");

		// Text messages for localization
		const textMessages = computed(() => ({
			ROOMS_EMPTY: __("No conversations"),
			ROOM_EMPTY: __("Select a conversation"),
			NEW_MESSAGES: __("New Messages"),
			MESSAGE_DELETED: __("This message was deleted"),
			MESSAGES_EMPTY: __("No messages"),
			CONVERSATION_STARTED: __("Conversation started"),
			TYPE_MESSAGE: __("Type a message..."),
			SEARCH: __("Search"),
			IS_ONLINE: __("is online"),
			LAST_SEEN: "", // Empty so room header shows medium:address directly
			IS_TYPING: __("is typing..."),
			CANCEL_SELECT_MESSAGE: __("Cancel"),
		}));

		// Menu actions for rooms - add archive and delete
		const menuActions: CustomAction[] = [
			{ name: "openContact", title: __("View Contact") },
			{ name: "markUnread", title: __("Mark as Unread") },
			{ name: "archiveRoom", title: __("Archive Conversation") },
			{ name: "deleteRoom", title: __("Delete Conversation") },
		];

		// Message actions - use 'reply' (not 'replyMessage') so the event
		// propagates out of the vue-advanced-chat web component to our custom footer
		const messageActions: MessageAction[] = [
			{ name: "reply", title: __("Reply") },
			{ name: "viewDetails", title: __("View Details") },
			{ name: "openCommunication", title: __("Open Communication") },
		];

		// Custom styles
		// Colors are Frappe CSS variables (resolved inline via the vendor's
		// cssThemeVars); they flip automatically on [data-theme], so no
		// isDarkMode ternaries are needed for color values.
		const customStyles = computed(() => ({
			general: {
				color: "var(--text-color)",
				colorButtonClear: "var(--primary)",
				colorButton: "var(--primary)",
				backgroundColorButton: "transparent",
				borderStyle: "1px solid var(--border-color)",
			},
			container: {
				borderRadius: "8px",
				boxShadow: "var(--shadow-sm)",
			},
			header: {
				background: "var(--card-bg)",
			},
			footer: {
				background: "var(--card-bg)",
				borderTop: "1px solid var(--border-color)",
			},
			content: {
				background: "var(--fg-color)",
			},
			sidemenu: {
				background: "var(--card-bg)",
				borderRight: "1px solid var(--border-color)",
			},
			room: {
				colorMessage: "var(--text-muted)",
				colorTimestamp: "var(--text-light)",
				colorStateOnline: "var(--green-500)",
				colorStateOffline: "var(--gray-500)",
			},
			message: {
				background: "var(--surface-gray-2)",
				backgroundMe: "var(--blue-100)",
				color: "var(--text-color)",
				colorMe: "var(--text-color)",
				colorStarted: "var(--text-light)",
				backgroundDeleted: "var(--subtle-fg)",
				colorDeleted: "var(--text-muted)",
				colorTimestamp: "var(--text-muted)",
				backgroundDate: "var(--surface-gray-2)",
				colorDate: "var(--text-muted)",
				backgroundReply: "var(--subtle-fg)",
				colorReply: "var(--text-color)",
				colorReplyUsername: "var(--primary)",
				backgroundImage: "var(--surface-gray-2)",
				colorNewMessages: "var(--primary)",
				backgroundNewMessages: "var(--blue-100)",
			},
			icons: {
				search: "var(--text-muted)",
				add: "var(--primary)",
				toggle: "var(--text-color)",
				menu: "var(--text-color)",
				close: "var(--text-muted)",
				closeImage: "var(--white)",
				file: "var(--primary)",
				paperclip: "var(--text-muted)",
				closeOutline: "var(--text-color)",
				closePreview: "var(--white)",
				send: "var(--primary)",
				sendDisabled: "var(--text-light)",
				emoji: "var(--text-muted)",
				emojiReaction: "var(--text-muted)",
				document: "var(--primary)",
				pencil: "var(--text-muted)",
				checkmark: "var(--text-muted)",
				checkmarkSeen: "var(--primary)",
				eye: "var(--white)",
				dropdownMessage: "var(--text-muted)",
				dropdownRoom: "var(--text-muted)",
				dropdownScroll: "var(--text-color)",
			},
		}));

		// Event handlers

		function onFetchMessages(data: FetchMessagesEvent): void {
			if (data?.room) {
				fetchMessages(data);
			}
		}

		function onSendMessage(data: SendMessageEvent): void {
			// data.replyMessage contains the message being replied to (if any)
			// The _id of replyMessage is the Communication document name
			handleSendMessage(data);
			// Clear reply state after sending
			replyToMessage.value = null;
		}

		function onRoomInfo(room: Room): void {
			// Show contact details panel
			selectedContactRoom.value = room;
			showContactPanel.value = true;
		}

		// Update onMenuAction to handle archive and delete
		async function onMenuAction(data: {
			roomId: string;
			action: CustomAction;
		}): Promise<void> {
			const room = rooms.value.find((r) => r.roomId === data?.roomId);
			if (!room || !data?.action) return;

			switch (data.action.name) {
				case "openContact":
					onRoomInfo(room);
					break;
				case "markUnread":
					frappe.show_alert({
						message: __("Marked as unread"),
						indicator: "blue",
					});
					break;
				case "archiveRoom":
					await archiveRoom(data.roomId);
					break;
				case "deleteRoom":
					await deleteRoom(data.roomId);
					break;
			}
		}

		// Add archive room function
		async function archiveRoom(roomId: string): Promise<void> {
			if (
				!confirm(
					__(
						"Are you sure you want to archive this conversation? All messages will be marked as closed.",
					),
				)
			) {
				return;
			}

			try {
				const response = await fetch(
					"/api/method/messaging.messaging.api.chat.api.archive_room",
					{
						method: "POST",
						headers: {
							"Content-Type": "application/json",
							"X-Frappe-CSRF-Token":
								(window as any).frappe?.csrf_token || "",
						},
						body: JSON.stringify({ room_id: roomId }),
					},
				);

				const result = await response.json();

				if (result.message?.success) {
					frappe.show_alert({
						message: __("Conversation archived ({0} messages)", [
							result.message.count,
						]),
						indicator: "green",
					});
					// Remove the room from local state instead of refetching
					// This preserves scroll position in the rooms list
					removeRoom(roomId);
				} else {
					frappe.show_alert({
						message:
							result.message?.error ||
							__("Failed to archive conversation"),
						indicator: "red",
					});
				}
			} catch (error) {
				frappe.show_alert({
					message: __("Failed to archive conversation"),
					indicator: "red",
				});
			}
		}

		// Add delete room function
		async function deleteRoom(roomId: string): Promise<void> {
			if (
				!confirm(
					__(
						"Are you sure you want to delete this conversation? This action cannot be undone.",
					),
				)
			) {
				return;
			}

			try {
				const response = await fetch(
					"/api/method/messaging.messaging.api.chat.api.delete_room",
					{
						method: "POST",
						headers: {
							"Content-Type": "application/json",
							"X-Frappe-CSRF-Token":
								(window as any).frappe?.csrf_token || "",
						},
						body: JSON.stringify({ room_id: roomId }),
					},
				);

				const result = await response.json();

				if (result.message?.success) {
					frappe.show_alert({
						message: __("Conversation deleted ({0} messages)", [
							result.message.count,
						]),
						indicator: "green",
					});
					// Remove the room from local state instead of refetching
					// This preserves scroll position in the rooms list
					removeRoom(roomId);
				} else {
					frappe.show_alert({
						message:
							result.message?.error ||
							__("Failed to delete conversation"),
						indicator: "red",
					});
				}
			} catch (error) {
				frappe.show_alert({
					message: __("Failed to delete conversation"),
					indicator: "red",
				});
			}
		}

		function onMessageAction(data: {
			roomId: string;
			action: MessageAction;
			message: Message;
		}): void {
			if (!data?.action) return;

			switch (data.action.name) {
				case "reply":
					// Store for our custom ChatFooter
					replyToMessage.value = {
						_id: data.message._id,
						content: data.message.content || "",
						senderId: data.message.senderId,
						files: data.message.files,
					} as ReplyMessage & { username?: string };
					// Attach display name for preview
					(
						replyToMessage.value as ReplyMessage & {
							username?: string;
						}
					).username = data.message.username || data.message.senderId;
					break;
				case "viewDetails":
					selectedMessage.value = data.message;
					showCommPanel.value = true;
					break;
				case "openCommunication":
					if (data.message?.communicationName) {
						window.open(
							`/app/communication/${data.message.communicationName}`,
							"_blank",
						);
					}
					break;
			}
		}

		function onSearchRoom(data: { value: string; roomId?: string }): void {
			if (data?.value !== undefined) {
				setSearchQuery(data.value);
			}
		}

		function onFetchMoreRooms(): void {
			if (!roomsLoaded.value && !loadingRooms.value) {
				fetchRooms(false);
			}
		}

		function onOpenFile(data: {
			message: Message;
			file: { url: string; action?: string };
		}): void {
			if (data?.file?.url) {
				window.open(data.file.url, "_blank");
			}
		}

		function onTypingMessage(_data: {
			roomId: string;
			message: string;
		}): void {
			// Could implement typing indicators here
		}

		function onMediumChange(): void {
			setMediumFilter(selectedMedium.value);
		}

		function closeCommPanel(): void {
			showCommPanel.value = false;
			selectedMessage.value = null;
		}

		function closeContactPanel(): void {
			showContactPanel.value = false;
			selectedContactRoom.value = null;
		}

		// Utility functions
		function encodeDoctype(doctype: string | null | undefined): string {
			if (!doctype) return "";
			return doctype.toLowerCase().replace(/ /g, "-");
		}

		function formatMessageContent(content: string | undefined): string {
			if (!content) return "";
			// Basic sanitization and formatting
			return frappe.utils
				.escape_html(content)
				.replace(/\n/g, "<br>")
				.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
				.replace(/\*(.*?)\*/g, "<em>$1</em>");
		}

		function isUserOnline(room: Room): boolean {
			return (
				room.users?.some((u) => u.status?.state === "online") ?? false
			);
		}

		function getMediumIcon(
			medium: CommunicationMedium | undefined,
		): string {
			const icons: Record<string, string> = {
				Email: "✉️",
				SMS: "💬",
				Phone: "📞",
				Chat: "💭",
				Other: "📝",
			};
			return icons[medium ?? "Other"] ?? "📝";
		}

		// Theme detection
		function updateTheme(): void {
			const htmlTheme =
				document.documentElement.getAttribute("data-theme-mode");
			if (htmlTheme === "dark") {
				isDarkMode.value = true;
			} else if (htmlTheme === "light") {
				isDarkMode.value = false;
			} else {
				// Automatic
				isDarkMode.value = window.matchMedia(
					"(prefers-color-scheme: dark)",
				).matches;
			}
		}

		// Lifecycle
		onMounted(async () => {
			updateTheme();

			// Watch for theme changes
			const observer = new MutationObserver(updateTheme);
			observer.observe(document.documentElement, {
				attributes: true,
				attributeFilter: ["data-theme-mode"],
			});

			// Initialize chat
			await initialize();

			// Open initial room if provided
			if (props.initialRoomId) {
				const room = rooms.value.find(
					(r) => r.roomId === props.initialRoomId,
				);
				if (room) {
					selectRoom(room);
				}
			}
		});

		return {
			// State
			rooms: filteredRooms,
			messages,
			loadingRooms,
			loadingMessages,
			roomsLoaded,
			messagesLoaded,
			currentRoomId,
			currentUserId,
			unreadCount,
			selectedMedium,
			showCommPanel,
			selectedMessage,
			showContactPanel,
			selectedContactRoom,
			isDarkMode,
			theme,
			textMessages,
			menuActions,
			messageActions,
			customStyles,
			replyToMessage,

			// Methods
			onFetchMessages,
			onSendMessage,
			onRoomInfo,
			onMenuAction,
			onMessageAction,
			onSearchRoom,
			onFetchMoreRooms,
			onOpenFile,
			onTypingMessage,
			onMediumChange,
			closeCommPanel,
			closeContactPanel,
			encodeDoctype,
			formatMessageContent,
			isUserOnline,
			getMediumIcon,
			__,
			archiveRoom,
			deleteRoom,
		};
	},
});
</script>

<style>
.chat-container {
	width: 100%;
	height: calc(100vh - 46px);
	display: flex;
	flex-direction: column;
	background: var(--bg-color);
}

/* ChatWindow fills remaining space below toolbar */
.chat-window {
	flex: 1;
	min-height: 0;
	overflow: hidden;
}

.chat-toolbar {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 12px 16px;
	background: var(--card-bg);
	border-bottom: 1px solid var(--border-color);
}

.toolbar-left {
	display: flex;
	align-items: center;
	gap: 8px;
}

.toolbar-right {
	display: flex;
	align-items: center;
	gap: 8px;
}

.toolbar-title {
	margin: 0;
	font-size: var(--text-xl);
	font-weight: var(--weight-semibold);
	color: var(--text-color);
}

.unread-badge {
	background: var(--bg-red);
	color: var(--text-on-red);
	font-size: var(--text-xs);
	font-weight: var(--weight-semibold);
	padding: 2px 8px;
	border-radius: var(--border-radius-md);
	min-width: 20px;
	text-align: center;
}

.medium-filter {
	padding: 6px 12px;
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius);
	background: var(--control-bg);
	color: var(--text-color);
	font-size: var(--text-md);
	cursor: pointer;
}

/* Room header customization */
.custom-room-header {
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.room-header-info {
	display: flex;
	align-items: center;
	gap: 8px;
}

.room-name {
	font-weight: 600;
}

.room-medium {
	font-size: var(--text-tiny);
	padding: 2px 8px;
	border-radius: var(--border-radius-tiny);
	background: var(--bg-blue);
	color: var(--text-on-blue);
}

.medium-email {
	background: var(--bg-blue);
	color: var(--text-on-blue);
}

.medium-sms {
	background: var(--bg-green);
	color: var(--text-on-green);
}

.medium-phone {
	background: var(--bg-orange);
	color: var(--text-on-orange);
}

.room-reference {
	font-size: var(--text-xs);
}

.reference-link {
	color: var(--primary);
	text-decoration: none;
}

.reference-link:hover {
	text-decoration: underline;
}

/* Message customization */
.custom-message {
	padding: 8px;
}

.message-failure {
	opacity: 0.6;
}

.message-subject {
	font-size: var(--text-xs);
	margin-bottom: 4px;
	color: var(--text-muted);
}

.message-reference {
	margin-top: 8px;
	font-size: var(--text-tiny);
}

/* Room list item customization */
.custom-room-item {
	display: flex;
	align-items: center;
	gap: 12px;
	padding: 12px;
	cursor: pointer;
	transition: background 0.2s;
}

.custom-room-item:hover {
	background: var(--black-overlay-50);
}

.room-item-avatar {
	position: relative;
	width: 48px;
	height: 48px;
	flex-shrink: 0;
}

.room-item-avatar img {
	width: 100%;
	height: 100%;
	border-radius: 50%;
	object-fit: cover;
}

.online-indicator {
	position: absolute;
	bottom: 2px;
	right: 2px;
	width: 10px;
	height: 10px;
	border-radius: var(--border-radius-full);
	background: var(--gray-500);
	border: 2px solid var(--white);
}

.online-indicator.is-online {
	background: var(--green-500);
}

.room-item-content {
	flex: 1;
	min-width: 0;
}

.room-item-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 4px;
}

.room-item-name {
	font-weight: var(--weight-semibold);
	color: var(--text-color);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.room-item-time {
	font-size: var(--text-xs);
	color: var(--text-light);
	flex-shrink: 0;
}

.room-item-footer {
	display: flex;
	align-items: center;
	gap: 6px;
}

.room-item-medium {
	font-size: var(--text-xs);
	flex-shrink: 0;
}

.room-item-preview {
	flex: 1;
	font-size: var(--text-sm);
	color: var(--text-muted);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.room-item-unread {
	background: var(--primary);
	color: var(--white);
	font-size: var(--text-tiny);
	font-weight: var(--weight-semibold);
	padding: 2px 6px;
	border-radius: var(--border-radius-md);
	min-width: 18px;
	text-align: center;
	flex-shrink: 0;
}

/* Communication panel */
.comm-panel-overlay {
	position: fixed;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background: var(--black-overlay-500);
	z-index: 1000;
	display: flex;
	justify-content: flex-end;
}

.comm-panel {
	width: 400px;
	max-width: 90vw;
	background: var(--fg-color);
	height: 100%;
	box-shadow: var(--shadow-lg);
	display: flex;
	flex-direction: column;
}

.comm-panel-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 16px;
	border-bottom: 1px solid var(--border-color);
}

.comm-panel-header h4 {
	margin: 0;
}

.close-btn {
	background: none;
	border: none;
	font-size: var(--text-3xl);
	cursor: pointer;
	color: var(--text-muted);
	line-height: 1;
	padding: 0;
}

.comm-panel-body {
	flex: 1;
	overflow-y: auto;
	padding: 16px;
}

.comm-details {
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.detail-row {
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.detail-row label {
	font-size: var(--text-xs);
	font-weight: var(--weight-semibold);
	color: var(--text-muted);
	text-transform: uppercase;
}

.detail-row.actions {
	margin-top: 16px;
}

/* Scoped to .chat-container: this <style> is not `scoped`, so bare `.btn` /
   `.btn-default` selectors leak out and override the desk's core Bootstrap
   buttons wherever this bundle loads. Namespacing under the component root keeps
   the chat's own buttons styled without touching core `.btn`. */
.chat-container .btn {
	display: inline-block;
	padding: 8px 16px;
	border-radius: var(--border-radius);
	text-decoration: none;
	font-size: var(--text-md);
	cursor: pointer;
	transition: all 0.2s;
}

/* .btn-default color overrides removed: let Frappe/carbon style desk buttons
   natively so they follow the active theme. */

/* Responsive */
@media (max-width: 768px) {
	.chat-container {
		height: calc(100vh - 60px);
	}

	.comm-panel {
		width: 100%;
	}

	.chat-toolbar {
		flex-direction: column;
		gap: 8px;
		align-items: flex-start;
	}

	.toolbar-right {
		width: 100%;
	}

	.medium-filter {
		width: 100%;
	}
}
</style>
