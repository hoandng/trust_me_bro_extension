import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { build } from 'vite';

const root = fileURLToPath(new URL('..', import.meta.url));
const outDir = resolve(root, '.cache/tests');

// Dùng Vite sẵn có để chạy module TypeScript bằng Node, không cần thêm test framework.
await build({
  configFile: false,
  root,
  envDir: false,
  define: {
    'import.meta.env.VITE_BACKEND_URL': JSON.stringify('http://127.0.0.1:8000'),
    'import.meta.env.VITE_EXTENSION_API_KEY': JSON.stringify('test-key'),
  },
  build: {
    outDir,
    emptyOutDir: true,
    target: 'node22',
    minify: false,
    lib: {
      entry: resolve(root, 'tests/analysis.test.ts'),
      formats: ['es'],
      fileName: () => 'analysis.test.mjs',
    },
    rollupOptions: { external: [/^node:/] },
  },
});

const result = spawnSync(process.execPath, ['--test', resolve(outDir, 'analysis.test.mjs')], {
  stdio: 'inherit',
});
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
