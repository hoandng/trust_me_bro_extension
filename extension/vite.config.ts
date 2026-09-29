import { defineConfig, Plugin } from 'vite';
import { resolve } from 'path';

const backendUrl = process.env.VITE_BACKEND_URL || 'http://localhost:3000/*';

function manifestPlugin(): Plugin {
  return {
    name: 'manifest-plugin',
    generateBundle() {
      const manifest = {
        manifest_version: 3,
        name: 'Fact Check Extension',
        version: '1.0.0',
        permissions: ['sidePanel', 'storage'],
        host_permissions: ['https://*.facebook.com/*', backendUrl],
        background: {
          service_worker: 'background/index.js',
          type: 'module'
        },
        content_scripts: [
          {
            matches: ['https://*.facebook.com/*'],
            js: ['content-script/index.js']
          }
        ],
        side_panel: {
          default_path: 'src/sidepanel/index.html'
        },
        icons: {
          '16': 'icons/icon16.png',
          '48': 'icons/icon48.png',
          '128': 'icons/icon128.png'
        },
        action: {
          default_title: 'Open Side Panel',
          default_icon: {
            '16': 'icons/icon16.png',
            '48': 'icons/icon48.png',
            '128': 'icons/icon128.png'
          }
        },
        web_accessible_resources: [
          {
            resources: ['icons/*.png'],
            matches: ['<all_urls>']
          }
        ]
      };
      this.emitFile({
        type: 'asset',
        fileName: 'manifest.json',
        source: JSON.stringify(manifest, null, 2)
      });
    }
  };
}

export default defineConfig({
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        background: resolve(import.meta.dirname, 'src/background/index.ts'),
        'content-script': resolve(import.meta.dirname, 'src/content-script/index.ts'),
        sidepanel: resolve(import.meta.dirname, 'src/sidepanel/index.html'),
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
