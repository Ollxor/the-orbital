// @ts-check
import { defineConfig } from 'astro/config';

import cloudflare from '@astrojs/cloudflare';

export default defineConfig({
  vite: {
    resolve: {
      alias: {
        '@styles': '/src/styles',
        '@data': '/src/data',
      }
    }
  },

  adapter: cloudflare()
});