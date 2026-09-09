// ESLint config for the dashboard — React + hooks rules, JSX enabled.
// react-in-jsx-scope is off since React 17+'s new JSX transform
// (used here via @vitejs/plugin-react) doesn't require React in scope.
module.exports = {
  root: true,
  env: { browser: true, es2021: true },
  extends: ['eslint:recommended', 'plugin:react/recommended', 'plugin:react-hooks/recommended'],
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module', ecmaFeatures: { jsx: true } },
  settings: { react: { version: 'detect' } },
  rules: {
    'react/prop-types': 'off',
    'react/react-in-jsx-scope': 'off',
  },
}
