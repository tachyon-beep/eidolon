# Eidolon Orchestrator UI

A modern, real-time web interface for monitoring and visualizing agent orchestration in the Eidolon agent system.

## Features

- **Real-time Updates**: WebSocket connection for live agent and finding updates
- **File Queue Management**: Track multiple file analyses with status indicators
- **Agent Visualization**: View agent flow and message passing
- **Hierarchical Assessment**: Function-level to module-level assessment with override indicators
- **Findings Panel**: Grouped by severity with expandable details
- **Accessibility**: Full keyboard navigation and screen reader support
- **Responsive Design**: Works on desktop and mobile devices

## Tech Stack

- **Vue 3** with Composition API
- **TypeScript** for type safety
- **Vite** for fast development and building
- **Pinia** for state management
- **TailwindCSS** for styling
- **Axios** for API communication
- **WebSocket** for real-time updates

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend FastAPI server running on `localhost:8000`

### Installation

```bash
# Install dependencies
npm install
```

### Development

```bash
# Start development server
npm run dev
```

The UI will be available at `http://localhost:3000`

### Build

```bash
# Type check
npm run type-check

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
ui/
├── src/
│   ├── components/          # Vue components
│   │   ├── FileQueue.vue           # File queue sidebar
│   │   ├── OrchestrationView.vue   # Agent flow visualization
│   │   ├── FindingsPanel.vue       # Findings grouped by severity
│   │   └── FileUploadModal.vue     # File upload dialog
│   ├── stores/              # Pinia stores
│   │   └── orchestration.ts        # Main state management
│   ├── services/            # API services
│   │   └── api.ts                  # API client
│   ├── types/               # TypeScript types
│   │   └── index.ts                # Type definitions
│   ├── App.vue              # Main app component
│   ├── main.ts              # App entry point
│   └── style.css            # Global styles
├── public/                  # Static assets
├── index.html              # HTML entry point
├── vite.config.ts          # Vite configuration
├── tailwind.config.js      # TailwindCSS configuration
├── tsconfig.json           # TypeScript configuration
└── package.json            # Dependencies and scripts
```

## Color System

### Severity Colors
- **Critical**: `#DC2626` (red-600)
- **High**: `#F59E0B` (amber-500)
- **Medium**: `#10B981` (green-500)
- **Low**: `#3B82F6` (blue-500)

### Status Colors
- **Queued**: `#6B7280` (gray-500)
- **Analyzing**: `#6366F1` (indigo-500)
- **Complete**: `#10B981` (green-500)
- **Failed**: `#DC2626` (red-600)

## API Endpoints

The UI communicates with the FastAPI backend:

- `GET /api/status` - Get orchestrator status
- `POST /api/analyze` - Start file analysis
- `GET /api/sessions/{id}` - Get analysis session details
- `GET /api/agents` - List active agents
- `GET /api/messages` - Get message history
- `GET /api/findings` - Get analysis findings
- `POST /api/upload` - Upload file
- `WS /ws/events` - WebSocket event stream

## WebSocket Events

Real-time events from the backend:

```typescript
type WebSocketEvent =
  | { type: 'agent_spawned'; agentId: string; role: string }
  | { type: 'message_sent'; from: string; to: string; content: string }
  | { type: 'finding_detected'; sessionId: string; finding: Finding }
  | { type: 'analysis_complete'; sessionId: string; findingsCount: number }
  | { type: 'analysis_started'; sessionId: string; filePath: string }
  | { type: 'analysis_progress'; sessionId: string; message: string }
  | { type: 'analysis_failed'; sessionId: string; error: string }
```

## Accessibility Features

- Full keyboard navigation with focus indicators
- ARIA labels and roles for screen readers
- Color contrast meeting WCAG AA standards
- Semantic HTML structure
- Live regions for dynamic updates
- Focus management for modals and dropdowns

## Performance Optimizations

- Virtual scrolling for large lists (via @vueuse/core)
- Computed properties for efficient reactivity
- Debounced search and filtering
- Lazy loading of heavy components
- Optimized re-renders with Vue's reactivity system

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run type checking: `npm run type-check`
5. Build to ensure no errors: `npm run build`
6. Submit a pull request

## License

MIT License - see LICENSE file for details
