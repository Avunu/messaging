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
          // emoji-picker is a web component from emoji-picker-element
          // (used internally by vue-advanced-chat's RoomFooter, still mounted but hidden)
          isCustomElement: (tag: string) => tag === 'emoji-picker',
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
    // Add .vue to resolvable extensions for vendor source imports (upstream omits extensions)
    extensions: ['.mjs', '.js', '.mts', '.ts', '.jsx', '.tsx', '.json', '.vue'],
    alias: {
      '@': path.resolve(__dirname, 'messaging/public/js'),
      // Import vue-advanced-chat sub-components directly from vendor submodule source
      '@vendor-chat': path.resolve(__dirname, 'vendor/vue-advanced-chat/src'),
      vue: 'vue/dist/vue.esm-bundler.js',
    },
  },
  define: {
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'production'),
    __VUE_OPTIONS_API__: true,
    __VUE_PROD_DEVTOOLS__: false,
    __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: false,
  },
  css: {
    preprocessorOptions: {
      scss: {
        // Suppress Sass @import deprecation warnings from upstream vue-advanced-chat SCSS
        silenceDeprecations: ['import'],
      },
    },
  },
  optimizeDeps: {
    include: ['vue', 'frappe-ui'],
  },
});
