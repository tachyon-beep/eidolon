# Installation Guide

Complete installation and setup instructions for the Eidolon Orchestrator UI.

## System Requirements

### Required
- **Node.js**: 18.x or higher
- **npm**: 9.x or higher (comes with Node.js)
- **Operating System**: Linux, macOS, or Windows
- **Browser**: Chrome 90+, Firefox 88+, Safari 14+, or Edge 90+

### Recommended
- 4GB RAM minimum
- 1GB free disk space
- Fast internet connection (for initial npm install)

## Installation Steps

### 1. Verify Prerequisites

```bash
# Check Node.js version (should be 18+)
node --version

# Check npm version (should be 9+)
npm --version
```

If Node.js is not installed:
- **Linux**: `curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - && sudo apt-get install -y nodejs`
- **macOS**: `brew install node`
- **Windows**: Download from [nodejs.org](https://nodejs.org)

### 2. Navigate to UI Directory

```bash
cd /home/john/eidolon/mvp/ui
```

### 3. Install Dependencies

```bash
npm install
```

This will install:
- Vue 3 (frontend framework)
- Pinia (state management)
- Vite (build tool)
- TailwindCSS (styling)
- TypeScript (type checking)
- Axios (HTTP client)
- VueUse (composables)

Installation typically takes 2-5 minutes depending on internet speed.

### 4. Verify Installation

```bash
# Check for errors in package installation
npm list --depth=0

# Verify TypeScript configuration
npm run type-check
```

Both commands should complete without errors.

### 5. Start Development Server

```bash
npm run dev
```

You should see:
```
VITE v5.2.0  ready in 500 ms

➜  Local:   http://localhost:3000/
➜  Network: use --host to expose
➜  press h + enter to show help
```

### 6. Open in Browser

Navigate to `http://localhost:3000`

You should see:
- Header with "Eidolon Orchestrator"
- File queue sidebar (empty)
- Main orchestration panel (empty state)
- Findings panel (collapsed)

## Configuration

### Environment Variables

Create a `.env` file in `/home/john/eidolon/mvp/ui/`:

```env
# Backend API URL (default: localhost:8000)
VITE_API_BASE_URL=http://localhost:8000

# WebSocket URL (default: localhost:8000)
VITE_WS_URL=ws://localhost:8000

# Development mode
VITE_DEV_MODE=true
```

### Backend Setup

The UI requires a running FastAPI backend. Ensure:

1. Backend is running on `localhost:8000`
2. CORS is enabled for `localhost:3000`
3. WebSocket endpoint `/ws/events` is accessible
4. API endpoints are available

Start backend:
```bash
cd /home/john/eidolon/mvp
python -m uvicorn src.eidolon_mvp.api.server:app --reload
```

### Vite Configuration

Edit `vite.config.ts` if you need to change:
- Dev server port (default: 3000)
- Backend proxy settings
- Build output directory

## Troubleshooting

### Installation Issues

#### Error: "Cannot find module"
```bash
# Clear npm cache and reinstall
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

#### Error: "EACCES: permission denied"
```bash
# Fix npm permissions (Linux/macOS)
sudo chown -R $(whoami) ~/.npm
sudo chown -R $(whoami) /home/john/eidolon/mvp/ui/node_modules
```

#### Error: "Unsupported engine"
Check Node.js version:
```bash
node --version
# Should be 18.x or higher
```

### Runtime Issues

#### Port 3000 already in use
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Or use different port
npm run dev -- --port 3001
```

#### WebSocket connection fails
1. Check backend is running: `curl http://localhost:8000/api/status`
2. Check CORS settings in backend
3. Check browser console for errors
4. Try different browser

#### TypeScript errors
```bash
# Rebuild TypeScript declarations
npm run type-check

# If errors persist, check tsconfig.json
```

#### Styles not loading
```bash
# Clear Vite cache
rm -rf node_modules/.vite

# Restart dev server
npm run dev
```

### Build Issues

#### Build fails with TypeScript errors
```bash
# Fix type errors first
npm run type-check

# Then build
npm run build
```

#### Out of memory during build
```bash
# Increase Node memory limit
NODE_OPTIONS="--max-old-space-size=4096" npm run build
```

## Verification Checklist

After installation, verify:

- [ ] npm install completed without errors
- [ ] Dev server starts (`npm run dev`)
- [ ] Page loads at `localhost:3000`
- [ ] No console errors
- [ ] Type checking passes (`npm run type-check`)
- [ ] Build succeeds (`npm run build`)
- [ ] Backend connection works (green dot in header)

## Next Steps

1. **Quick Start**: Follow [QUICKSTART.md](./QUICKSTART.md)
2. **Testing**: Review [TESTING.md](./TESTING.md)
3. **Development**: Read [DEVELOPMENT.md](./DEVELOPMENT.md)
4. **Architecture**: Study [ARCHITECTURE.md](./ARCHITECTURE.md)
5. **UX Design**: Explore [UX_DESIGN.md](./UX_DESIGN.md)

## Uninstallation

To remove the UI:

```bash
# Remove node_modules
rm -rf /home/john/eidolon/mvp/ui/node_modules

# Remove build artifacts
rm -rf /home/john/eidolon/mvp/ui/dist

# Remove lock file
rm /home/john/eidolon/mvp/ui/package-lock.json

# Optionally remove entire directory
rm -rf /home/john/eidolon/mvp/ui
```

## Getting Help

If you encounter issues:

1. Check this guide's troubleshooting section
2. Review [TESTING.md](./TESTING.md) for common problems
3. Check browser console for errors
4. Verify backend is running
5. Try a different browser
6. Clear browser cache and reload

## Additional Resources

- [Vue 3 Installation Guide](https://vuejs.org/guide/quick-start.html)
- [Vite Troubleshooting](https://vitejs.dev/guide/troubleshooting.html)
- [npm Documentation](https://docs.npmjs.com/)
- [Node.js Troubleshooting](https://nodejs.org/en/docs/guides/debugging-getting-started/)
