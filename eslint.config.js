import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tseslint from 'typescript-eslint';

const publicApiPattern = {
  group: ['@/entities/*/*', '@/features/*/*', '@/widgets/*/*'],
  message: 'Import domain slices through their public index.ts entry point.',
};

function architectureImports(...patterns) {
  return ['error', { patterns: [publicApiPattern, ...patterns] }];
}

export default tseslint.config(
  {
    ignores: ['coverage', 'dist', 'node_modules'],
  },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommendedTypeChecked],
    files: ['src/**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      globals: globals.browser,
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.flat.recommended.rules,
      // Existing forms intentionally synchronize server data into editable local drafts.
      'react-hooks/set-state-in-effect': 'off',
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      'no-restricted-imports': architectureImports(),
    },
  },
  {
    files: ['src/shared/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-imports': architectureImports({
        group: ['@/app/**', '@/pages/**', '@/widgets/**', '@/features/**', '@/entities/**'],
        message: 'The shared layer cannot depend on product or application layers.',
      }),
    },
  },
  {
    files: ['src/entities/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-imports': architectureImports({
        group: ['@/app/**', '@/pages/**', '@/widgets/**', '@/features/**', '@/entities/**'],
        message: 'Entities may only depend on their own relative modules and the shared layer.',
      }),
    },
  },
  {
    files: ['src/features/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-imports': architectureImports({
        group: ['@/app/**', '@/pages/**', '@/widgets/**', '@/features/**'],
        message: 'Features may only depend on their own relative modules, entities, and shared modules.',
      }),
    },
  },
  {
    files: ['src/widgets/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-imports': architectureImports({
        group: ['@/app/**', '@/pages/**', '@/widgets/**'],
        message: 'Widgets may only depend on their own relative modules and lower layers.',
      }),
    },
  },
  {
    files: ['src/pages/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-imports': architectureImports({
        group: ['@/app/**', '@/pages/**'],
        message: 'Pages may only depend on their own relative modules and lower layers.',
      }),
    },
  },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommendedTypeChecked],
    files: ['*.ts'],
    languageOptions: {
      ecmaVersion: 'latest',
      globals: globals.node,
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  {
    extends: [js.configs.recommended],
    files: ['*.js'],
    languageOptions: {
      ecmaVersion: 'latest',
      globals: globals.node,
    },
  },
);
