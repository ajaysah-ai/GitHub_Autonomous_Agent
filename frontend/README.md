# GitHub Automation Agent — Frontend

A React + Vite client for the GitHub Automation Agent backend — sign up (or try the demo),
describe a goal in plain language, answer clarifications if asked, review and approve the
full plan once, and track everything in history.

---

## Table of contents

- [Tech stack](#tech-stack)
- [Folder structure](#folder-structure)
- [Pages & components](#pages--components)
- [Design system](#design-system)
- [Environment variables](#environment-variables)
- [Setup & run](#setup--run)
- [Known limitation](#known-limitation)

---

## Tech stack

| Purpose | Library |
|---|---|
| Build tool | Vite |
| UI framework | React 19 (functional components + hooks) |
| Routing | `react-router-dom` |
| Icons | `lucide-react` |
| Styling | Plain CSS with design tokens (no Tailwind/UI kit dependency) |
| API access | Native `fetch`, wrapped in a single client module |

No backend framework, no state-management library — auth/session state lives in a small
React Context, everything else is local component state fetched on demand.

---

## Folder structure

```
frontend/
├── index.html
├── package.json
├── vite.config.js
├── .env.example
└── src/
    ├── main.jsx                    # entry point
    ├── App.jsx                     # routing + auth/toast providers + route guard
    ├── index.css                   # design system (tokens, layout, components)
    ├── api/
    │   └── client.js               # every backend call, JWT/guest_id injection
    ├── context/
    │   ├── Authcontext.jsx         # JWT + guest_id session state (localStorage-backed)
    │   └── Toastcontext.jsx        # lightweight notifications
    ├── components/
    │   ├── Layout.jsx              # sidebar nav shell
    │   ├── Plandiffcard.jsx        # signature element — plan shown as a git diff
    │   ├── Messagelist.jsx         # chat log renderer
    │   └── FeedbackModal.jsx       # post-task feedback form
    └── pages/
        ├── Loginpage.jsx
        ├── Signuppage.jsx          # collects GitHub token + Groq API key up front
        ├── Demopage.jsx            # no-signup entry point
        ├── Chatpage.jsx            # core goal flow: start/clarify/approve/execute
        ├── Historypage.jsx
        ├── Filespage.jsx           # zip upload/download/delete
        ├── Allfeedbackspage.jsx    # public feedback feed
        └── Aboutpage.jsx           # project info, tools reference, security notes
```

---

## Pages & components

- **`LoginPage` / `SignupPage`** — signup takes username, password, GitHub token, and Groq
  API key in one step, so the agent never has to ask for them mid-task. Both auto-log the
  user in (JWT stored via `AuthContext`).
- **`DemoPage`** — no account needed; starts a goal restricted to `write_readme` /
  `write_requirements` and stores the returned `guest_id` for all follow-up calls.
- **`ChatPage`** — the core loop. Renders one of:
  - a goal composer (new task),
  - a clarification card + free-text reply (missing required info),
  - `PlanDiffCard` (the one-time full-plan approval),
  - a terminal state (`completed` / `blocked` / `cancelled`) with a "Leave feedback" button.
- **`PlanDiffCard`** — the signature UI element: the proposed plan rendered as a git-style
  patch (`+ create_repo(repo_name="test9")`), with **Approve & run** / **Cancel task**.
- **`HistoryPage`** — every past goal for the logged-in user; clicking one reopens it in
  `ChatPage` (reload path, see [Known limitation](#known-limitation)).
- **`FilesPage`** — drag-and-drop `.zip` upload (max 50MB), list, download, delete; works
  in both authenticated and demo mode.
- **`AllFeedbacksPage`** — public feed of every user's feedback + the goal it was for.
- **`AboutPage`** — project description, full tools reference, how-to-use steps, and a
  security/privacy summary. Edit the `AUTHOR` object at the top of the file with your own
  details.

---

## Design system

A dev-console aesthetic rather than a generic dashboard look: deep ink background,
amber accent (used for pending/diff-highlight states), teal for success, coral for
danger/cancelled. Typography: **Space Grotesk** for headings, **Inter** for body text,
**JetBrains Mono** for anything code/plan/message-related. All tokens live in
`src/index.css` as CSS custom properties (`--bg`, `--accent`, `--ok`, `--danger`, etc.) —
change them there to re-theme the whole app.

---

## Environment variables

Create `frontend/.env` (see `.env.example`):

```env
VITE_API_BASE_URL=http://localhost:8000
```

Point this at wherever `uvicorn app.api:app` is running.

---

## Setup & run

```bash
cd frontend
npm install
cp .env.example .env   # set VITE_API_BASE_URL
npm run dev            # http://localhost:5173
```

Production build:

```bash
npm run build
```

> Make sure the backend's `FRONTEND_ORIGIN` env var matches this dev server's URL, or
> requests will fail CORS.

---

## Known limitation

`GET /history/{thread_id}` currently returns only `messages` + `awaiting_input` (a
boolean) — not the original interrupt's `prompt`/`plan` text. So reopening a task from
History that's mid-clarification or mid-approval shows a generic "continue this task"
box instead of the styled clarify-card / plan-diff-card. Replies still work correctly
(the raw text is passed straight to the paused `interrupt()`), it's just less pretty
until the backend endpoint is extended to include the pending interrupt payload.

---

**Author:** [ajaysah-ai](https://github.com/ajaysah-ai/) — [LinkedIn](https://www.linkedin.com/in/ajaysah-ai/)