<template>
	<Teleport to="body">
		<Transition name="panel-slide">
			<div
				v-if="show"
				class="contact-panel-overlay"
				@click="$emit('close')"
			>
				<div class="contact-panel" @click.stop>
					<!-- Header -->
					<div class="contact-panel-header">
						<div class="header-info">
							<div class="avatar-wrapper">
								<img
									v-if="room?.avatar"
									:src="room.avatar"
									:alt="room?.roomName"
									class="avatar-img"
								/>
								<span v-else class="avatar-placeholder">{{
									avatarInitial
								}}</span>
							</div>
							<div class="header-text">
								<h3 class="panel-title">
									{{ room?.roomName || __("Unknown") }}
								</h3>
								<p class="panel-subtitle">
									{{ contactSubtitle }}
								</p>
							</div>
						</div>
						<button
							class="close-btn"
							@click="$emit('close')"
							:title="__('Close')"
						>
							<svg
								class="icon"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M6 18L18 6M6 6l12 12"
								/>
							</svg>
						</button>
					</div>

					<!-- Body -->
					<div class="contact-panel-body">
						<!-- Contact Info Section -->
						<div class="panel-section">
							<h4 class="section-title">
								{{ __("Contact Information") }}
							</h4>

							<!-- Loading state -->
							<div
								v-if="loadingContact && room?.contactName"
								class="loading-state"
							>
								<div class="spinner"></div>
								<span>{{ __("Loading...") }}</span>
							</div>

							<!-- Contact details from Contact record -->
							<template v-else-if="hasContactInfo">
								<!-- All Email Addresses -->
								<div
									v-for="(emailInfo, idx) in allEmails"
									:key="`email-${idx}`"
									class="info-row"
								>
									<div class="info-icon">
										<svg
											class="icon"
											fill="none"
											stroke="currentColor"
											viewBox="0 0 24 24"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
											/>
										</svg>
									</div>
									<div class="info-content">
										<span class="info-label">
											{{ __("Email") }}
											<span
												v-if="emailInfo.isPrimary"
												class="primary-badge"
												>{{ __("Primary") }}</span
											>
										</span>
										<a
											:href="`mailto:${emailInfo.email}`"
											class="info-value link"
										>
											{{ emailInfo.email }}
										</a>
									</div>
								</div>

								<!-- All Phone Numbers -->
								<div
									v-for="(phoneInfo, idx) in allPhones"
									:key="`phone-${idx}`"
									class="info-row"
								>
									<div class="info-icon">
										<svg
											class="icon"
											fill="none"
											stroke="currentColor"
											viewBox="0 0 24 24"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
											/>
										</svg>
									</div>
									<div class="info-content">
										<span class="info-label">
											{{
												phoneInfo.isMobile
													? __("Mobile")
													: __("Phone")
											}}
											<span
												v-if="phoneInfo.isPrimary"
												class="primary-badge"
												>{{ __("Primary") }}</span
											>
										</span>
										<a
											:href="`tel:${phoneInfo.phone}`"
											class="info-value link"
										>
											{{ phoneInfo.phone }}
										</a>
									</div>
								</div>
							</template>

							<!-- Fallback to room data if no contact record -->
							<template v-else>
								<div v-if="room?.emailId" class="info-row">
									<div class="info-icon">
										<svg
											class="icon"
											fill="none"
											stroke="currentColor"
											viewBox="0 0 24 24"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
											/>
										</svg>
									</div>
									<div class="info-content">
										<span class="info-label">{{
											__("Email")
										}}</span>
										<a
											:href="`mailto:${room.emailId}`"
											class="info-value link"
										>
											{{ room.emailId }}
										</a>
									</div>
								</div>

								<div v-if="room?.phoneNo" class="info-row">
									<div class="info-icon">
										<svg
											class="icon"
											fill="none"
											stroke="currentColor"
											viewBox="0 0 24 24"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
											/>
										</svg>
									</div>
									<div class="info-content">
										<span class="info-label">{{
											__("Phone")
										}}</span>
										<a
											:href="`tel:${room.phoneNo}`"
											class="info-value link"
										>
											{{ room.phoneNo }}
										</a>
									</div>
								</div>
							</template>

							<!-- Current Thread Medium -->
							<div class="info-row">
								<div class="info-icon">
									<svg
										class="icon"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
										/>
									</svg>
								</div>
								<div class="info-content">
									<span class="info-label">{{
										__("Current Thread")
									}}</span>
									<span
										class="badge"
										:class="mediumBadgeClass"
									>
										{{
											room?.communicationMedium || "Email"
										}}
									</span>
								</div>
							</div>
						</div>

						<!-- Reference Section -->
						<div
							v-if="room?.referenceDoctype"
							class="panel-section"
						>
							<h4 class="section-title">
								{{ __("Linked Document") }}
							</h4>
							<div class="info-row">
								<div class="info-icon">
									<svg
										class="icon"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
										/>
									</svg>
								</div>
								<div class="info-content">
									<span class="info-label">{{
										room.referenceDoctype
									}}</span>
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
							<h4 class="section-title">
								{{ __("Contact Record") }}
							</h4>
							<div v-if="room?.contactName" class="info-row">
								<div class="info-icon">
									<svg
										class="icon"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
										/>
									</svg>
								</div>
								<div class="info-content">
									<span class="info-label">{{
										__("Contact")
									}}</span>
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
								<p class="notice-text">
									{{
										__(
											"No contact record linked to this conversation.",
										)
									}}
								</p>
								<button
									class="btn btn-secondary"
									@click="createContact"
								>
									<svg
										class="icon"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M12 4v16m8-8H4"
										/>
									</svg>
									{{ __("Create Contact") }}
								</button>
							</div>
						</div>

						<!-- Linked Documents Section -->
						<div v-if="room?.contactName" class="panel-section">
							<h4 class="section-title">
								{{ __("Linked Documents") }}
							</h4>

							<div v-if="loadingLinked" class="loading-state">
								<div class="spinner"></div>
								<span>{{ __("Loading...") }}</span>
							</div>

							<div v-else-if="hasLinkedDocuments">
								<div
									v-for="group in linkedGroups"
									:key="group"
									class="linked-group"
								>
									<h5 class="group-title">{{ group }}</h5>
									<ul class="linked-list">
										<li
											v-for="doc in linkedDocuments[
												group
											]"
											:key="`${doc.doctype}-${doc.name}`"
											class="linked-item"
										>
											<div class="info-icon small">
												<svg
													class="icon"
													fill="none"
													stroke="currentColor"
													viewBox="0 0 24 24"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
													/>
												</svg>
											</div>
											<div class="linked-content">
												<span class="linked-doctype">{{
													doc.doctype
												}}</span>
												<a
													:href="`/app/${encodeDoctype(doc.doctype)}/${doc.name}`"
													class="linked-link"
													target="_blank"
												>
													{{ doc.title || doc.name }}
												</a>
											</div>
										</li>
									</ul>
								</div>
							</div>

							<div v-else class="no-linked-notice">
								<p class="notice-text">
									{{ __("No linked documents found.") }}
								</p>
							</div>
						</div>
					</div>

					<!-- Footer Actions -->
					<div class="contact-panel-footer">
						<button
							v-if="room?.contactName"
							class="btn btn-primary"
							@click="openContact"
						>
							{{ __("Open Contact") }}
						</button>
						<button
							v-if="room?.emailId"
							class="btn btn-secondary"
							@click="composeEmail"
						>
							<svg
								class="icon"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
								/>
							</svg>
							{{ __("Send Email") }}
						</button>
					</div>
				</div>
			</div>
		</Transition>
	</Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { Room } from "./types";

// Frappe globals
declare const frappe: {
	_: (text: string) => string;
	set_route: (...args: string[]) => void;
	new_doc: (doctype: string, options?: Record<string, unknown>) => void;
	call: <T>(options: {
		method: string;
		args?: Record<string, unknown>;
		async?: boolean;
		freeze?: boolean;
	}) => Promise<{ message: T }>;
};

const __ = frappe._;

interface LinkedDoc {
	doctype: string;
	name: string;
	title: string;
}

interface ContactEmail {
	email_id: string;
	is_primary: 0 | 1;
}

interface ContactPhone {
	phone: string;
	is_primary_phone: 0 | 1;
	is_primary_mobile_no: 0 | 1;
}

interface ContactDetails {
	name: string;
	full_name: string;
	first_name: string;
	last_name: string;
	email_id: string;
	phone: string;
	mobile_no: string;
	email_ids: ContactEmail[];
	phone_nos: ContactPhone[];
	company_name: string;
	designation: string;
	address: string;
	image: string;
}

type LinkedDocuments = Record<string, LinkedDoc[]>;

const props = defineProps<{
	show: boolean;
	room: Room | null;
}>();

const emit = defineEmits<{
	(e: "close"): void;
}>();

// Linked documents state
const linkedDocuments = ref<LinkedDocuments>({});
const loadingLinked = ref(false);

// Contact details state
const contactDetails = ref<ContactDetails | null>(null);
const loadingContact = ref(false);

// Watch for room changes to fetch contact details and linked documents
watch(
	() => props.room?.contactName,
	async (contactName) => {
		linkedDocuments.value = {};
		contactDetails.value = null;
		if (!contactName) return;

		// Fetch contact details and linked documents in parallel
		loadingLinked.value = true;
		loadingContact.value = true;

		const [linkedResponse, contactResponse] = await Promise.allSettled([
			frappe.call<LinkedDocuments>({
				method: "messaging.messaging.api.chat.links.get_linked_documents",
				args: {
					doctype: "Contact",
					docname: contactName,
				},
			}),
			frappe.call<ContactDetails>({
				method: "frappe.client.get",
				args: {
					doctype: "Contact",
					name: contactName,
				},
			}),
		]);

		if (linkedResponse.status === "fulfilled") {
			linkedDocuments.value = linkedResponse.value.message || {};
		} else {
			console.error(
				"Error fetching linked documents:",
				linkedResponse.reason,
			);
		}
		loadingLinked.value = false;

		if (contactResponse.status === "fulfilled") {
			contactDetails.value = contactResponse.value.message || null;
		} else {
			console.error(
				"Error fetching contact details:",
				contactResponse.reason,
			);
		}
		loadingContact.value = false;
	},
	{ immediate: true },
);

// Computed properties for contact info
const allEmails = computed(() => {
	if (!contactDetails.value) return [];
	const emails: { email: string; isPrimary: boolean }[] = [];

	// Add emails from email_ids child table
	if (contactDetails.value.email_ids?.length) {
		for (const e of contactDetails.value.email_ids) {
			emails.push({ email: e.email_id, isPrimary: !!e.is_primary });
		}
	}

	// Sort primary first
	return emails.sort((a, b) => (b.isPrimary ? 1 : 0) - (a.isPrimary ? 1 : 0));
});

const allPhones = computed(() => {
	if (!contactDetails.value) return [];
	const phones: { phone: string; isPrimary: boolean; isMobile: boolean }[] =
		[];

	// Add phones from phone_nos child table
	if (contactDetails.value.phone_nos?.length) {
		for (const p of contactDetails.value.phone_nos) {
			phones.push({
				phone: p.phone,
				isPrimary: !!p.is_primary_phone,
				isMobile: !!p.is_primary_mobile_no,
			});
		}
	}

	// Sort primary first, then mobile
	return phones.sort((a, b) => {
		if (b.isPrimary !== a.isPrimary) return b.isPrimary ? 1 : -1;
		if (b.isMobile !== a.isMobile) return b.isMobile ? 1 : -1;
		return 0;
	});
});

const hasContactInfo = computed(() => {
	return allEmails.value.length > 0 || allPhones.value.length > 0;
});

const linkedGroups = computed(() => Object.keys(linkedDocuments.value).sort());
const hasLinkedDocuments = computed(() => linkedGroups.value.length > 0);

const avatarInitial = computed(() => {
	const name = props.room?.roomName || "?";
	return name.charAt(0).toUpperCase();
});

const contactSubtitle = computed(() => {
	if (props.room?.emailId) return props.room.emailId;
	if (props.room?.phoneNo) return props.room.phoneNo;
	return props.room?.communicationMedium || "";
});

const mediumBadgeClass = computed(() => {
	const medium = props.room?.communicationMedium;
	switch (medium) {
		case "Email":
			return "badge-blue";
		case "SMS":
			return "badge-green";
		case "Phone":
			return "badge-orange";
		default:
			return "badge-gray";
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
		options.phone_nos = [
			{ phone: props.room.phoneNo, is_primary_phone: 1 },
		];
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
	background-color: var(--black-overlay-300);
	z-index: 1050;
	display: flex;
	justify-content: flex-end;
}

.contact-panel {
	width: 380px;
	max-width: 100vw;
	height: 100%;
	background: var(--fg-color);
	box-shadow: var(--shadow-lg);
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.contact-panel-header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	padding: 1.25rem;
	border-bottom: 1px solid var(--border-color);
	background: var(--subtle-fg);
}

.header-info {
	display: flex;
	align-items: center;
	gap: 0.75rem;
	min-width: 0;
	flex: 1;
}

.avatar-wrapper {
	width: 48px;
	height: 48px;
	border-radius: var(--border-radius-full);
	overflow: hidden;
	flex-shrink: 0;
	background: var(--surface-gray-2);
}

.avatar-img {
	width: 100%;
	height: 100%;
	object-fit: cover;
}

.avatar-placeholder {
	width: 100%;
	height: 100%;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: var(--text-2xl);
	font-weight: var(--weight-semibold);
	color: var(--text-muted);
	background: var(--surface-gray-2);
}

.header-text {
	min-width: 0;
	flex: 1;
}

.panel-title {
	font-size: var(--text-xl);
	font-weight: var(--weight-semibold);
	color: var(--text-color);
	margin: 0 0 0.25rem 0;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.panel-subtitle {
	font-size: var(--text-md);
	color: var(--text-muted);
	margin: 0;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.close-btn {
	background: transparent;
	border: none;
	padding: 0.5rem;
	cursor: pointer;
	border-radius: var(--border-radius);
	color: var(--text-muted);
	transition:
		background-color 0.15s,
		color 0.15s;
}

.close-btn:hover {
	background: var(--fg-hover-color);
	color: var(--text-color);
}

.contact-panel-body {
	flex: 1;
	overflow-y: auto;
	padding: 1rem;
}

.contact-panel-footer {
	padding: 1rem;
	border-top: 1px solid var(--border-color);
	display: flex;
	flex-direction: column;
	gap: 0.5rem;
}

.panel-section {
	margin-bottom: 1.5rem;
}

.section-title {
	font-size: var(--text-xs);
	font-weight: var(--weight-semibold);
	text-transform: uppercase;
	letter-spacing: 0.05em;
	color: var(--text-muted);
	margin: 0 0 0.75rem 0;
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
	background: var(--subtle-fg);
	border-radius: var(--border-radius);
	color: var(--text-muted);
}

.icon {
	width: 1rem;
	height: 1rem;
}

.info-content {
	flex: 1;
	min-width: 0;
}

.info-label {
	display: flex;
	align-items: center;
	gap: 0.375rem;
	font-size: var(--text-xs);
	color: var(--text-muted);
	margin-bottom: 0.125rem;
}

.primary-badge {
	display: inline-block;
	padding: 0.0625rem 0.375rem;
	border-radius: var(--border-radius-tiny);
	font-size: 0.625rem;
	font-weight: var(--weight-semibold);
	text-transform: uppercase;
	letter-spacing: 0.025em;
	background: var(--blue-100);
	color: var(--primary);
}

.info-value {
	display: block;
	font-size: var(--text-md);
	color: var(--text-color);
	word-break: break-word;
}

.info-value.link {
	color: var(--primary);
	text-decoration: none;
}

.info-value.link:hover {
	text-decoration: underline;
}

.badge {
	display: inline-block;
	padding: 0.125rem 0.5rem;
	border-radius: var(--border-radius-full);
	font-size: var(--text-xs);
	font-weight: var(--weight-medium);
}

.badge-blue {
	background: var(--bg-blue);
	color: var(--text-on-blue);
}

.badge-green {
	background: var(--bg-green);
	color: var(--text-on-green);
}

.badge-orange {
	background: var(--bg-orange);
	color: var(--text-on-orange);
}

.badge-gray {
	background: var(--bg-gray);
	color: var(--text-on-gray);
}

.no-contact-notice {
	padding: 1rem;
	background: var(--subtle-fg);
	border-radius: var(--border-radius);
	text-align: center;
}

.notice-text {
	font-size: var(--text-md);
	color: var(--text-muted);
	margin: 0 0 0.75rem 0;
}

/* Buttons */
.btn {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	gap: 0.5rem;
	padding: 0.5rem 1rem;
	font-size: var(--text-md);
	font-weight: var(--weight-medium);
	border-radius: var(--border-radius);
	cursor: pointer;
	transition:
		background-color 0.15s,
		border-color 0.15s;
	border: 1px solid transparent;
	width: 100%;
}

.btn .icon {
	width: 1rem;
	height: 1rem;
}

.btn-primary {
	background: var(--primary);
	color: var(--white);
	border-color: var(--primary);
}

.btn-primary:hover {
	background: var(--blue-600);
	border-color: var(--blue-600);
}

.btn-secondary {
	background: var(--fg-color);
	color: var(--text-color);
	border-color: var(--border-color);
}

.btn-secondary:hover {
	background: var(--subtle-fg);
	border-color: var(--border-color);
}

/* Slide transition */
.panel-slide-enter-active,
.panel-slide-leave-active {
	transition: opacity 0.2s ease;
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

/* Linked Documents */
.linked-group {
	margin-bottom: 1rem;
}

.linked-group:last-child {
	margin-bottom: 0;
}

.group-title {
	font-size: var(--text-sm);
	font-weight: var(--weight-semibold);
	color: var(--text-color);
	margin: 0 0 0.5rem 0;
	padding-bottom: 0.25rem;
	border-bottom: 1px solid var(--border-color);
}

.linked-list {
	list-style: none;
	padding: 0;
	margin: 0;
}

.linked-item {
	display: flex;
	align-items: flex-start;
	gap: 0.5rem;
	padding: 0.375rem 0;
}

.linked-item:not(:last-child) {
	border-bottom: 1px solid var(--border-color);
}

.info-icon.small {
	width: 1.5rem;
	height: 1.5rem;
}

.info-icon.small .icon {
	width: 0.875rem;
	height: 0.875rem;
}

.linked-content {
	flex: 1;
	min-width: 0;
}

.linked-doctype {
	display: block;
	font-size: var(--text-tiny);
	color: var(--text-muted);
	text-transform: uppercase;
	letter-spacing: 0.025em;
}

.linked-link {
	display: block;
	font-size: var(--text-sm);
	color: var(--primary);
	text-decoration: none;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.linked-link:hover {
	text-decoration: underline;
}

.no-linked-notice {
	padding: 0.75rem;
	background: var(--subtle-fg);
	border-radius: var(--border-radius);
	text-align: center;
}

.no-linked-notice .notice-text {
	margin: 0;
	font-size: var(--text-sm);
}

/* Loading state */
.loading-state {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 0.5rem;
	padding: 1rem;
	color: var(--text-muted);
	font-size: var(--text-md);
}

.spinner {
	width: 1rem;
	height: 1rem;
	border: 2px solid var(--border-color);
	border-top-color: var(--primary);
	border-radius: var(--border-radius-full);
	animation: spin 0.8s linear infinite;
}

@keyframes spin {
	to {
		transform: rotate(360deg);
	}
}
</style>
