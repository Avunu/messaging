#!/usr/bin/env ts-node
/**
 * Post-build script to update Frappe's assets.json with Vite build outputs.
 * This mimics Frappe's esbuild cache-busting scheme.
 */

import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

// ES module equivalent of __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

interface ManifestEntry {
    file: string;
    src?: string;
    isEntry?: boolean;
    css?: string[];
    assets?: string[];
}

interface ViteManifest {
    [key: string]: ManifestEntry;
}

interface AssetsJson {
    [key: string]: string;
}

const APP_NAME = 'messaging';
const SITES_PATH = path.resolve(__dirname, '..', '..', 'sites');
const DIST_PATH = path.resolve(__dirname, APP_NAME, 'public', 'dist');
const MANIFEST_PATH = path.resolve(DIST_PATH, '.vite', 'manifest.json');
const ASSETS_JSON_PATH = path.resolve(SITES_PATH, 'assets', 'assets.json');
const ASSETS_DEST_PATH = path.resolve(SITES_PATH, 'assets', APP_NAME, 'dist');

function main(): void {
    // Read Vite manifest
    if (!fs.existsSync(MANIFEST_PATH)) {
        console.error('Vite manifest not found. Run `yarn build` first.');
        process.exit(1);
    }

    const manifest: ViteManifest = JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf-8'));

    // Read existing assets.json
    let assetsJson: AssetsJson = {};
    if (fs.existsSync(ASSETS_JSON_PATH)) {
        assetsJson = JSON.parse(fs.readFileSync(ASSETS_JSON_PATH, 'utf-8'));
    }

    // Ensure destination directory exists
    fs.mkdirSync(ASSETS_DEST_PATH, { recursive: true });
    fs.mkdirSync(path.join(ASSETS_DEST_PATH, 'js'), { recursive: true });
    fs.mkdirSync(path.join(ASSETS_DEST_PATH, 'css'), { recursive: true });

    // Process manifest entries
    for (const [input, entry] of Object.entries(manifest)) {
        if (entry.isEntry) {
            // Handle JS entry
            const jsFile = entry.file;
            const jsSource = path.join(DIST_PATH, jsFile);
            const jsDest = path.join(ASSETS_DEST_PATH, jsFile);

            // Copy JS file
            fs.mkdirSync(path.dirname(jsDest), { recursive: true });
            fs.copyFileSync(jsSource, jsDest);

            // Copy sourcemap if exists
            if (fs.existsSync(jsSource + '.map')) {
                fs.copyFileSync(jsSource + '.map', jsDest + '.map');
            }

            // Update assets.json - map simple name to hashed path
            // e.g., "chat.bundle.js" -> "/assets/messaging/dist/js/chat.bundle.ABC123.js"
            const bundleName = 'chat.bundle.js';
            const assetPath = `/assets/${APP_NAME}/dist/${jsFile}`;
            assetsJson[bundleName] = assetPath;

            console.log(`  ${bundleName} -> ${assetPath}`);

            // Handle CSS if present in entry's css array
            if (entry.css && entry.css.length > 0) {
                for (const cssFile of entry.css) {
                    processCssFile(cssFile, DIST_PATH, ASSETS_DEST_PATH, assetsJson);
                }
            }
        }

        // Handle standalone CSS entries (like "style.css" in the manifest)
        // These are CSS files that aren't associated with a JS entry's css array
        if (!entry.isEntry && entry.file.endsWith('.css')) {
            processCssFile(entry.file, DIST_PATH, ASSETS_DEST_PATH, assetsJson);
        }
    }

    // Write updated assets.json
    fs.writeFileSync(ASSETS_JSON_PATH, JSON.stringify(assetsJson, null, 4));
    console.log(`\nUpdated ${ASSETS_JSON_PATH}`);
}

/**
 * Process and copy a CSS file, updating assets.json
 */
function processCssFile(
    cssFile: string,
    distPath: string,
    assetsDestPath: string,
    assetsJson: AssetsJson
): void {
    const cssSource = path.join(distPath, cssFile);
    const cssDest = path.join(assetsDestPath, cssFile);

    // Only process if source exists
    if (!fs.existsSync(cssSource)) {
        console.warn(`  Warning: CSS file not found: ${cssSource}`);
        return;
    }

    // Copy CSS file
    fs.mkdirSync(path.dirname(cssDest), { recursive: true });
    fs.copyFileSync(cssSource, cssDest);

    // Update assets.json for CSS
    const cssBundleName = 'chat.bundle.css';
    const cssAssetPath = `/assets/${APP_NAME}/dist/${cssFile}`;
    assetsJson[cssBundleName] = cssAssetPath;

    console.log(`  ${cssBundleName} -> ${cssAssetPath}`);
}

main();
