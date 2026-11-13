// Static build of the use-case explorer. Output lands in dist/ and is merged
// into the docs site artifact. Links use import.meta.env.BASE_URL, never a
// hard-coded base. Telemetry is off through ASTRO_TELEMETRY_DISABLED=1 in the
// Makefile and both workflows.
import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://ravisharma5.github.io',
  base: '/otel-telco-blueprints',
  trailingSlash: 'always',
  outDir: './dist',
  build: {
    format: 'directory',
  },
  vite: {
    server: {
      // The layout imports ../site-src/brand/tokens.css from outside explorer/.
      fs: { allow: ['..'] },
    },
  },
});
