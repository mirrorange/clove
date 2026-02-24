---
title: "Frontend i18n with react-i18next (English default)"
description: "Add internationalization to Clove frontend, replacing ~122 hardcoded Chinese strings with t() calls, defaulting to English"
status: complete
priority: P1
effort: 3h
branch: feat/frontend-english-localization
tags: [i18n, frontend, react-i18next, localization]
created: 2026-02-24
---

# Frontend i18n - English Localization Plan

## Objective
Replace all hardcoded Chinese strings across 8 frontend files with `react-i18next` translation calls. Default language: English. Minimize upstream merge conflicts by creating NEW files for i18n infrastructure and only replacing string literals in existing files.

## Conflict Mitigation Strategy
- All i18n infrastructure = NEW files (zero conflicts)
- Existing files: only change Chinese string literals to `t('key')` calls + add `useTranslation()` import/hook
- Preserve identical JSX structure, component logic, formatting
- `toLocaleString('zh-CN')` changes to locale-aware formatting via i18n

---

## Phase 1: i18n Infrastructure (NEW files only - zero conflicts)

### 1.1 Install dependencies
```bash
cd front && pnpm add react-i18next i18next i18next-browser-languagedetector
```

### 1.2 Create i18n config
**New file:** `src/i18n/i18n-config.ts`
```typescript
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import en from './locales/en.json'
import zh from './locales/zh.json'

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: { en: { translation: en }, zh: { translation: zh } },
    fallbackLng: 'en',
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: 'i18nLanguage',
      caches: ['localStorage'],
    },
  })

export default i18n
```

### 1.3 Create translation files
**Key naming convention:** flat dot-notation grouped by component/page.
- `login.title`, `login.subtitle`, `login.placeholder`, etc.
- `dashboard.title`, `dashboard.welcome`, etc.
- `accounts.title`, `accounts.delete`, etc.
- `settings.title`, `settings.apiKeys`, etc.
- `layout.nav.dashboard`, `layout.nav.accounts`, etc.
- `accountModal.title.add`, `accountModal.title.edit`, etc.
- `oauthModal.title`, `oauthModal.orgUuidLabel`, etc.
- `batchModal.title`, `batchModal.placeholder`, etc.
- `common.cancel`, `common.delete`, `common.save`, `common.edit`, etc.

**New file:** `src/i18n/locales/en.json` - English translations (primary)
**New file:** `src/i18n/locales/zh.json` - Chinese translations (match current hardcoded strings exactly)

### 1.4 Complete string inventory (~122 strings across 8 files)

| File | Count | Key prefix |
|------|-------|-----------|
| Login.tsx | 5 | `login.*` |
| Dashboard.tsx | 13 | `dashboard.*` |
| Accounts.tsx | 27 | `accounts.*` |
| Settings.tsx | 29 | `settings.*` |
| Layout.tsx | 4 | `layout.*` |
| AccountModal.tsx | 17 | `accountModal.*` |
| OAuthModal.tsx | 13 | `oauthModal.*` |
| BatchCookieModal.tsx | 14 | `batchModal.*` |
| **Shared** | ~8 | `common.*` |

---

## Phase 2: Integration (minimal changes to existing files)

### 2.1 Wire i18n into app entry
**Modify:** `src/main.tsx` - add single import line:
```typescript
import './i18n/i18n-config'  // add before App import
```

### 2.2 Replace strings in each file

For each of the 8 files, the changes are:
1. Add import: `import { useTranslation } from 'react-i18next'`
2. Add hook: `const { t } = useTranslation()`
3. Replace each Chinese string literal with `t('key')`
4. Replace `toLocaleString('zh-CN')` with `new Date(x).toLocaleString(i18n.language === 'zh' ? 'zh-CN' : 'en-US')`

**Detailed per-file changes:**

#### Login.tsx (5 strings)
- `'欢迎回来'` -> `t('login.welcomeBack')`
- `'输入您的 Admin Key 以访问管理面板'` -> `t('login.subtitle')`
- `'输入您的管理密钥'` (placeholder) -> `t('login.placeholder')`
- `'验证中...' / '登录'` -> `t('login.verifying') / t('login.signIn')`
- `'Admin Key 无效或服务器连接失败'` -> `t('login.invalidKey')`
- `'Clove - 全力以赴的 Claude 反向代理！'` -> `t('login.footer')`

#### Dashboard.tsx (13 strings)
- `'仪表板'` -> `t('dashboard.title')`
- `'欢迎使用 Clove!'` -> `t('dashboard.welcome')`
- `'账户总数' / '服务器状态' / '活跃会话' / '系统状态'` -> `t('dashboard.totalAccounts')` etc.
- `'在线' / '离线' / '正常' / '降级'` -> `t('dashboard.online')` etc.
- `'快速操作' / '管理账户' / '系统设置'` -> `t('dashboard.quickActions')` etc.
- `'添加、编辑或删除 Claude 账户'` -> `t('dashboard.manageAccountsDesc')`
- `'配置应用程序参数'` -> `t('dashboard.systemSettingsDesc')`
- `'前往管理' / '前往设置'` -> `t('dashboard.goToAccounts') / t('dashboard.goToSettings')`

#### Accounts.tsx (27 strings)
- Page header, button labels, table headers, status names, empty states, delete dialog, etc.
- Status mapping: `'正常'/'无效'/'限流中'` -> `t('accounts.status.valid')` etc.
- All `toLocaleString('zh-CN')` -> locale-aware

#### Settings.tsx (29 strings)
- Section titles, labels, descriptions, placeholders, status badges, delete dialogs, toast messages
- Toast messages: `'密钥已复制到剪贴板'` -> `t('settings.keyCopied')` etc.

#### Layout.tsx (4 strings)
- Nav items: `'仪表板' / '账户管理' / '应用设置'` -> `t('layout.nav.*')`
- `'退出登录'` -> `t('layout.logout')`

#### AccountModal.tsx (17 strings)
- Dialog titles, labels, placeholders, button text, alert messages, select options

#### OAuthModal.tsx (13 strings)
- Dialog titles, labels, placeholders, error messages, button states, info alerts

#### BatchCookieModal.tsx (14 strings)
- Dialog titles, placeholders, progress labels, result messages, button states

### 2.3 API client comments
**Modify:** `src/api/client.ts`
- Translate Chinese comments to English
- Change error fallback: `'发生未知错误'` -> `t('common.unknownError')` (or keep simple English string since this is in a non-component context; use `i18n.t()` import directly)

---

## Phase 3: Language Switcher

### 3.1 Add toggle to Layout.tsx header
Add a minimal EN/ZH toggle button in the header bar (next to SidebarTrigger):

```tsx
import { useTranslation } from 'react-i18next'
import { Languages } from 'lucide-react'

// In header:
<Button variant="ghost" size="sm" onClick={() => {
  const newLang = i18n.language === 'zh' ? 'en' : 'zh'
  i18n.changeLanguage(newLang)
}}>
  <Languages className="h-4 w-4 mr-1" />
  {i18n.language === 'zh' ? 'EN' : 'ZH'}
</Button>
```

Language persisted automatically via `i18next-browser-languagedetector` + localStorage key `i18nLanguage`.

---

## Files Created (NEW - zero conflict risk)
| File | Purpose |
|------|---------|
| `src/i18n/i18n-config.ts` | i18n initialization |
| `src/i18n/locales/en.json` | English translations |
| `src/i18n/locales/zh.json` | Chinese translations |

## Files Modified (minimal changes)
| File | Changes |
|------|---------|
| `src/main.tsx` | +1 import line |
| `src/pages/Login.tsx` | +import, +hook, 5 string replacements |
| `src/pages/Dashboard.tsx` | +import, +hook, 13 string replacements |
| `src/pages/Accounts.tsx` | +import, +hook, 27 string replacements |
| `src/pages/Settings.tsx` | +import, +hook, 29 string replacements |
| `src/components/Layout.tsx` | +import, +hook, 4 string replacements, +language toggle |
| `src/components/AccountModal.tsx` | +import, +hook, 17 string replacements |
| `src/components/OAuthModal.tsx` | +import, +hook, 13 string replacements |
| `src/components/BatchCookieModal.tsx` | +import, +hook, 14 string replacements |
| `src/api/client.ts` | Translate comments, 1 error string |

## Implementation Order
1. Phase 1 (infrastructure) - can be done without touching existing files
2. Phase 2 (string replacement) - do one file at a time, build-test after each
3. Phase 3 (language switcher) - final touch

## Success Criteria
- [x] `pnpm build` passes with zero errors
- [x] App defaults to English on fresh visit
- [x] All UI text displays in English
- [x] Toggle switches to Chinese, all text matches original
- [x] Language preference persists across page reloads
- [x] Date/time formatting adapts to selected language
- [x] No Chinese strings remain hardcoded in any TSX file

## Risk Assessment
- **Low risk:** All i18n infra is new files; string replacements are mechanical
- **Merge conflict mitigation:** Upstream changes to Chinese strings will conflict with our `t()` calls, but these are simple line-level conflicts resolvable by updating translation JSONs
- **Date formatting:** `toLocaleString` locale param change is safe; both `en-US` and `zh-CN` are universally supported
