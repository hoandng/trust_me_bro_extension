import { defineConfig, type Plugin } from 'vite';
import { resolve } from 'path';
import { SIDEPANEL_PATH } from './src/shared/config.ts';

const backendUrl = process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000/*';

function manifestPlugin(): Plugin {
  return {
    name: 'manifest-plugin',
    generateBundle() {
      const manifest = {
        manifest_version: 3,
        name: 'Fact Check Extension',
        version: '1.0.0',
        permissions: ['sidePanel', 'storage'],
        host_permissions: ['https://*.reddit.com/*', 'https://*.facebook.com/*', backendUrl],
        background: {
          service_worker: 'background/index.js',
          type: 'module',
        },
        content_scripts: [
          {
            matches: ['https://*.reddit.com/*', 'https://*.facebook.com/*'],
            js: ['content-script/index.js'],
          },
        ],
        side_panel: {
          default_path: SIDEPANEL_PATH,
        },
        icons: {
          '16': 'icons/icon16.png',
          '48': 'icons/icon48.png',
          '128': 'icons/icon128.png',
        },
        action: {
          default_title: 'Open Side Panel',
          default_icon: {
            '16': 'icons/icon16.png',
            '48': 'icons/icon48.png',
            '128': 'icons/icon128.png',
          },
        },
        web_accessible_resources: [
          {
            resources: ['icons/*.png'],
            matches: ['https://*.reddit.com/*', 'https://*.facebook.com/*'],
          },
        ],
        content_security_policy: {
          extension_pages: "script-src 'self'; object-src 'self';",
        },
      };
      this.emitFile({
        type: 'asset',
        fileName: 'manifest.json',
        source: JSON.stringify(manifest, null, 2),
      });
    },
  };
}

export default defineConfig({
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        background: resolve(import.meta.dirname, 'src/entrypoints/background.ts'),
        'content-script': resolve(import.meta.dirname, 'src/entrypoints/content.ts'),
        sidepanel: resolve(import.meta.dirname, SIDEPANEL_PATH),
      },
      output: {
        entryFileNames: (chunkInfo) => {
          if (chunkInfo.name === 'background' || chunkInfo.name === 'content-script') {
            return '[name]/index.js';
          }
          return 'assets/[name]-[hash].js';
        },
      },
    },
  },
  plugins: [manifestPlugin()],
});
