<template>
	<div v-if="roomId" class="chat-footer-wrapper" :class="{ 'chat-dark': isDark }">
		<!-- Reply preview -->
		<div v-if="replyMessage" class="reply-preview">
			<div class="reply-preview-bar" />
			<div class="reply-preview-content">
				<span class="reply-preview-sender">{{ replyMessage.username || replyMessage.senderId }}</span>
				<p class="reply-preview-text" v-html="truncatedReplyContent" />
			</div>
			<button class="reply-preview-close" @click="$emit('clear-reply')" :title="__('Cancel reply')">
				&times;
			</button>
		</div>

		<!-- File previews -->
		<div v-if="files.length" class="file-preview-list">
			<div v-for="(file, index) in files" :key="index" class="file-preview-item">
				<img
					v-if="file.preview && file.type?.startsWith('image/')"
					:src="file.preview"
					class="file-preview-thumb"
					alt=""
				/>
				<span v-else class="file-preview-icon">📎</span>
				<span class="file-preview-name">{{ file.name }}</span>
				<button class="file-preview-remove" @click="removeFile(index)">&times;</button>
			</div>
		</div>

		<!-- Editor + actions row -->
		<div class="chat-footer-input">
			<div class="editor-container" @keydown="handleKeydown">
				<Editor
					ref="editorRef"
					v-model="editorContent"
					:extensions="extensions"
					:placeholder="placeholder"
					@change="onEditorChange"
				>
					<EditorContent class="chat-editor-content" />
				</Editor>
			</div>
			<div class="chat-footer-actions">
				<button class="footer-action-btn attach-btn" @click="triggerFileUpload" :title="__('Attach file')">
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
			<input ref="fileInputRef" type="file" multiple style="display: none" @change="onFileSelect" />
		</div>
	</div>
</template>

<script lang="ts">
import { defineComponent, ref, computed, watch, nextTick } from "vue";
import { Editor, EditorContent, Link, Placeholder, StarterKit } from "frappe-ui/editor";
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
		Editor,
		EditorContent,
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
		const editorRef = ref<InstanceType<typeof Editor> | null>(null);
		const fileInputRef = ref<HTMLInputElement | null>(null);
		const editorContent = ref("");
		const currentHtml = ref("");
		const files = ref<FileWithPreview[]>([]);

		// Bold, italic, lists, quotes and links: no headings (not useful in chat). frappe-ui's
		// StarterKit has no code blocks, and its editor shows no toolbar unless asked to.
		const extensions = [StarterKit.configure({ heading: false }), Placeholder, Link];

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

		function onEditorChange(html: string | null): void {
			currentHtml.value = html ?? "";
			emit("typing", stripHtml(currentHtml.value).trim());
		}

		function handleKeydown(e: KeyboardEvent): void {
			// Enter without Shift sends the message
			if (e.key === "Enter" && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
				// Don't intercept if an autocomplete/suggestion popup is open
				// (TipTap slash commands, mentions, etc.)
				if (editorRef.value?.editor) {
					const popup = document.querySelector(".tippy-box, .suggestion-list, .slash-commands-list");
					if (popup) return; // Let the suggestion handle Enter
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
					reader.addEventListener("load", (e) => {
						filePreview.preview = e.target?.result as string;
						// Trigger reactivity
						files.value = [...files.value];
					});
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
			extensions,
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
	/* Private --chat-* token layer, defined once as Frappe equivalents so it
	   follows the active theme automatically (no .chat-dark overrides). */
	--chat-footer-bg: var(--card-bg);
	--chat-input-bg: var(--control-bg);
	--chat-file-bg: var(--subtle-fg);
	--chat-reply-bg: var(--surface-gray-2);
	--chat-text-color: var(--text-color);
	--chat-text-muted: var(--text-muted);
	--chat-border-color: var(--border-color);
	--chat-icon-color: var(--text-muted);
	--chat-icon-hover-color: var(--text-color);
	--chat-btn-hover-bg: var(--fg-hover-color);

	border-top: 1px solid var(--chat-border-color);
	background: var(--chat-footer-bg);
	padding: 8px 12px;
}

/* Reply preview */
.reply-preview {
	display: flex;
	align-items: flex-start;
	gap: 8px;
	padding: 8px;
	margin-bottom: 8px;
	background: var(--chat-reply-bg);
	border-radius: var(--border-radius);
}

.reply-preview-bar {
	width: 3px;
	min-height: 100%;
	align-self: stretch;
	background: var(--primary);
	border-radius: 2px;
	flex-shrink: 0;
}

.reply-preview-content {
	flex: 1;
	min-width: 0;
	overflow: hidden;
}

.reply-preview-sender {
	font-size: var(--text-xs);
	font-weight: var(--weight-semibold);
	color: var(--primary);
	display: block;
	margin-bottom: 2px;
}

.reply-preview-text {
	margin: 0;
	font-size: var(--text-sm);
	color: var(--chat-text-muted);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.reply-preview-close {
	background: none;
	border: none;
	font-size: var(--text-xl);
	cursor: pointer;
	color: var(--chat-text-muted);
	padding: 0 4px;
	line-height: 1;
	flex-shrink: 0;
}

.reply-preview-close:hover {
	color: var(--red-500);
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
	background: var(--chat-file-bg);
	border-radius: var(--border-radius);
	font-size: var(--text-sm);
}

.file-preview-thumb {
	width: 28px;
	height: 28px;
	object-fit: cover;
	border-radius: var(--border-radius-tiny);
}

.file-preview-icon {
	font-size: var(--text-lg);
}

.file-preview-name {
	max-width: 120px;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	color: var(--chat-text-color);
}

.file-preview-remove {
	background: none;
	border: none;
	font-size: var(--text-lg);
	cursor: pointer;
	color: var(--chat-text-muted);
	padding: 0 2px;
	line-height: 1;
}

.file-preview-remove:hover {
	color: var(--red-500);
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
	border: 1px solid var(--chat-border-color);
	border-radius: var(--border-radius);
	overflow: hidden;
	background: var(--chat-input-bg);
}

/* Editor overrides for chat context */
.editor-container .chat-editor-content {
	border: none !important;
	outline: none !important;
	max-height: 150px;
	min-height: 36px;
	overflow-y: auto;
	padding: 8px 12px;
	font-size: var(--text-md);
	line-height: 1.4;
}

.editor-container .chat-editor-content .ProseMirror {
	min-height: 20px;
	max-width: none !important;
	padding: 0;
	outline: none;
}

.editor-container .chat-editor-content .ProseMirror p {
	margin: 0;
}

.editor-container .chat-editor-content .ProseMirror p.is-editor-empty:first-child::before {
	color: var(--text-light);
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
	border-radius: var(--border-radius);
	color: var(--chat-icon-color);
	transition: all 0.15s ease;
	display: flex;
	align-items: center;
	justify-content: center;
}

.footer-action-btn:hover {
	background: var(--chat-btn-hover-bg);
	color: var(--chat-icon-hover-color);
}

.send-btn:not(.send-disabled) {
	color: var(--primary);
}

.send-btn.send-disabled {
	opacity: 0.4;
	cursor: not-allowed;
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
