// Copyright (c) 2026, Avunu LLC and contributors
// For license information, please see license.txt

// Tailwind CSS v3 config for frappe-ui component styling
// Uses frappe-ui's preset for semantic colors, typography, etc.
import frappeUIPreset from "frappe-ui/tailwind";

/** @type {import('tailwindcss').Config} */
export default {
	presets: [frappeUIPreset],
	content: [
		// Our own components that may use Tailwind classes
		"./messaging/public/js/**/*.{vue,js,ts,jsx,tsx}",
		// frappe-ui's editor (the chat footer's), so the utility classes its sources use are generated
		"./node_modules/frappe-ui/src/molecules/editor/**/*.{vue,js,ts,jsx,tsx}",
		// TipTap extensions that may reference Tailwind classes
		"./node_modules/@tiptap/**/*.{vue,js,ts,jsx,tsx}",
	],
	theme: { extend: {} },
	plugins: [],
	// Win specificity when embedded inside Frappe desk
	important: true,
};
