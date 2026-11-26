import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { viteSingleFile } from "vite-plugin-singlefile";

// Build ra 1 file HTML duy nhất (JS + CSS nhúng sẵn) tại ../dashboard/index.html
export default defineConfig({
  plugins: [react(), tailwindcss(), viteSingleFile()],
  base: "./",
  publicDir: false,
  build: { outDir: "../dashboard", emptyOutDir: false },
  server: { fs: { allow: [".."] } },
});
