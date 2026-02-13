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
		const customStyles = computed(() => ({
			general: {
				color: isDarkMode.value ? "#fff" : "#0a0a0a",
				colorButtonClear: isDarkMode.value ? "#fff" : "#1976d2",
				colorButton: isDarkMode.value ? "#fff" : "#1976d2",
				backgroundColorButton: "transparent",
				borderStyle: "1px solid #e1e4e8",
			},
			container: {
				borderRadius: "8px",
				boxShadow: "0 2px 8px rgba(0, 0, 0, 0.08)",
			},
			header: {
				background: isDarkMode.value ? "#1e1e1e" : "#f8f9fa",
			},
			footer: {
				background: isDarkMode.value ? "#1e1e1e" : "#f8f9fa",
				borderTop: "1px solid #e1e4e8",
			},
			content: {
				background: isDarkMode.value ? "#121212" : "#fff",
			},
			sidemenu: {
				background: isDarkMode.value ? "#1e1e1e" : "#f8f9fa",
				borderRight: "1px solid #e1e4e8",
			},
			room: {
				colorMessage: isDarkMode.value ? "#e0e0e0" : "#67717a",
				colorTimestamp: isDarkMode.value ? "#9e9e9e" : "#9ca6af",
				colorStateOnline: "#4caf50",
				colorStateOffline: "#9e9e9e",
			},
			message: {
				background: isDarkMode.value ? "#2d2d2d" : "#f0f2f5",
				backgroundMe: isDarkMode.value ? "#0d47a1" : "#dcf8c6",
				color: isDarkMode.value ? "#fff" : "#0a0a0a",
				colorMe: isDarkMode.value ? "#fff" : "#0a0a0a",
				colorStarted: isDarkMode.value ? "#9e9e9e" : "#9ca6af",
				backgroundDeleted: isDarkMode.value ? "#1e1e1e" : "#e8e8e8",
				colorDeleted: isDarkMode.value ? "#757575" : "#757575",
				colorTimestamp: isDarkMode.value ? "#bdbdbd" : "#828282",
				backgroundDate: isDarkMode.value ? "#424242" : "#e5efff",
				colorDate: isDarkMode.value ? "#fff" : "#505a62",
				backgroundReply: isDarkMode.value ? "#3d3d3d" : "#e8f4fd",
				colorReply: isDarkMode.value ? "#e0e0e0" : "#185a9d",
				colorReplyUsername: isDarkMode.value ? "#64b5f6" : "#185a9d",
				backgroundImage: isDarkMode.value ? "#3d3d3d" : "#ddd",
				colorNewMessages: "#1976d2",
				backgroundNewMessages: isDarkMode.value ? "#0d47a1" : "#e3f2fd",
			},
			icons: {
				search: isDarkMode.value ? "#bdbdbd" : "#9ca6af",
				add: isDarkMode.value ? "#64b5f6" : "#1976d2",
				toggle: isDarkMode.value ? "#bdbdbd" : "#0a0a0a",
				menu: isDarkMode.value ? "#bdbdbd" : "#0a0a0a",
				close: isDarkMode.value ? "#bdbdbd" : "#9ca6af",
				closeImage: isDarkMode.value ? "#fff" : "#fff",
				file: isDarkMode.value ? "#64b5f6" : "#1976d2",
				paperclip: isDarkMode.value ? "#bdbdbd" : "#9ca6af",
				closeOutline: isDarkMode.value ? "#bdbdbd" : "#000",
				closePreview: isDarkMode.value ? "#bdbdbd" : "#fff",
				send: isDarkMode.value ? "#64b5f6" : "#1976d2",
				sendDisabled: isDarkMode.value ? "#616161" : "#9ca6af",
				emoji: isDarkMode.value ? "#bdbdbd" : "#9ca6af",
				emojiReaction: isDarkMode.value ? "#bdbdbd" : "#828282",
				document: isDarkMode.value ? "#64b5f6" : "#1976d2",
				pencil: isDarkMode.value ? "#bdbdbd" : "#9e9e9e",
				checkmark: isDarkMode.value ? "#4caf50" : "#9e9e9e",
				checkmarkSeen: isDarkMode.value ? "#64b5f6" : "#0d6efd",
				eye: isDarkMode.value ? "#64b5f6" : "#fff",
				dropdownMessage: isDarkMode.value ? "#bdbdbd" : "#fff",
				dropdownRoom: isDarkMode.value ? "#bdbdbd" : "#9e9e9e",
				dropdownScroll: isDarkMode.value ? "#64b5f6" : "#0a0a0a",
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
	background: var(--bg-color, #fff);
}

/* ChatWindow fills remaining space below toolbar */
.chat-window {
	flex: 1;
	min-height: 0;
	overflow: hidden;
}

.chat-dark {
	--bg-color: #121212;
}

.chat-toolbar {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 12px 16px;
	background: var(--card-bg, #f8f9fa);
	border-bottom: 1px solid var(--border-color, #e1e4e8);
}

.chat-dark .chat-toolbar {
	--card-bg: #1e1e1e;
	--border-color: #333;
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
	font-size: 18px;
	font-weight: 600;
	color: var(--text-color, #0a0a0a);
}

.chat-dark .toolbar-title {
	--text-color: #fff;
}

.unread-badge {
	background: #dc3545;
	color: #fff;
	font-size: 12px;
	font-weight: 600;
	padding: 2px 8px;
	border-radius: 10px;
	min-width: 20px;
	text-align: center;
}

.medium-filter {
	padding: 6px 12px;
	border: 1px solid var(--border-color, #e1e4e8);
	border-radius: 6px;
	background: var(--input-bg, #fff);
	color: var(--text-color, #0a0a0a);
	font-size: 14px;
	cursor: pointer;
}

.chat-dark .medium-filter {
	--input-bg: #2d2d2d;
	--text-color: #fff;
	--border-color: #444;
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
	font-size: 11px;
	padding: 2px 8px;
	border-radius: 4px;
	background: #e3f2fd;
	color: #1976d2;
}

.medium-email {
	background: #e3f2fd;
	color: #1976d2;
}

.medium-sms {
	background: #e8f5e9;
	color: #388e3c;
}

.medium-phone {
	background: #fff3e0;
	color: #f57c00;
}

.room-reference {
	font-size: 12px;
}

.reference-link {
	color: #1976d2;
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
	font-size: 12px;
	margin-bottom: 4px;
	color: #666;
}

.message-reference {
	margin-top: 8px;
	font-size: 11px;
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
	background: rgba(0, 0, 0, 0.04);
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
	border-radius: 50%;
	background: #9e9e9e;
	border: 2px solid #fff;
}

.online-indicator.is-online {
	background: #4caf50;
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
	font-weight: 600;
	color: var(--text-color, #0a0a0a);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.room-item-time {
	font-size: 12px;
	color: #9ca6af;
	flex-shrink: 0;
}

.room-item-footer {
	display: flex;
	align-items: center;
	gap: 6px;
}

.room-item-medium {
	font-size: 12px;
	flex-shrink: 0;
}

.room-item-preview {
	flex: 1;
	font-size: 13px;
	color: #67717a;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.room-item-unread {
	background: #1976d2;
	color: #fff;
	font-size: 11px;
	font-weight: 600;
	padding: 2px 6px;
	border-radius: 10px;
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
	background: rgba(0, 0, 0, 0.5);
	z-index: 1000;
	display: flex;
	justify-content: flex-end;
}

.comm-panel {
	width: 400px;
	max-width: 90vw;
	background: #fff;
	height: 100%;
	box-shadow: -2px 0 8px rgba(0, 0, 0, 0.15);
	display: flex;
	flex-direction: column;
}

.chat-dark .comm-panel {
	background: #1e1e1e;
	color: #fff;
}

.comm-panel-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 16px;
	border-bottom: 1px solid #e1e4e8;
}

.chat-dark .comm-panel-header {
	border-color: #333;
}

.comm-panel-header h4 {
	margin: 0;
}

.close-btn {
	background: none;
	border: none;
	font-size: 24px;
	cursor: pointer;
	color: #666;
	line-height: 1;
	padding: 0;
}

.chat-dark .close-btn {
	color: #bbb;
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
	font-size: 12px;
	font-weight: 600;
	color: #666;
	text-transform: uppercase;
}

.chat-dark .detail-row label {
	color: #999;
}

.detail-row.actions {
	margin-top: 16px;
}

.btn {
	display: inline-block;
	padding: 8px 16px;
	border-radius: 6px;
	text-decoration: none;
	font-size: 14px;
	cursor: pointer;
	transition: all 0.2s;
}

.btn-default {
	background: #f0f0f0;
	color: #333;
	border: 1px solid #ddd;
}

.btn-default:hover {
	background: #e0e0e0;
}

.chat-dark .btn-default {
	background: #333;
	color: #fff;
	border-color: #444;
}

.chat-dark .btn-default:hover {
	background: #444;
}

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
