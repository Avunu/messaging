<template>
	<div class="vac-card-window" :style="cssVars">
		<div class="vac-chat-container">
			<rooms-list
				v-if="!singleRoomCasted"
				:current-user-id="currentUserId"
				:rooms="orderedRooms"
				:loading-rooms="loadingRoomsCasted"
				:rooms-loaded="roomsLoadedCasted"
				:room="room"
				:room-actions="roomActionsCasted"
				:custom-search-room-enabled="customSearchRoomEnabled"
				:text-messages="t"
				:show-search="showSearchCasted"
				:show-add-room="showAddRoomCasted"
				:show-rooms-list="showRoomsList && roomsListOpenedCasted"
				:text-formatting="textFormattingCasted"
				:link-options="linkOptionsCasted"
				:is-mobile="isMobile"
				:scroll-distance="scrollDistance"
				@fetch-room="fetchRoom"
				@fetch-more-rooms="fetchMoreRooms"
				@loading-more-rooms="loadingMoreRooms = $event"
				@add-room="addRoom"
				@search-room="searchRoom"
				@room-action-handler="roomActionHandler"
			>
				<template v-for="el in slots" #[el.slot]="data">
					<slot :name="el.slot" v-bind="data" />
				</template>
			</rooms-list>

			<!-- Wrap Room + ChatFooter in a flex column -->
			<div class="chat-messages-column">
				<room
					:current-user-id="currentUserId"
					:rooms="roomsCasted"
					:room-id="room.roomId || ''"
					:load-first-room="loadFirstRoomCasted"
					:messages="messagesCasted"
					:room-message="roomMessage"
					:messages-loaded="messagesLoadedCasted"
					:menu-actions="menuActionsCasted"
					:message-actions="messageActionsCasted"
					:message-selection-actions="messageSelectionActionsCasted"
					:auto-scroll="autoScrollCasted"
					:show-send-icon="showSendIconCasted"
					:show-files="showFilesCasted"
					:show-audio="showAudioCasted"
					:audio-bit-rate="audioBitRate"
					:audio-sample-rate="audioSampleRate"
					:show-emojis="showEmojisCasted"
					:show-reaction-emojis="showReactionEmojisCasted"
					:show-new-messages-divider="showNewMessagesDividerCasted"
					:show-footer="false"
					:text-messages="t"
					:single-room="singleRoomCasted"
					:show-rooms-list="showRoomsList && roomsListOpenedCasted"
					:text-formatting="textFormattingCasted"
					:link-options="linkOptionsCasted"
					:is-mobile="isMobile"
					:loading-rooms="loadingRoomsCasted"
					:room-info-enabled="roomInfoEnabledCasted"
					:textarea-action-enabled="textareaActionEnabledCasted"
					:textarea-auto-focus="textareaAutoFocusCasted"
					:user-tags-enabled="userTagsEnabledCasted"
					:emojis-suggestion-enabled="emojisSuggestionEnabledCasted"
					:scroll-distance="scrollDistance"
					:accepted-files="acceptedFiles"
					:capture-files="captureFiles"
					:multiple-files="multipleFilesCasted"
					:templates-text="templatesTextCasted"
					:username-options="usernameOptionsCasted"
					:emoji-data-source="emojiDataSource"
					@toggle-rooms-list="toggleRoomsList"
					@room-info="roomInfo"
					@fetch-messages="fetchMessages"
					@send-message="sendMessage"
					@edit-message="editMessage"
					@delete-message="deleteMessage"
					@open-file="openFile"
					@open-user-tag="openUserTag"
					@open-failed-message="openFailedMessage"
					@menu-action-handler="menuActionHandler"
					@message-action-handler="messageActionHandler"
					@message-selection-action-handler="
						messageSelectionActionHandler
					"
					@send-message-reaction="sendMessageReaction"
					@typing-message="typingMessage"
					@textarea-action-handler="textareaActionHandler"
				>
					<template v-for="el in slots" #[el.slot]="data">
						<slot :name="el.slot" v-bind="data" />
					</template>
				</room>

				<!-- Our custom footer with frappe-ui TextEditor -->
				<ChatFooter
					v-if="room.roomId"
					:room-id="room.roomId"
					:reply-message="replyMessage"
					:is-dark="theme === 'dark'"
					:placeholder="t.TYPE_MESSAGE"
					@send-message="footerSendMessage"
					@clear-reply="$emit('clear-reply')"
					@typing="footerTyping"
				/>
			</div>
		</div>

		<transition name="vac-fade-preview" appear>
			<media-preview
				v-if="showMediaPreview"
				:file="previewFile"
				@close-media-preview="showMediaPreview = false"
			>
				<template v-for="el in slots" #[el.slot]="data">
					<slot :name="el.slot" v-bind="data" />
				</template>
			</media-preview>
		</transition>
	</div>
</template>

<script>
/**
 * ChatWindow – extends upstream ChatWindow.vue, inheriting all props, data,
 * computed, methods, watchers, and lifecycle hooks.  The only changes are:
 *
 *   1. Template wraps <room> + <ChatFooter> in a flex column
 *   2. Room's built-in footer is hidden (:show-footer="false")
 *   3. Our ChatFooter (frappe-ui TextEditor) is placed below the messages
 *   4. MediaPreview is kept for free from upstream
 *
 * This avoids duplicating ~400 lines of orchestration logic.
 */
import ChatWindow from "@vendor-chat/lib/ChatWindow.vue";
import ChatFooter from "./ChatFooter.vue";

export default {
	name: "ChatWindow",

	extends: ChatWindow,

	components: {
		ChatFooter,
	},

	props: {
		/** Reply message object for ChatFooter (from parent's reply state) */
		replyMessage: { type: Object, default: null },
	},

	emits: ["clear-reply"],

	methods: {
		/** Forward ChatFooter's send-message (already includes roomId) */
		footerSendMessage(data) {
			this.$emit("send-message", data);
		},
		/** Forward ChatFooter's typing as typing-message with roomId */
		footerTyping(message) {
			this.$emit("typing-message", {
				message,
				roomId: this.room.roomId,
			});
		},
	},
};
</script>

<style lang="scss">
@import "@vendor-chat/styles/index.scss";

.chat-messages-column {
	display: flex;
	flex-direction: column;
	flex: 1;
	min-width: 0;
	overflow: hidden;
}

.chat-messages-column > .vac-col-messages {
	flex: 1;
	min-height: 0;
}
</style>
