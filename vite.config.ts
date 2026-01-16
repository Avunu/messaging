// Copyright (c) 2025, Avunu LLC
// License: MIT. See LICENSE

import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';

export default defineConfig({
  plugins: [vue()],
  build: {
    lib: {
      entry: path.resolve(__dirname, 'messaging/public/js/chat.bundle.ts'),
      name: 'MessagingChat',
      fileName: 'chat.bundle',
      formats: ['iife'],
    },
    outDir: 'messaging/public/dist',
    emptyOutDir: true,
    minify: true,
    target: 'es2020',
    rollupOptions: {
      // Make sure to externalize deps that shouldn't be bundled
      external: [],
      output: {
        // Global variables for externalized deps
        globals: {},
        assetFileNames: 'chat.css',
        // Ensure single file output
        inlineDynamicImports: true,
        // Suppress warning about named + default exports
        exports: 'named',
      },
    },
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
