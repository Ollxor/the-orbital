// @ts-check
import { defineConfig } from 'astro/config';

export default defineConfig({
  vite: {
    resolve: {
      alias: {
        '@styles': '/src/styles',
        '@data': '/src/data',
      }
    }
  }
});