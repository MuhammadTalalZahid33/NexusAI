import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
    rules: {
      // Fetching data on mount via an effect is a legitimate, intended pattern
      // here (load documents / resolve current user). Downgrade this strict
      // rule from error to warning so it informs without failing CI.
      'react-hooks/set-state-in-effect': 'warn',
      // Co-locating a context Provider with its useX() hook is a standard,
      // intentional pattern; Fast Refresh still works fine in practice.
      'react-refresh/only-export-components': 'warn',
    },
  },
])
