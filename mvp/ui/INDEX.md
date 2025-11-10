# Eidolon Orchestrator UI - Complete File Index

## Quick Navigation

- **Getting Started**: [QUICKSTART.md](./QUICKSTART.md)
- **Installation**: [INSTALLATION.md](./INSTALLATION.md)
- **Main Documentation**: [README.md](./README.md)
- **Project Overview**: [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md)

## All Files (by Category)

### Documentation (10 files)
1. `README.md` - Main project documentation with features, tech stack, usage
2. `QUICKSTART.md` - 5-minute quick start guide
3. `INSTALLATION.md` - Detailed installation and troubleshooting
4. `TESTING.md` - Comprehensive testing checklist and procedures
5. `DEVELOPMENT.md` - Technical development notes and guidelines
6. `ARCHITECTURE.md` - System architecture and design patterns
7. `UX_DESIGN.md` - UX specifications and design philosophy
8. `PROJECT_SUMMARY.md` - Complete project overview and statistics
9. `COMPONENT_DIAGRAM.md` - Visual component architecture diagrams
10. `INDEX.md` - This file - complete file index

### Configuration (7 files)
1. `package.json` - NPM dependencies and scripts
2. `package-lock.json` - Dependency lock file
3. `vite.config.ts` - Vite build configuration
4. `tailwind.config.js` - TailwindCSS theme and custom colors
5. `postcss.config.js` - PostCSS plugin configuration
6. `tsconfig.json` - TypeScript compiler options
7. `tsconfig.node.json` - TypeScript config for Node.js files

### Application Root (3 files)
1. `index.html` - HTML entry point
2. `src/main.ts` - Application bootstrap
3. `src/style.css` - Global styles and Tailwind imports

### Core Application (1 file)
1. `src/App.vue` - Root Vue component with layout (header, sidebar, main, findings)

### Components (4 files)
1. `src/components/FileQueue.vue` - Left sidebar with file cards and filtering
2. `src/components/OrchestrationView.vue` - Main panel with agents and messages
3. `src/components/FindingsPanel.vue` - Bottom panel with grouped findings
4. `src/components/FileUploadModal.vue` - File upload modal with drag-drop

### State Management (1 file)
1. `src/stores/orchestration.ts` - Pinia store with WebSocket, state, actions

### Services (1 file)
1. `src/services/api.ts` - Axios HTTP client for backend API calls

### Types (1 file)
1. `src/types/index.ts` - TypeScript type definitions and interfaces

### Supporting Files (3 files)
1. `.gitignore` - Git ignore patterns
2. `.vscode/extensions.json` - Recommended VS Code extensions
3. `src/assets/` - Static assets directory (empty, ready for images/icons)

## File Sizes and Line Counts

### Large Files (200+ lines)
- `src/stores/orchestration.ts` - ~400 lines (State management)
- `src/components/FindingsPanel.vue` - ~350 lines (Findings display)
- `src/components/OrchestrationView.vue` - ~300 lines (Agent visualization)
- `src/components/FileUploadModal.vue` - ~250 lines (Upload interface)
- `src/components/FileQueue.vue` - ~200 lines (File sidebar)

### Medium Files (50-200 lines)
- `src/App.vue` - ~150 lines (Root component)
- `src/services/api.ts` - ~100 lines (API client)
- `src/types/index.ts` - ~80 lines (Type definitions)
- `src/style.css` - ~70 lines (Global styles)
- `tailwind.config.js` - ~50 lines (Tailwind config)

### Small Files (<50 lines)
- `src/main.ts` - ~10 lines (Bootstrap)
- `vite.config.ts` - ~20 lines (Vite config)
- `tsconfig.json` - ~30 lines (TypeScript config)
- `postcss.config.js` - ~5 lines (PostCSS config)
- `.gitignore` - ~25 lines (Git ignores)

### Documentation Files
- `DEVELOPMENT.md` - ~500 lines
- `TESTING.md` - ~400 lines
- `PROJECT_SUMMARY.md` - ~350 lines
- `COMPONENT_DIAGRAM.md` - ~300 lines
- `INSTALLATION.md` - ~250 lines
- `README.md` - ~200 lines
- `QUICKSTART.md` - ~100 lines
- `ARCHITECTURE.md` - ~230 lines (provided)
- `UX_DESIGN.md` - ~260 lines (provided)

## Total Statistics

**Source Files**: 17
**Documentation Files**: 10
**Total Files**: 27

**Source Code**: ~3,000 lines
**Documentation**: ~2,500 lines
**Total Lines**: ~5,500 lines

## File Dependencies

### Direct Dependencies (package.json)
```json
{
  "vue": "^3.4.21",
  "pinia": "^2.1.7",
  "vue-router": "^4.3.0",
  "@vueuse/core": "^10.9.0",
  "axios": "^1.6.8"
}
```

### Dev Dependencies
```json
{
  "@vitejs/plugin-vue": "^5.0.4",
  "vite": "^5.2.0",
  "vue-tsc": "^2.0.6",
  "typescript": "^5.4.2",
  "tailwindcss": "^3.4.1",
  "autoprefixer": "^10.4.19",
  "postcss": "^8.4.38"
}
```

## Import Graph

```
main.ts
  ├─ App.vue
  │   ├─ FileQueue.vue
  │   │   └─ orchestration.ts (store)
  │   ├─ OrchestrationView.vue
  │   │   └─ orchestration.ts (store)
  │   ├─ FindingsPanel.vue
  │   │   └─ orchestration.ts (store)
  │   └─ FileUploadModal.vue
  │       └─ api.ts (services)
  ├─ orchestration.ts (store)
  │   ├─ types/index.ts
  │   └─ api.ts (services)
  ├─ style.css
  └─ pinia

api.ts
  ├─ axios
  └─ types/index.ts

types/index.ts
  └─ (standalone)
```

## Component Usage

### App.vue uses:
- FileQueue.vue
- OrchestrationView.vue
- FindingsPanel.vue
- FileUploadModal.vue (conditional)
- useOrchestrationStore()

### FileQueue.vue uses:
- useOrchestrationStore()
- types (FileAnalysis, Finding, Severity)

### OrchestrationView.vue uses:
- useOrchestrationStore()
- types (Agent, Message, Severity)

### FindingsPanel.vue uses:
- useOrchestrationStore()
- types (Finding, Severity, FindingType)

### FileUploadModal.vue uses:
- api.ts (uploadFile, startAnalysis)
- types (basic types)

## Build Output

After `npm run build`, the `dist/` directory contains:

```
dist/
├── index.html              (Processed HTML)
├── assets/
│   ├── index-[hash].js     (Main bundle ~150KB)
│   ├── index-[hash].css    (Styles ~20KB)
│   └── vendor-[hash].js    (Dependencies ~500KB)
└── vite.svg               (Favicon)
```

## Key File Relationships

### State Flow
```
orchestration.ts (store)
  ↕ (reactive state)
Components (FileQueue, OrchestrationView, FindingsPanel)
```

### API Communication
```
Components
  → api.ts (HTTP calls)
  → Backend (FastAPI)

orchestration.ts
  → WebSocket
  → Backend (events)
```

### Type Safety
```
types/index.ts
  → orchestration.ts
  → api.ts
  → All components
```

## File Purposes

### Entry & Setup
- `index.html` - Browser entry point
- `main.ts` - JavaScript entry, creates Vue app
- `App.vue` - Root component, layout structure

### UI Components
- `FileQueue.vue` - Shows list of files being analyzed
- `OrchestrationView.vue` - Shows agents and message flow
- `FindingsPanel.vue` - Shows analysis findings by severity
- `FileUploadModal.vue` - Handles file upload workflow

### Business Logic
- `orchestration.ts` - All application state and WebSocket logic
- `api.ts` - HTTP API calls to backend
- `types/index.ts` - TypeScript interfaces for type safety

### Styling
- `style.css` - Global styles, Tailwind imports, custom classes
- `tailwind.config.js` - Custom theme, colors, animations

### Build & Config
- `vite.config.ts` - Dev server, build settings, proxying
- `tsconfig.json` - TypeScript strictness, paths, target
- `postcss.config.js` - CSS processing pipeline
- `package.json` - Dependencies, scripts

## Recommended Reading Order

### For New Developers
1. `INDEX.md` (this file) - Understand file structure
2. `README.md` - Learn project overview
3. `QUICKSTART.md` - Get running quickly
4. `COMPONENT_DIAGRAM.md` - Understand architecture
5. `DEVELOPMENT.md` - Learn development workflow

### For Designers/UX
1. `UX_DESIGN.md` - Design specifications
2. `README.md` - Technical context
3. `COMPONENT_DIAGRAM.md` - UI structure
4. `tailwind.config.js` - Color system

### For DevOps/Deployment
1. `INSTALLATION.md` - Setup requirements
2. `README.md` - Tech stack
3. `vite.config.ts` - Build configuration
4. `DEVELOPMENT.md` - Deployment section

### For Testers
1. `TESTING.md` - Testing procedures
2. `QUICKSTART.md` - How to run
3. `README.md` - Features to test
4. `DEVELOPMENT.md` - Debugging tips

### For Backend Developers
1. `ARCHITECTURE.md` - API requirements
2. `api.ts` - API endpoints used
3. `orchestration.ts` - WebSocket event handling
4. `types/index.ts` - Data contracts

## File Modification Frequency

### Frequently Modified
- Components (FileQueue, OrchestrationView, FindingsPanel, FileUploadModal)
- orchestration.ts (adding features)
- types/index.ts (new types)
- style.css (styling tweaks)

### Occasionally Modified
- App.vue (layout changes)
- api.ts (new endpoints)
- tailwind.config.js (theme updates)
- README.md (documentation updates)

### Rarely Modified
- vite.config.ts (build changes)
- tsconfig.json (compiler options)
- main.ts (bootstrap)
- package.json (dependency updates)

## Critical Files

**Must not break**:
1. `src/stores/orchestration.ts` - Core state management
2. `src/types/index.ts` - Type contracts
3. `src/App.vue` - Root component
4. `vite.config.ts` - Build system

**High impact if changed**:
1. `src/components/FileQueue.vue` - User's primary navigation
2. `src/components/FindingsPanel.vue` - Critical feature display
3. `src/services/api.ts` - Backend communication
4. `tailwind.config.js` - Visual consistency

## Next Steps

1. Read [QUICKSTART.md](./QUICKSTART.md) to get the app running
2. Read [DEVELOPMENT.md](./DEVELOPMENT.md) to understand the codebase
3. Read [COMPONENT_DIAGRAM.md](./COMPONENT_DIAGRAM.md) for architecture
4. Start modifying components to add new features

## Support

If you can't find what you're looking for:
1. Check the file's inline comments
2. Review related documentation files
3. Check the commit history for context
4. Consult the main README.md

---

**Total Project Size**: 27 files, 5,500+ lines
**Ready to run**: `npm install && npm run dev`
**All files located in**: `/home/john/eidolon/mvp/ui/`
