import tailwindcss from "@tailwindcss/vite"
import vue from "@vitejs/plugin-vue"
import { defineConfig } from "vite"

// https://vite.dev/config
export default defineConfig({
  resolve: { alias: { "@": "/src", "#": "/assets" } },
  plugins: [vue(), tailwindcss()],
  build: {
    outDir: "../dist",
    emptyOutDir: true,
    minify: false,
    manifest: false,
    sourcemap: false,
    rolldownOptions: {
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "[name].js",
        assetFileNames: "[name].[ext]",
      },
    },
  },
})
