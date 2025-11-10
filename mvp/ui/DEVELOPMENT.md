# Development Notes

Technical details and development guidelines for the Eidolon Orchestrator UI.

## Architecture Overview

### Component Hierarchy
```
App.vue
├── FileQueue.vue              # Left sidebar
├── OrchestrationView.vue      # Main panel
│   ├── Agent cards
│   └── Message feed
├── FindingsPanel.vue          # Bottom panel
│   └── Finding cards
└── FileUploadModal.vue        # Modal overlay
```

### State Management (Pinia)

**Store**: `orchestration.ts`

State structure:
```typescript
{
  files: FileAnalysis[]           // All uploaded files
  agents: Agent[]                 // Active agents
  messages: Message[]             // Message history
  findings: Finding[]             // All findings
  sessions: Map<string, Session>  // Analysis sessions
  currentSessionId: string | null // Selected file
  orchestratorStatus: Status      // Backend status
  wsConnected: boolean            // WebSocket state
  wsError: string | null          // Connection errors
}
```

Computed properties:
- `currentSession` - Currently selected session
- `findingsBySeverity` - Findings grouped by severity
- `activeFiles` - Files being analyzed
- `completedFiles` - Completed analyses
- `failedFiles` - Failed analyses

Actions:
- `connectWebSocket()` - Establish WS connection
- `disconnectWebSocket()` - Close WS connection
- `selectFile(id)` - Select file for viewing
- `addFile(file)` - Add file to queue
- `updateFileProgress(id, progress)` - Update progress
- `clearAll()` - Reset all state

### WebSocket Event Flow

1. **Connection**: `ws://localhost:8000/ws/events`
2. **Events**: JSON messages
3. **Handling**: Store dispatches to appropriate handlers
4. **UI Updates**: Reactive state triggers component re-renders

Event handlers:
- `handleAgentSpawned()` - Add agent to list
- `handleMessageSent()` - Add message to feed
- `handleFindingDetected()` - Add finding to panel
- `handleAnalysisComplete()` - Mark file complete
- `handleAnalysisStarted()` - Add file to queue
- `handleAnalysisProgress()` - Update progress
- `handleAnalysisFailed()` - Mark file failed

### API Communication

**Service**: `api.ts`

Axios instance with:
- Base URL: `/api`
- Timeout: 30s
- JSON content type
- Error interceptor

Methods:
- `getStatus()` - Get orchestrator status
- `startAnalysis()` - Start file analysis
- `getSession()` - Get session details
- `getAgents()` - List agents
- `getMessages()` - Get messages
- `getFindings()` - Get findings
- `uploadFile()` - Upload file

## Styling System

### TailwindCSS Configuration

Custom colors defined in `tailwind.config.js`:
```javascript
colors: {
  'severity-critical': '#DC2626',
  'severity-high': '#F59E0B',
  'severity-medium': '#10B981',
  'severity-low': '#3B82F6',
  'status-queued': '#6B7280',
  'status-analyzing': '#6366F1',
  // ... more colors
}
```

### CSS Classes

Utility classes in `style.css`:
- `.severity-dot` - Colored status indicators
- `.status-dot` - File status indicators
- `.card` - Card component base
- `.card-hover` - Interactive card
- `.btn`, `.btn-primary`, `.btn-secondary` - Buttons
- `.badge`, `.badge-critical`, etc. - Severity badges

### Animations

Custom animations:
- `pulse-slow` - Slow pulse for active agents
- `slide-in` - Slide in from left
- `fade-in` - Fade in

CSS animations:
- `message-flow-animation` - Arrow flow for messages
- Progress bars with `transition-all`
- Expand/collapse with height transitions

## TypeScript Types

### Core Types (`types/index.ts`)

```typescript
type Severity = 'critical' | 'high' | 'medium' | 'low'
type FileStatus = 'queued' | 'analyzing' | 'complete' | 'failed'
type AgentStatus = 'spawning' | 'active' | 'completed' | 'failed'
type FindingType = 'bug' | 'security' | 'performance' | 'style' | 'complexity'

interface FileAnalysis {
  id: string
  filename: string
  filepath: string
  status: FileStatus
  progress: number
  findings: Finding[]
  // ... more fields
}

interface Finding {
  id: string
  severity: Severity
  type: FindingType
  description: string
  filePath: string
  lineNumber?: number
  suggestedFix?: string
  agentId: string
  // ... more fields
}

// ... more interfaces
```

### Type Safety

- All component props typed
- Store state fully typed
- API responses typed
- Event types discriminated unions
- No `any` types (except error handling)

## Accessibility Implementation

### Keyboard Navigation

Navigation flow:
1. Tab through main sections
2. Enter/Space to activate
3. Arrow keys within lists
4. Esc to close modals

Focus management:
- Visible focus rings (ring-2 ring-primary)
- Focus trap in modals
- Preserve focus on dynamic updates
- Skip links for main content

### ARIA Attributes

Implemented:
- `role="dialog"` for modals
- `role="list"` and `role="listitem"` for lists
- `role="button"` for clickable divs
- `aria-label` for icon buttons
- `aria-expanded` for collapsibles
- `aria-live="polite"` for notifications
- `aria-controls` for related elements
- `aria-valuenow/min/max` for progress bars

### Screen Reader Support

Announcements:
- Status changes via live regions
- New findings detected
- Analysis complete/failed
- Connection status changes

Text alternatives:
- All icons have labels
- Images have alt text
- Status dots have text labels
- Color not sole indicator

### Color Contrast

All text meets WCAG AA:
- Normal text: 4.5:1
- Large text: 3.0:1
- UI components: 3.0:1

Verified using:
- Chrome DevTools contrast checker
- axe DevTools
- WAVE browser extension

## Performance Optimizations

### Vue Reactivity

Optimizations:
- Computed properties for derived state
- `v-show` vs `v-if` appropriately
- Avoid unnecessary watchers
- Key attributes for lists

### Large Lists

Techniques:
- Virtual scrolling with `@vueuse/core` (ready to add)
- Pagination for message history
- Limit WebSocket event processing rate
- Debounce search/filter

### Bundle Size

Optimizations:
- Tree-shaking with ES modules
- Code splitting (router-based)
- Lazy loading components
- Minification in production

### Network

Optimizations:
- API response caching (short TTL)
- WebSocket for real-time (no polling)
- Compress payloads (gzip)
- Parallel requests where possible

## Development Workflow

### Local Development

```bash
# Start dev server
npm run dev

# Type check in watch mode
npm run type-check -- --watch

# Format code (if prettier added)
npm run format
```

### Adding New Features

1. Define types in `types/index.ts`
2. Add store actions if needed
3. Create component in `components/`
4. Add to parent component
5. Style with Tailwind
6. Add accessibility features
7. Test keyboard navigation
8. Verify screen reader support

### Debugging

Tools:
- Vue DevTools browser extension
- Browser console for logs
- Network tab for API calls
- WebSocket frame inspector
- Performance profiler

Console logging:
```typescript
console.log('WebSocket event:', event)  // Events
console.error('API Error:', error)      // Errors
```

### Code Style

Guidelines:
- Vue 3 Composition API (script setup)
- TypeScript strict mode
- Semantic HTML
- Tailwind utility classes (avoid custom CSS)
- Descriptive variable names
- Comments for complex logic
- Group related code

## Testing Strategy

### Manual Testing

Priority areas:
1. WebSocket connection stability
2. Real-time updates accuracy
3. File upload and analysis flow
4. Keyboard navigation
5. Screen reader compatibility

### Browser Testing

Test matrix:
- Chrome 90+ (primary)
- Firefox 88+
- Safari 14+ (macOS)
- Edge 90+

### Responsive Testing

Breakpoints:
- Mobile: 375px - 767px
- Tablet: 768px - 1023px
- Desktop: 1024px+

### Accessibility Testing

Tools:
- axe DevTools
- WAVE
- Lighthouse
- NVDA/JAWS (screen readers)
- Keyboard only

## Future Enhancements

### Planned Features

1. **Export functionality**
   - Export findings as JSON/CSV
   - Generate PDF reports
   - Download refactored code

2. **Search and Filter**
   - Search findings by keyword
   - Filter by severity/type
   - Search messages

3. **Agent Details Modal**
   - Click agent for detailed view
   - Show full workspace
   - View all agent messages

4. **Code Editor Integration**
   - View file in editor panel
   - Jump to line from finding
   - Apply fixes inline

5. **Batch Operations**
   - Upload multiple files
   - Bulk analysis
   - Compare analyses

6. **Settings Panel**
   - Configure thresholds
   - Customize colors
   - Enable/disable features

### Technical Debt

Items to address:
- [ ] Add comprehensive test suite (Vitest)
- [ ] Implement virtual scrolling for large lists
- [ ] Add service worker for offline support
- [ ] Optimize bundle size (code splitting)
- [ ] Add error boundary components
- [ ] Implement retry logic for failed API calls
- [ ] Add analytics/telemetry
- [ ] Improve WebSocket reconnection logic

## Deployment

### Production Build

```bash
npm run build
```

Output in `dist/`:
```
dist/
├── index.html
├── assets/
│   ├── index-[hash].js
│   ├── index-[hash].css
│   └── vendor-[hash].js
└── favicon.ico
```

### Hosting Options

1. **Static hosting** (Netlify, Vercel, GitHub Pages)
2. **CDN** (CloudFront, Cloudflare)
3. **Container** (Docker with nginx)
4. **Server** (Express serving static files)

### Environment Configuration

Production `.env`:
```env
VITE_API_BASE_URL=https://api.example.com
VITE_WS_URL=wss://api.example.com
```

### Docker Example

```dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Contributing

### Pull Request Process

1. Create feature branch
2. Make changes
3. Run type check: `npm run type-check`
4. Test thoroughly
5. Build: `npm run build`
6. Submit PR with description

### Code Review Checklist

- [ ] TypeScript types correct
- [ ] Accessibility features included
- [ ] No console errors
- [ ] Mobile responsive
- [ ] Keyboard navigable
- [ ] No performance issues
- [ ] Documentation updated

## Resources

### Documentation
- [Vue 3 Docs](https://vuejs.org)
- [Pinia Docs](https://pinia.vuejs.org)
- [Vite Docs](https://vitejs.dev)
- [TailwindCSS Docs](https://tailwindcss.com)
- [TypeScript Docs](https://www.typescriptlang.org)

### Tools
- [Vue DevTools](https://devtools.vuejs.org)
- [axe DevTools](https://www.deque.com/axe/devtools)
- [WAVE](https://wave.webaim.org/extension)

### Standards
- [WCAG 2.1](https://www.w3.org/WAI/WCAG21/quickref)
- [MDN Web Docs](https://developer.mozilla.org)
- [Vue Style Guide](https://vuejs.org/style-guide)
