import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    chunkSizeWarningLimit: 2500,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('react') || id.includes('react-dom') || id.includes('react-router-dom')) {
              return 'vendor-react';
            }
            if (id.includes('motion') || id.includes('framer-motion')) {
              return 'vendor-motion';
            }
            if (id.includes('@tabler/icons-react') || id.includes('lucide-react')) {
              return 'vendor-icons';
            }
            if (id.includes('react-syntax-highlighter') || id.includes('react-markdown')) {
              return 'vendor-markdown';
            }
            if (id.includes('pdfjs-dist') || id.includes('@react-pdf-viewer')) {
              return 'vendor-pdfjs';
            }
            return 'vendor';
          }
        },
      },
      onwarn(warning, warn) {
        if (warning.code === 'EVAL' && warning.id?.includes('pdfjs-dist')) {
          return;
        }
        warn(warning);
      },
    },
    rolldownOptions: {
      onwarn(warning: any, warn: any) {
        if (warning.code === 'EVAL' && warning.id?.includes('pdfjs-dist')) {
          return;
        }
        warn(warning);
      },
    }
  },
})
