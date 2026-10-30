// Copyright (c) 2026, Avunu LLC and contributors
// For license information, please see license.txt

/**
 * Run vue-tsc against TypeScript 5 (the `typescript5` alias).
 *
 * The app's `typescript` dependency is the native TS 7 build, which ships no
 * `lib/tsc` / JS API, and vue-tsc 3 can only drive the JS compiler.
 * Usage: node scripts/vue-tsc.cjs --noEmit [-p tsconfig.json]
 */

process.argv = [process.argv[0], "vue-tsc", ...process.argv.slice(2)];
require("vue-tsc").run(require.resolve("typescript5/lib/tsc"));
