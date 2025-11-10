# Testing Guide

Comprehensive testing instructions for the Eidolon Orchestrator UI.

## Manual Testing Checklist

### 1. Initial Load
- [ ] Page loads without errors
- [ ] Header displays "Eidolon Orchestrator"
- [ ] Connection status shows "Disconnected" initially
- [ ] File queue shows empty state
- [ ] Main panel shows "No file selected" message
- [ ] Findings panel is collapsible

### 2. WebSocket Connection
- [ ] Connection status changes to "Connected" (green dot)
- [ ] If backend is down, shows "Disconnected" (red dot)
- [ ] Error toast appears if connection fails
- [ ] Automatic reconnection attempts on disconnect

### 3. File Upload
- [ ] Click "Upload File" button opens modal
- [ ] Modal has drag-and-drop zone
- [ ] Can browse files via button
- [ ] Only accepts .py files
- [ ] Shows error for non-Python files
- [ ] Selected file displays with name and size
- [ ] Can remove selected file
- [ ] Configuration sliders work (complexity threshold, agent count)
- [ ] Upload progress bar appears
- [ ] Modal closes after successful upload
- [ ] File appears in queue sidebar

### 4. File Queue Sidebar
- [ ] File cards display with status dot
- [ ] Status colors: gray (queued), blue (analyzing), green (complete), red (failed)
- [ ] Progress bar shows during analysis
- [ ] Findings count badge appears when findings exist
- [ ] Badge color matches worst severity
- [ ] Severity dots show counts (critical, high, medium, low)
- [ ] Timestamp shows relative time
- [ ] Click selects file (blue ring appears)
- [ ] Keyboard navigation works (Tab, Enter, Space)
- [ ] Filter tabs work (All, Active, Complete, Failed)
- [ ] Empty state shows when no files

### 5. Orchestration View
- [ ] Loads when file is selected
- [ ] Header shows filename and status
- [ ] Agent count updates
- [ ] Message count updates
- [ ] Agent cards appear as agents spawn
- [ ] Agent cards show role, ID, status, message count
- [ ] Status badges colored correctly
- [ ] Message feed updates in real-time
- [ ] Messages show from/to agents with arrow
- [ ] Timestamps formatted correctly
- [ ] "Show more" appears for truncated messages
- [ ] Empty states show when no data

### 6. Module Override Alert
- [ ] Alert appears when module overrides function assessment
- [ ] Shows module assessment severity
- [ ] Lists overridden function count
- [ ] Displays override reason
- [ ] Styled with left border and warning colors

### 7. Findings Panel
- [ ] Header always visible with summary counts
- [ ] Click header toggles expansion
- [ ] Keyboard navigation works (Enter, Space)
- [ ] Severity groups (Critical, High, Medium, Low)
- [ ] Each group collapsible
- [ ] Groups default expanded for Critical and High
- [ ] Finding cards show:
  - Type badge (bug, security, performance, etc.)
  - Description
  - File path
  - Line number
  - Agent ID
- [ ] Click finding expands details
- [ ] Expanded view shows:
  - Suggested fix (if available)
  - Complexity bar (if applicable)
  - Action buttons
- [ ] Severity colors correct throughout
- [ ] Empty state when no findings

### 8. Accessibility
- [ ] All interactive elements keyboard navigable
- [ ] Focus indicators visible
- [ ] Screen reader labels present (check with browser tools)
- [ ] Color contrast sufficient (check with axe DevTools)
- [ ] ARIA attributes correct
- [ ] Live regions announce updates
- [ ] Modals trap focus

### 9. Real-time Updates
- [ ] New agents appear immediately
- [ ] Messages stream without lag
- [ ] Findings appear as detected
- [ ] File status updates in real-time
- [ ] Progress bars update smoothly
- [ ] No duplicate events

### 10. Error Handling
- [ ] WebSocket errors show toast
- [ ] API errors display appropriately
- [ ] Failed uploads show error message
- [ ] Failed analysis marks file as failed
- [ ] Network errors don't crash app

### 11. Performance
- [ ] No lag with multiple files
- [ ] Smooth scrolling in all panels
- [ ] Animations perform well
- [ ] No memory leaks (check DevTools)
- [ ] WebSocket messages process quickly

### 12. Responsive Design
- [ ] Works on desktop (1920x1080)
- [ ] Works on laptop (1366x768)
- [ ] Works on tablet (768x1024)
- [ ] Works on mobile (375x667)
- [ ] Sidebar collapsible on mobile
- [ ] Text doesn't overflow
- [ ] Buttons remain clickable

## Browser Testing

Test in these browsers:
- [ ] Chrome/Edge (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest, macOS only)

## Automated Testing

### Type Checking
```bash
npm run type-check
```
Should show no errors.

### Build Test
```bash
npm run build
```
Should complete without errors.

### Preview Production Build
```bash
npm run preview
```
Should serve production build successfully.

## Testing with Backend

### Prerequisites
1. Backend running on `localhost:8000`
2. Backend has `/api/upload` and `/api/analyze` endpoints
3. WebSocket endpoint `/ws/events` is accessible

### Test Flow
1. Start backend: `uvicorn server:app --reload`
2. Start frontend: `npm run dev`
3. Upload a Python file with complex functions
4. Watch real-time updates
5. Verify findings appear
6. Check all features work end-to-end

## Common Issues

### WebSocket won't connect
- Check backend is running
- Verify port 8000 is correct
- Check browser console for CORS errors
- Try clearing browser cache

### TypeScript errors
- Run `npm install` again
- Delete `node_modules` and reinstall
- Check `tsconfig.json` is correct

### Styles not loading
- Check Tailwind config
- Verify PostCSS is processing
- Clear Vite cache: `rm -rf node_modules/.vite`

### Hot reload not working
- Check Vite config
- Restart dev server
- Check file watchers (increase limit on Linux)

## Performance Testing

### Memory Leaks
1. Open Chrome DevTools > Memory
2. Take heap snapshot
3. Perform actions (upload, analyze, etc.)
4. Take another snapshot
5. Compare - should not grow significantly

### Network Traffic
1. Open DevTools > Network
2. Monitor WebSocket messages
3. Should not see duplicate or excessive messages
4. Should reconnect gracefully on disconnect

### Rendering Performance
1. Open DevTools > Performance
2. Record session
3. Should maintain 60fps during animations
4. No long tasks blocking UI

## Accessibility Testing

### Automated
```bash
# Install axe-core
npm install -D @axe-core/cli

# Run accessibility checks
axe http://localhost:3000
```

### Manual
1. Use keyboard only (no mouse)
2. Navigate through entire app
3. Verify all features accessible
4. Use screen reader (NVDA, JAWS, VoiceOver)
5. Test with high contrast mode
6. Test with zoom (200%, 400%)

## Security Testing

- [ ] No sensitive data in localStorage
- [ ] No XSS vulnerabilities (check user input handling)
- [ ] HTTPS used in production
- [ ] WebSocket connection secure (wss://)
- [ ] File upload validates type
- [ ] File size limits enforced

## Test Data

Sample Python files to test:
1. Simple file (1-2 functions)
2. Complex file (10+ functions)
3. File with high complexity functions
4. File with security issues
5. File with performance problems

## Reporting Issues

When reporting bugs, include:
1. Browser and version
2. Steps to reproduce
3. Expected vs actual behavior
4. Console errors (if any)
5. Screenshots
6. Backend logs (if applicable)
