import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import jarvisPlugin from "eslint-plugin-jarvis";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  // Jarvis coding rules — set to "warn" so existing code doesn't block builds.
  // Fix violations incrementally; bump to "error" once baseline is clean.
  {
    plugins: {
      jarvis: jarvisPlugin,
    },
    rules: {
      "jarvis/assertion-density": "warn",
      "jarvis/bounded-loops": "warn",
      "jarvis/no-recursion": "warn",
      "jarvis/function-length": "warn",
    },
  },
]);

export default eslintConfig;
