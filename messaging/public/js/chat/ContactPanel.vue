<template>
	<Teleport to="body">
		<Transition name="panel-slide">
			<div v-if="show" class="contact-panel-overlay" @click="$emit('close')">
				<div class="contact-panel" @click.stop>
					<!-- Header -->
					<div class="contact-panel-header">
						<div class="flex items-center gap-3">
							<Avatar
								:image="room?.avatar"
								:label="room?.roomName || '?'"
								size="xl"
							/>
							<div class="flex-1 min-w-0">
								<h3 class="text-lg font-semibold text-ink-gray-9 truncate">
									{{ room?.roomName || __("Unknown") }}
								</h3>
								<p class="text-sm text-ink-gray-5 truncate">
									{{ contactSubtitle }}
								</p>
							</div>
						</div>
						<Button variant="ghost" @click="$emit('close')">
							<template #icon>
								<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
								</svg>
							</template>
						</Button>
					</div>

					<!-- Body -->
					<div class="contact-panel-body">
						<!-- Contact Info Section -->
						<div class="panel-section">
							<h4 class="section-title">{{ __("Contact Information") }}</h4>
							
							<div v-if="room?.emailId" class="info-row">
								<div class="info-icon">
									<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
									</svg>
								</div>
								<div class="info-content">
									<span class="info-label">{{ __("Email") }}</span>
									<a :href="`mailto:${room.emailId}`" class="info-value link">
										{{ room.emailId }}
									</a>
								</div>
							</div>

							<div v-if="room?.phoneNo" class="info-row">
								<div class="info-icon">
									<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
									</svg>
								</div>
								<div class="info-content">
									<span class="info-label">{{ __("Phone") }}</span>
									<a :href="`tel:${room.phoneNo}`" class="info-value link">
										{{ room.phoneNo }}
									</a>
								</div>
							</div>

							<div class="info-row">
								<div class="info-icon">
									<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
									</svg>
								</div>
								<div class="info-content">
									<span class="info-label">{{ __("Medium") }}</span>
									<Badge :theme="mediumBadgeTheme">
										{{ room?.communicationMedium || "Email" }}
									</Badge>
								</div>
							</div>
						</div>

						<!-- Reference Section -->
						<div v-if="room?.referenceDoctype" class="panel-section">
							<h4 class="section-title">{{ __("Linked Document") }}</h4>
							<div class="info-row">
								<div class="info-icon">
									<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
									</svg>
								</div>
								<div class="info-content">
									<span class="info-label">{{ room.referenceDoctype }}</span>
									<a 
										:href="`/app/${encodeDoctype(room.referenceDoctype)}/${room.referenceName}`"
										class="info-value link"
										target="_blank"
									>
										{{ room.referenceName }}
									</a>
								</div>
							</div>
						</div>

						<!-- Contact Record Section -->
						<div class="panel-section">
							<h4 class="section-title">{{ __("Contact Record") }}</h4>
							<div v-if="room?.contactName" class="info-row">
								<div class="info-icon">
									<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
									</svg>
								</div>
								<div class="info-content">
									<span class="info-label">{{ __("Contact") }}</span>
									<a 
										:href="`/app/contact/${room.contactName}`"
										class="info-value link"
										target="_blank"
									>
										{{ room.contactName }}
									</a>
								</div>
							</div>
							<div v-else class="no-contact-notice">
								<p class="text-sm text-ink-gray-5 mb-3">
									{{ __("No contact record linked to this conversation.") }}
								</p>
								<Button 
									variant="subtle" 
									theme="blue"
									@click="createContact"
								>
									<template #prefix>
										<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
										</svg>
									</template>
									{{ __("Create Contact") }}
								</Button>
							</div>
						</div>
					</div>

					<!-- Footer Actions -->
					<div class="contact-panel-footer">
						<Button 
							v-if="room?.contactName"
							variant="solid" 
							theme="gray"
							class="w-full"
							@click="openContact"
						>
							{{ __("Open Contact") }}
						</Button>
						<Button 
							v-if="room?.emailId"
							variant="outline" 
							theme="gray"
							class="w-full"
							@click="composeEmail"
						>
							<template #prefix>
								<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
								</svg>
							</template>
							{{ __("Send Email") }}
						</Button>
					</div>
				</div>
			</div>
		</Transition>
	</Teleport>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Avatar, Button, Badge } from "frappe-ui";
import type { Room } from "./types";

// Frappe globals
declare const frappe: {
	_: (text: string) => string;
	set_route: (...args: string[]) => void;
	new_doc: (doctype: string, options?: Record<string, unknown>) => void;
};

const __ = frappe._;

const props = defineProps<{
	show: boolean;
	room: Room | null;
}>();

const emit = defineEmits<{
	(e: "close"): void;
}>();

const contactSubtitle = computed(() => {
	if (props.room?.emailId) return props.room.emailId;
	if (props.room?.phoneNo) return props.room.phoneNo;
	return props.room?.communicationMedium || "";
});

const mediumBadgeTheme = computed(() => {
	const medium = props.room?.communicationMedium;
	switch (medium) {
		case "Email":
			return "blue";
		case "SMS":
			return "green";
		case "Phone":
			return "orange";
		default:
			return "gray";
	}
});

function encodeDoctype(doctype: string): string {
	return doctype.toLowerCase().replace(/ /g, "-");
}

function openContact(): void {
	if (props.room?.contactName) {
		frappe.set_route("Form", "Contact", props.room.contactName);
		emit("close");
	}
}

function createContact(): void {
	const options: Record<string, unknown> = {};
	
	if (props.room?.emailId) {
		options.email_ids = [{ email_id: props.room.emailId, is_primary: 1 }];
	}
	if (props.room?.phoneNo) {
		options.phone_nos = [{ phone: props.room.phoneNo, is_primary_phone: 1 }];
	}
	if (props.room?.roomName && !props.room.roomName.includes("@")) {
		// Try to split name into first/last
		const nameParts = props.room.roomName.split(" ");
		if (nameParts.length >= 2) {
			options.first_name = nameParts[0];
			options.last_name = nameParts.slice(1).join(" ");
		} else {
			options.first_name = props.room.roomName;
		}
	}
	
	frappe.new_doc("Contact", options);
	emit("close");
}

function composeEmail(): void {
	if (props.room?.emailId) {
		window.location.href = `mailto:${props.room.emailId}`;
	}
}
</script>

<style scoped>
.contact-panel-overlay {
	position: fixed;
	inset: 0;
	background-color: rgba(0, 0, 0, 0.3);
	z-index: 1050;
	display: flex;
	justify-content: flex-end;
}

.contact-panel {
	width: 380px;
	max-width: 100vw;
	height: 100%;
	background: var(--fg-color, #fff);
	box-shadow: -4px 0 20px rgba(0, 0, 0, 0.15);
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.contact-panel-header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	padding: 1.25rem;
	border-bottom: 1px solid var(--border-color, #e5e7eb);
	background: var(--subtle-fg, #f9fafb);
}

.contact-panel-body {
	flex: 1;
	overflow-y: auto;
	padding: 1rem;
}

.contact-panel-footer {
	padding: 1rem;
	border-top: 1px solid var(--border-color, #e5e7eb);
	display: flex;
	flex-direction: column;
	gap: 0.5rem;
}

.panel-section {
	margin-bottom: 1.5rem;
}

.section-title {
	font-size: 0.75rem;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	color: var(--text-muted, #6b7280);
	margin-bottom: 0.75rem;
}

.info-row {
	display: flex;
	align-items: flex-start;
	gap: 0.75rem;
	padding: 0.5rem 0;
}

.info-icon {
	flex-shrink: 0;
	width: 2rem;
	height: 2rem;
	display: flex;
	align-items: center;
	justify-content: center;
	background: var(--subtle-fg, #f3f4f6);
	border-radius: 0.375rem;
	color: var(--text-muted, #6b7280);
}

.info-content {
	flex: 1;
	min-width: 0;
}

.info-label {
	display: block;
	font-size: 0.75rem;
	color: var(--text-muted, #6b7280);
	margin-bottom: 0.125rem;
}

.info-value {
	display: block;
	font-size: 0.875rem;
	color: var(--text-color, #111827);
	word-break: break-word;
}

.info-value.link {
	color: var(--primary, #2490ef);
	text-decoration: none;
}

.info-value.link:hover {
	text-decoration: underline;
}

.no-contact-notice {
	padding: 1rem;
	background: var(--subtle-fg, #f9fafb);
	border-radius: 0.5rem;
	text-align: center;
}

/* Slide transition */
.panel-slide-enter-active,
.panel-slide-leave-active {
	transition: opacity 0.2s ease, transform 0.2s ease;
}

.panel-slide-enter-active .contact-panel,
.panel-slide-leave-active .contact-panel {
	transition: transform 0.25s ease;
}

.panel-slide-enter-from,
.panel-slide-leave-to {
	opacity: 0;
}

.panel-slide-enter-from .contact-panel,
.panel-slide-leave-to .contact-panel {
	transform: translateX(100%);
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
	.contact-panel {
		background: var(--fg-color, #1f2937);
	}
	
	.contact-panel-header {
		background: var(--subtle-fg, #111827);
		border-color: var(--border-color, #374151);
	}
	
	.contact-panel-footer {
		border-color: var(--border-color, #374151);
	}
	
	.info-icon {
		background: var(--subtle-fg, #374151);
	}
	
	.no-contact-notice {
		background: var(--subtle-fg, #374151);
	}
}
</style>
