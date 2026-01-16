// Copyright (c) 2025, Avunu LLC
// License: MIT. See LICENSE

import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';

export default defineConfig({
  plugins: [vue()],
  build: {
    // Use rollupOptions for more control over output
    rollupOptions: {
      input: path.resolve(__dirname, 'messaging/public/js/chat/bundle.ts'),
      output: {
        // Fixed filename - use query string for cache busting via Frappe's build_version
        entryFileNames: 'chat.bundle.js',
        assetFileNames: 'chat.bundle.css',
        format: 'iife',
        name: 'MessagingChat',
        inlineDynamicImports: true,
        exports: 'named',
      },
    },
    // Output to dist folder (similar to frappe_editor)
    outDir: 'messaging/public/dist',
    emptyOutDir: true,
    minify: true,
    target: 'es2020',
    sourcemap: false,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'messaging/public/js'),
      vue: 'vue/dist/vue.esm-bundler.js',
    },
  },
  define: {
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'production'),
    __VUE_OPTIONS_API__: true,
    __VUE_PROD_DEVTOOLS__: false,
    __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: false,
  },
  optimizeDeps: {
    include: ['vue', 'vue-advanced-chat'],
  },
});
