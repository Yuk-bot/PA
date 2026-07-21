# Momentum – PlanMind AI

An AI-powered productivity companion that intelligently transforms tasks, emails, and calendar events into an actionable execution plan. Instead of simply reminding users about deadlines, Momentum proactively analyzes workload, finds free time, breaks large tasks into manageable subtasks, prioritizes them, and schedules them intelligently to maximize productivity while preventing burnout.

---

## Live Demo

**Application**: 
https://vibe2ship-863e5.web.app

---
(sorry rn GCP free billing account exhausted - switcihng to localhost)- bare with slow speed

---
# Overview

Momentum combines **manual tasks**, **Google Calendar events**, and **Gmail-derived tasks** into a single intelligent planning workflow.

The application uses AI agents to:

- Break complex tasks into smaller actionable subtasks.
- Prioritize work using deadlines and importance.
- Detect genuine free slots from the user's calendar.
- Generate an optimized execution schedule.
- Mix subtasks from different projects to reduce monotony and improve engagement.
- Continuously adapt schedules when tasks change.

Unlike traditional to-do applications, Momentum focuses on **execution planning**, not just task tracking.

---

# Key Features

- Google Calendar integration
- Gmail task extraction and suggestions
- Manual task management
- AI-powered task decomposition
- Intelligent task prioritization
- Automatic free-slot detection
- Dynamic schedule generation
- Drag-and-drop plan customization
- Expandable subtasks for every task
- Responsive modern UI built with Shadcn UI

---

## AI Agent Architecture

Momentum follows a multi-agent architecture where specialized AI agents collaborate to generate an optimized execution plan for the user.

### Agent Orchestration

When a user requests a schedule, it invokes each specialized agent sequentially, manages task flow between them, and produces the final execution plan.

### Session Management

The system maintains the active execution context throughout a planning request. ADK compoents such as planner/ and execution/ are used. It retrieves user tasks, Google Calendar events, user preferences, and previous planning information from Firestore, ensuring every planning run operates on the latest state.

### Runner

The Runner serves as the execution engine for the planning pipeline. It executes the agents asynchronously, coordinates scheduling operations, and manages background execution throughout the planning process.

### Memory and State Management

Momentum utilizes both short-term and long-term memory.

- **Short-term memory** stores the current planning context, available calendar slots, intermediate scheduling decisions, and task queues during execution.
- **Long-term memory** persists generated plans, subtasks, schedules, and user preferences in Firestore.

A unified state manager enables communication between agents. Rather than interacting directly, each agent reads the shared state, performs its assigned responsibility, writes its output back to the state, and passes execution to the next agent. Once planning is complete, the final state is persisted in Firestore.
(Still a centralized architecture betweeen agents is followed)
### Planning Agents

#### Task Decomposition Agent
- Breaks complex tasks into logical, actionable subtasks.
- Estimates the effort required for each subtask.
- Generates an executable sequence of work items.

#### Priority Agent
- Evaluates tasks using deadlines, urgency, and user-defined priority.
- Ranks tasks according to importance.
- Detects scheduling conflicts when available time is insufficient and identifies lower-priority tasks that cannot be completed before their deadlines.

#### Engagement Planner
- Retrieves verified free time slots from Google Calendar.
- Schedules subtasks within available slots while respecting working hours, productive hours, and preferred session duration.
- Mixes subtasks from different parent tasks to reduce monotony and improve engagement.
- Produces the final execution schedule and stores it in Firestore for display within the application.


---

# Tech Stack

## Frontend

- React
- Vite
- Tailwind CSS
- Shadcn UI
- Dnd Kit
- React Router

## Backend

- FastAPI
- Python
- Firebase Admin SDK
- Google ADK- for building agentic system
- Uvicorn

## Database

- Cloud Firestore

## Google Cloud

- Google Cloud Run
- Firebase Hosting
- Firestore

## Google APIs

- Gemini API
- Google Calendar API
- Gmail API
- Firebase Authentication

---

# Project Structure

```
Momentum/
│
├── backend/
│   ├── app/
│   ├── agents/
│   ├── api/
│   ├── services/
│   └── ...
│
├── frontend/
│   ├── src/
│   ├── components/
│   ├── pages/
│   ├── services/
│   └── ...
│
└── README.md
```

---

# Running Locally

## Backend

```bash
cd backend

python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt

uvicorn app.main:app --reload
```

---

## Frontend

```bash
cd frontend

npm install

npm run dev
```

---

## Environment Variables

Create the required `.env` files for both frontend and backend.

Backend requires:

- Firebase configuration
- Gemini API Key
- Google OAuth Client ID
- Google OAuth Client Secret
- Calendar Encryption Key
- Redirect URI

Frontend requires:

- Backend API URL

---

# Deployment

The application is deployed using Google Cloud Platform.

- **Frontend:** Firebase Hosting
- **Backend:** Google Cloud Run
- **Database:** Cloud Firestore

---

# Important Integration Notice

> **Google Calendar** and **Gmail** integrations currently operate in **Google OAuth Testing Mode**.

Only **pre-authorized Google accounts** added to the OAuth test users list can successfully use Calendar and Gmail integrations.

---

# AI Usage

Artificial Intelligence was used during development to assist with:

- UI and designing
- Agent workflow design
- Prompt engineering
- Planning agent implementation
- Debugging- adding print statements wherever told to add(rather than manually adding for every request or setup)
- Documentation preparation
- This readme lmao 

---

# Future Improvements

- Multi-calendar support
- Recurring task optimization
- Mobile application
- Real-time collaborative planning
- AI workload forecasting
- Adaptive scheduling based on historical productivity- adding more agents
- Adding risk calculating agent
- Improving memory, enviornment and agent interaction for perosonalisation
- Calendar write-back for generated subtasks
- Adding security to preventthe access to sensitive gmails

---
