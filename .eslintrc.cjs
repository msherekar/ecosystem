/**
 * ESLint configuration.
 *
 * `eslint` was declared in devDependencies and `npm run lint` was wired up,
 * but there was no config file anywhere in the repo, so the script failed
 * immediately. The TypeScript parser and plugin were also missing, so it
 * could not have linted the .ts/.tsx files the script targets.
 */
module.exports = {
  root: true,
  env: { browser: true, es2022: true, node: true },
  extends: ['eslint:recommended'],
  parserOptions: { ecmaVersion: 2022, sourceType: 'module' },
  ignorePatterns: [
    'dist/',
    'release/',
    'build/',
    'node_modules/',
    'src/cloud/',
    '**/*.py',
  ],
  rules: {
    // Unused variables are usually a sign of a half-finished refactor; the
    // repo had several (axios, monaco-editor, messageQueue).
    'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
    'no-console': 'off', // the main process logs to stdout by design
    eqeqeq: ['error', 'smart'],
    'no-var': 'error',
    'prefer-const': 'warn',
  },
  overrides: [
    {
      files: ['**/*.ts', '**/*.tsx'],
      parser: '@typescript-eslint/parser',
      parserOptions: { ecmaFeatures: { jsx: true } },
      plugins: ['@typescript-eslint', 'react-hooks'],
      extends: ['plugin:@typescript-eslint/recommended'],
      rules: {
        // Caught the real TS18046 bug in mcpService.ts.
        '@typescript-eslint/no-explicit-any': 'warn',
        '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
        'react-hooks/rules-of-hooks': 'error',
        // Missing effect dependencies caused the stale-status bugs in App.tsx.
        'react-hooks/exhaustive-deps': 'warn',
      },
    },
    {
      files: ['electron/**/*.js', 'main.js', '*.cjs', '*.config.js'],
      env: { node: true, browser: false },
    },
    {
      files: ['electron/visualization.js'],
      env: { browser: true, node: false },
      globals: { Plotly: 'readonly' },
    },
  ],
};
