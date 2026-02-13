<template>
	<div
		v-if="roomId"
		class="chat-footer-wrapper"
		:class="{ 'chat-dark': isDark }"
	>
		<!-- Reply preview -->
		<div v-if="replyMessage" class="reply-preview">
			<div class="reply-preview-bar" />
			<div class="reply-preview-content">
				<span class="reply-preview-sender">{{
					replyMessage.username || replyMessage.senderId
				}}</span>
				<p class="reply-preview-text" v-html="truncatedReplyContent" />
			</div>
			<button
				class="reply-preview-close"
				@click="$emit('clear-reply')"
				:title="__('Cancel reply')"
			>
				&times;
			</button>
		</div>

		<!-- File previews -->
		<div v-if="files.length" class="file-preview-list">
			<div
				v-for="(file, index) in files"
				:key="index"
				class="file-preview-item"
			>
				<img
					v-if="file.preview && file.type?.startsWith('image/')"
					:src="file.preview"
					class="file-preview-thumb"
					alt=""
				/>
				<span v-else class="file-preview-icon">📎</span>
				<span class="file-preview-name">{{ file.name }}</span>
				<button class="file-preview-remove" @click="removeFile(index)">
					&times;
				</button>
			</div>
		</div>

		<!-- Editor + actions row -->
		<div class="chat-footer-input">
			<div class="editor-container" @keydown="handleKeydown">
				<TextEditor
					ref="editorRef"
					:content="editorContent"
					:editable="true"
					:placeholder="placeholder"
					:bubble-menu="false"
					:fixed-menu="true"
					:floating-menu="false"
					editor-class="chat-editor-content"
					:starterkit-options="starterkitOptions"
					@change="onEditorChange"
				/>
			</div>
			<div class="chat-footer-actions">
				<button
					class="footer-action-btn attach-btn"
					@click="triggerFileUpload"
					:title="__('Attach file')"
				>
					<svg
						width="20"
						height="20"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<path
							d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"
						/>
					</svg>
				</button>
				<button
					class="footer-action-btn send-btn"
					:class="{ 'send-disabled': isEmpty }"
					:disabled="isEmpty"
					@click="sendMessage"
					:title="__('Send message')"
				>
					<svg
						width="20"
						height="20"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<line x1="22" y1="2" x2="11" y2="13" />
						<polygon points="22 2 15 22 11 13 2 9 22 2" />
					</svg>
				</button>
			</div>
			<input
				ref="fileInputRef"
				type="file"
				multiple
				style="display: none"
				@change="onFileSelect"
			/>
		</div>
	</div>
</template>

<script lang="ts">
import { defineComponent, ref, computed, watch, nextTick } from "vue";
import { TextEditor } from "frappe-ui";
import type { ReplyMessage, MessageFile } from "./types";

declare const __: (text: string, args?: unknown[], context?: string) => string;

/** Extended reply message with optional username for display */
interface ReplyMessageWithUsername extends ReplyMessage {
	username?: string;
}

interface FileWithPreview {
	name: string;
	type: string;
	size: number;
	file: File;
	preview?: string;
	loading?: boolean;
}

export default defineComponent({
	name: "ChatFooter",
	components: {
		TextEditor,
	},

	props: {
		/** The current room ID */
		roomId: {
			type: String,
			default: "",
		},
		/** The message being replied to, if any */
		replyMessage: {
			type: Object as () => ReplyMessageWithUsername | null,
			default: null,
		},
		/** Whether the theme is dark */
		isDark: {
			type: Boolean,
			default: false,
		},
		/** Placeholder text for the editor */
		placeholder: {
			type: String,
			default: "",
		},
	},

	emits: ["send-message", "clear-reply", "typing"],

	setup(props, { emit }) {
		const editorRef = ref<InstanceType<typeof TextEditor> | null>(null);
		const fileInputRef = ref<HTMLInputElement | null>(null);
		const editorContent = ref("");
		const currentHtml = ref("");
		const files = ref<FileWithPreview[]>([]);

		// StarterKit options: disable heading (not useful in chat)
		const starterkitOptions = {
			heading: false,
			codeBlock: false,
		};

		// Check if the editor is empty (only whitespace or empty HTML tags)
		const isEmpty = computed(() => {
			const text = stripHtml(currentHtml.value).trim();
			return text.length === 0 && files.value.length === 0;
		});

		// Truncate reply content for preview
		const truncatedReplyContent = computed(() => {
			if (!props.replyMessage?.content) return "";
			const text = stripHtml(props.replyMessage.content);
			return text.length > 100 ? text.substring(0, 100) + "..." : text;
		});

		function stripHtml(html: string): string {
			const tmp = document.createElement("div");
			tmp.innerHTML = html;
			return tmp.textContent || tmp.innerText || "";
		}

		function onEditorChange(html: string): void {
			currentHtml.value = html;
			emit("typing", stripHtml(html).trim());
		}

		function handleKeydown(e: KeyboardEvent): void {
			// Enter without Shift sends the message
			if (e.key === "Enter" && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
				// Don't intercept if an autocomplete/suggestion popup is open
				// (TipTap slash commands, mentions, etc.)
				const editor = editorRef.value?.editor;
				if (editor) {
					// Check if any suggestion/autocomplete plugin is active
					// by looking for the suggestion-active class or tippy popups
					const rootEl = editorRef.value?.rootRef;
					if (rootEl) {
						const popup = document.querySelector(
							".tippy-box, .suggestion-list, .slash-commands-list",
						);
						if (popup) return; // Let the suggestion handle Enter
					}
				}

				e.preventDefault();
				e.stopPropagation();
				sendMessage();
			}
		}

		function sendMessage(): void {
			if (isEmpty.value) return;

			const content = currentHtml.value;
			const messageFiles: MessageFile[] = files.value.map((f) => ({
				name: f.name,
				type: f.type,
				extension: f.name.split(".").pop() || "",
				url: "", // Will be populated after upload
				size: f.size,
			}));

			emit("send-message", {
				roomId: props.roomId,
				content: stripHtml(content).trim() ? content : "",
				files: messageFiles,
				replyMessage: props.replyMessage || undefined,
			});

			// Clear editor
			clearEditor();
			files.value = [];
			emit("clear-reply");
		}

		function clearEditor(): void {
			const editor = editorRef.value?.editor;
			if (editor) {
				editor.commands.clearContent();
			}
			currentHtml.value = "";
			editorContent.value = "";
		}

		function triggerFileUpload(): void {
			fileInputRef.value?.click();
		}

		function onFileSelect(event: Event): void {
			const input = event.target as HTMLInputElement;
			if (!input.files) return;

			for (const file of Array.from(input.files)) {
				const filePreview: FileWithPreview = {
					name: file.name,
					type: file.type,
					size: file.size,
					file: file,
				};

				// Create preview for images
				if (file.type.startsWith("image/")) {
					const reader = new FileReader();
					reader.onload = (e) => {
						filePreview.preview = e.target?.result as string;
						// Trigger reactivity
						files.value = [...files.value];
					};
					reader.readAsDataURL(file);
				}

				files.value.push(filePreview);
			}

			// Reset input
			if (input) {
				input.value = "";
			}
		}

		function removeFile(index: number): void {
			files.value.splice(index, 1);
			files.value = [...files.value];
		}

		// Focus the editor when room changes
		watch(
			() => props.roomId,
			() => {
				nextTick(() => {
					editorRef.value?.editor?.commands.focus();
				});
			},
		);

		// Focus editor when a reply is initiated
		watch(
			() => props.replyMessage,
			(val) => {
				if (val) {
					nextTick(() => {
						editorRef.value?.editor?.commands.focus();
					});
				}
			},
		);

		return {
			editorRef,
			fileInputRef,
			editorContent,
			currentHtml,
			files,
			isEmpty,
			truncatedReplyContent,
			starterkitOptions,
			onEditorChange,
			handleKeydown,
			sendMessage,
			triggerFileUpload,
			onFileSelect,
			removeFile,
			__,
		};
	},
});
</script>

<style>
/* ============================================
   Chat Footer Styles
   ============================================ */

.chat-footer-wrapper {
	border-top: 1px solid var(--chat-border-color, #e1e4e8);
	background: var(--chat-footer-bg, #f8f9fa);
	padding: 8px 12px;
}

.chat-dark .chat-footer-wrapper,
.chat-footer-wrapper.chat-dark {
	--chat-footer-bg: #1e1e1e;
	--chat-border-color: #333;
}

/* Reply preview */
.reply-preview {
	display: flex;
	align-items: flex-start;
	gap: 8px;
	padding: 8px;
	margin-bottom: 8px;
	background: var(--chat-reply-bg, #e8f4fd);
	border-radius: 6px;
}

.chat-dark .reply-preview {
	--chat-reply-bg: #2d3748;
}

.reply-preview-bar {
	width: 3px;
	min-height: 100%;
	align-self: stretch;
	background: #1976d2;
	border-radius: 2px;
	flex-shrink: 0;
}

.reply-preview-content {
	flex: 1;
	min-width: 0;
	overflow: hidden;
}

.reply-preview-sender {
	font-size: 12px;
	font-weight: 600;
	color: #1976d2;
	display: block;
	margin-bottom: 2px;
}

.reply-preview-text {
	margin: 0;
	font-size: 13px;
	color: var(--chat-text-muted, #666);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.chat-dark .reply-preview-text {
	--chat-text-muted: #a0aec0;
}

.reply-preview-close {
	background: none;
	border: none;
	font-size: 18px;
	cursor: pointer;
	color: var(--chat-text-muted, #666);
	padding: 0 4px;
	line-height: 1;
	flex-shrink: 0;
}

.reply-preview-close:hover {
	color: #dc3545;
}

/* File previews */
.file-preview-list {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
	margin-bottom: 8px;
}

.file-preview-item {
	display: flex;
	align-items: center;
	gap: 6px;
	padding: 4px 8px;
	background: var(--chat-file-bg, #e9ecef);
	border-radius: 6px;
	font-size: 13px;
}

.chat-dark .file-preview-item {
	--chat-file-bg: #2d3748;
}

.file-preview-thumb {
	width: 28px;
	height: 28px;
	object-fit: cover;
	border-radius: 4px;
}

.file-preview-icon {
	font-size: 16px;
}

.file-preview-name {
	max-width: 120px;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	color: var(--chat-text-color, #333);
}

.chat-dark .file-preview-name {
	--chat-text-color: #e2e8f0;
}

.file-preview-remove {
	background: none;
	border: none;
	font-size: 16px;
	cursor: pointer;
	color: var(--chat-text-muted, #666);
	padding: 0 2px;
	line-height: 1;
}

.file-preview-remove:hover {
	color: #dc3545;
}

/* Editor + actions row */
.chat-footer-input {
	display: flex;
	align-items: flex-end;
	gap: 8px;
}

.editor-container {
	flex: 1;
	min-width: 0;
	border: 1px solid var(--chat-border-color, #e1e4e8);
	border-radius: 8px;
	overflow: hidden;
	background: var(--chat-input-bg, #fff);
}

.chat-dark .editor-container {
	--chat-input-bg: #2d2d2d;
	--chat-border-color: #444;
}

/* TextEditor overrides for chat context */
.editor-container .chat-editor-content {
	border: none !important;
	outline: none !important;
	max-height: 150px;
	min-height: 36px;
	overflow-y: auto;
	padding: 8px 12px;
	font-size: 14px;
	line-height: 1.4;
}

.editor-container .chat-editor-content .ProseMirror {
	min-height: 20px;
	padding: 0;
	outline: none;
}

.editor-container .chat-editor-content .ProseMirror p {
	margin: 0;
}

.editor-container
	.chat-editor-content
	.ProseMirror
	p.is-editor-empty:first-child::before {
	color: #adb5bd;
	content: attr(data-placeholder);
	float: left;
	height: 0;
	pointer-events: none;
}

/* Chat footer action buttons */
.chat-footer-actions {
	display: flex;
	align-items: center;
	gap: 4px;
	padding-bottom: 4px;
}

.footer-action-btn {
	background: none;
	border: none;
	cursor: pointer;
	padding: 6px;
	border-radius: 6px;
	color: var(--chat-icon-color, #9ca6af);
	transition: all 0.15s ease;
	display: flex;
	align-items: center;
	justify-content: center;
}

.footer-action-btn:hover {
	background: var(--chat-btn-hover-bg, rgba(0, 0, 0, 0.06));
	color: var(--chat-icon-hover-color, #1976d2);
}

.chat-dark .footer-action-btn {
	--chat-icon-color: #bdbdbd;
}

.chat-dark .footer-action-btn:hover {
	--chat-btn-hover-bg: rgba(255, 255, 255, 0.08);
	--chat-icon-hover-color: #64b5f6;
}

.send-btn:not(.send-disabled) {
	color: #1976d2;
}

.send-btn.send-disabled {
	opacity: 0.4;
	cursor: not-allowed;
}

.chat-dark .send-btn:not(.send-disabled) {
	color: #64b5f6;
}

/* Hide TextEditor bubble menu border/fixed menu if accidentally rendered */
.editor-container .text-editor-fixed-menu,
.editor-container [class*="TextEditorFixedMenu"] {
	display: none !important;
}

/* Responsive */
@media (max-width: 768px) {
	.chat-footer-wrapper {
		padding: 6px 8px;
	}

	.editor-container .chat-editor-content {
		max-height: 100px;
		font-size: 16px; /* Prevent zoom on iOS */
	}
}
</style>
