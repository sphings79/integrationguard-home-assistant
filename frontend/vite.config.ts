import { defineConfig } from "vite";

// Two entry points plus one chunk per language. Everything is committed to
// the repository because HACS does not run a build step.
export default defineConfig({
  build: {
    outDir: "../custom_components/integrationguard/frontend",
    // Deliberately false: emptying it would delete and recreate the folder,
    // which breaks a bind mount pointing at it during development. The
    // prebuild script removes the files instead and leaves the folder alone.
    emptyOutDir: false,
    target: "es2021",
    minify: "esbuild",
    sourcemap: false,
    rollupOptions: {
      input: {
        "integrationguard-panel": "src/integrationguard-panel.ts",
        "integrationguard-card": "src/card/integrationguard-card.ts",
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: (chunk) => {
          // Language chunks get a readable name, so it is obvious in the
          // network tab which catalogue a browser actually fetched.
          const locale = chunk.facadeModuleId?.match(
            /[\\/]locales[\\/]([a-z]{2})\.ts$/,
          )?.[1];
          return locale
            ? `integrationguard-lang-${locale}.js`
            : "integrationguard-shared.js";
        },
        format: "es",
      },
    },
  },
});
