import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const toolRequire = createRequire("/opt/static-analysis/package.json");

function loadPackage(name) {
  try {
    return require(name);
  } catch {
    return toolRequire(name);
  }
}

const js = loadPackage("@eslint/js");
const globals = loadPackage("globals");
const reactHooks = loadPackage("eslint-plugin-react-hooks");
const reactRefresh = loadPackage("eslint-plugin-react-refresh");
const tseslint = loadPackage("typescript-eslint");

export default [
  {
    ignores: ["dist/**", "node_modules/**"],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
      sourceType: "module",
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
    },
  },
];
