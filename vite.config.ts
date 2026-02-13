// Copyright (c) 2025, Avunu LLC
// License: MIT. See LICENSE

import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';
import Icons from 'unplugin-icons/vite';

export default defineConfig({
  plugins: [
    vue({
      template: {
        compilerOptions: {
          // Treat vue-advanced-chat and emoji-picker as custom elements (web components)
          isCustomElement: (tag: string) =>
            tag === 'vue-advanced-chat' || tag === 'emoji-picker',
        },
      },
    }),
    Icons({
      compiler: 'vue3',
    }),
  ],
  build: {
    // Use rollupOptions for more control over output
    rollupOptions: {
      input: path.resolve(__dirname, 'messaging/public/js/chat/bundle.ts'),
      output: {
        // Use hash in filename for cache busting (mimics esbuild's [name].[hash] pattern)
        entryFileNames: 'js/chat.bundle.[hash].js',
        assetFileNames: 'css/chat.bundle.[hash].[ext]',
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
    sourcemap: true,
    // Extract CSS into separate file (don't inline into JS)
    cssCodeSplit: false,
    // Generate manifest.json for asset mapping
    manifest: true,
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
    include: ['vue', 'vue-advanced-chat', 'frappe-ui'],
  },
});
