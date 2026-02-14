// Tailwind CSS v3 config for frappe-ui component styling
// Uses frappe-ui's preset for semantic colors, typography, etc.
import frappeUIPreset from "frappe-ui/tailwind";

/** @type {import('tailwindcss').Config} */
export default {
	presets: [frappeUIPreset],
	content: [
		// Our own components that may use Tailwind classes
		"./messaging/public/js/**/*.{vue,js,ts,jsx,tsx}",
		// frappe-ui source components (TextEditor, etc.) — ensures their utility classes are generated
		"./node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}",
		// TipTap extensions that may reference Tailwind classes
		"./node_modules/@tiptap/**/*.{vue,js,ts,jsx,tsx}",
	],
	theme: { extend: {} },
	plugins: [],
	// Win specificity when embedded inside Frappe desk
	important: true,
};
