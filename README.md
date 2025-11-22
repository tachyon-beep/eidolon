# MONAD — Hierarchical Agent System

**"Recursive unity made manifest."**

MONAD is a hierarchical intelligence system where agents analyze code at multiple levels (system → module → function), with insights flowing upward to create unified meta-perspectives.

## Architecture

### Core Concepts

- **Cards**: Every work item is a card. Cards can be broken down and routed between different system tabs.
- **Hierarchical Agents**: Agents deploy at system, module, and function levels, each analyzing their scope and reporting upward.
- **Six Domains**: Explore, Code, Repair, Test, Plan, Design (MVP implements Explore, Code, Plan)

### MVP Features

- ✅ Card-based work tracking system
- ✅ 3-level agent hierarchy (System → Module → Function)
- ✅ Code analysis with AST and pattern detection
- ✅ Agent inspection ("snoop" view)
- ✅ Card routing between tabs
- ✅ Real-time updates via WebSocket
- ✅ Vue 3 frontend with clean UX

## Project Structure

```
monad/
├── backend/              # FastAPI backend
│   ├── models/          # Data models (cards, agents)
│   ├── agents/          # Agent orchestration and hierarchy
│   ├── analysis/        # Code analysis tools
│   ├── api/             # REST and WebSocket endpoints
│   └── storage/         # SQLite database layer
├── frontend/            # Vue 3 frontend
│   ├── src/
│   │   ├── components/  # Vue components
│   │   ├── views/       # Tab views
│   │   └── stores/      # State management
│   └── public/
├── examples/            # Sample code for analysis
└── docs/               # Documentation
```

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 16+
- Anthropic API key ([Get one here](https://console.anthropic.com/))

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set your API key:**
   ```bash
   export ANTHROPIC_API_KEY=your_key_here  # Linux/Mac
   # or
   set ANTHROPIC_API_KEY=your_key_here  # Windows
   ```

5. **Run the server:**
   ```bash
   python main.py
   ```

   Backend runs on `http://localhost:8000`

### Frontend Setup

1. **Open a new terminal and navigate to frontend:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Run the development server:**
   ```bash
   npm run dev
   ```

   Frontend runs on `http://localhost:5173`

### Try It Out

1. Open your browser to `http://localhost:5173`
2. In the **Explore** tab, enter `../examples` as the analysis path
3. Click **Analyze** to deploy the hierarchical agent mesh
4. Watch as agents analyze the code at different levels (System → Module → Function)
5. View the generated cards showing bugs, code smells, and improvement opportunities
6. Click any card to see details and open the **Agent Snoop** tab to inspect the agent's reasoning
7. Drag cards to different tabs using the left dock icons

## Usage

1. **Explore Tab**: Upload or point to a codebase. Click "Analyze" to deploy the agent hierarchy.
2. **View Cards**: Each analysis produces cards showing issues, enhancements, and code smells.
3. **Inspect Agents**: Click any agent card to open the "snoop" view and see its reasoning.
4. **Route Cards**: Drag cards to other tabs or use the route button to move work items.

## Card Types

- **Review** (Explore): Code audit findings
- **Change** (Code): Proposed code changes
- **Architecture** (Plan): System design decisions
- **Test** (Test): Test requirements
- **Defect** (Repair): Bug reports
- **Requirement** (Design): Product requirements

## Agent Hierarchy

```
SystemAgent
  ├─> ModuleAgent (per .py file)
  │     ├─> FunctionAgent (per function/class)
  │     └─> FunctionAgent
  └─> ModuleAgent
        └─> FunctionAgent
```

## Development Roadmap

### MVP (Current)
- [x] Core card system
- [x] 3-level agent hierarchy
- [x] Basic code analysis
- [x] Explore, Code, Plan tabs
- [x] Agent inspection

### Phase 2
- [ ] Repair tab with bug triage
- [ ] Test tab with TDD guardians
- [ ] Design tab with requirements chat
- [ ] Advanced contestability system
- [ ] Risk and confidence scoring

### Phase 3
- [ ] Multi-language support
- [ ] Integration with CI/CD
- [ ] Team collaboration features
- [ ] Historical analysis and trends

## Philosophy

> *In Leibniz's Monadology, every monad reflects the entire universe from its perspective — exactly like this design, where each agent reflects the system through its analytical scope.*

Every agent is a microcosm of the whole, performing analysis, self-reflection, and synthesis, reporting upward until the system forms a unified meta-perspective.

## License

MIT
