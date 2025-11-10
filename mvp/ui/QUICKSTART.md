# Quick Start Guide

Get the Eidolon Orchestrator UI running in 5 minutes!

## Prerequisites

- Node.js 18+ installed
- Backend FastAPI server running on `http://localhost:8000`

## Installation & Running

```bash
# Navigate to the UI directory
cd /home/john/eidolon/mvp/ui

# Install dependencies
npm install

# Start the development server
npm run dev
```

The UI will open automatically at `http://localhost:3000`

## Testing the UI

1. **Upload a Python file**
   - Click the "Upload File" button in the header
   - Select a Python (.py) file
   - Configure complexity threshold and agent count
   - Click "Start Analysis"

2. **Monitor progress**
   - Watch the file card in the left sidebar show progress
   - Status dot changes color based on analysis state
   - Findings count updates in real-time

3. **View orchestration**
   - Click on a file card to select it
   - See agent flow and messages in the main panel
   - Agents appear as they spawn
   - Messages stream in real-time

4. **Review findings**
   - Expand the bottom panel (Findings)
   - Findings are grouped by severity
   - Click to expand individual findings for details
   - View suggested fixes and complexity metrics

## Keyboard Shortcuts

- `Tab` - Navigate between interactive elements
- `Enter` / `Space` - Activate buttons and select items
- `Esc` - Close modals
- Arrow keys - Navigate within lists

## Troubleshooting

### WebSocket Connection Failed
- Ensure backend is running on `localhost:8000`
- Check browser console for connection errors
- Verify CORS is enabled in backend

### No Files Appearing
- Check that WebSocket is connected (green dot in header)
- Verify file upload succeeded (check network tab)
- Ensure backend API is responding

### TypeScript Errors
```bash
# Run type checking
npm run type-check

# If errors persist, clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

## Development Tips

- Hot Module Replacement (HMR) is enabled - changes reflect instantly
- Use Vue DevTools browser extension for debugging
- Check browser console for WebSocket event logs
- Monitor network tab for API calls

## Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

Built files will be in the `dist/` directory.

## Environment Variables

Create a `.env` file for custom configuration:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## Next Steps

- Review `/home/john/eidolon/mvp/ui/README.md` for detailed documentation
- Check `/home/john/eidolon/mvp/ui/UX_DESIGN.md` for design specifications
- Read `/home/john/eidolon/mvp/ui/ARCHITECTURE.md` for system architecture

## Support

If you encounter issues:
1. Check the browser console for errors
2. Verify backend is running and accessible
3. Ensure all dependencies are installed
4. Review the README.md for detailed troubleshooting

Happy orchestrating!
