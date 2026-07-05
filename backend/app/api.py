"""
FastAPI Integration — GitHub Automation Agent (v2)
=====================================================
Naya flow: signup (github_token + groq_api_key yahi le liye jaate hain) ->
login (JWT, 24h) -> goal start/resume. Demo route sirf write_readme /
write_requirements allow karta hai, signup ki zaroorat nahi.

Run:
    uvicorn app.api:app --reload --port 8000

.env:
    MCP_SERVER_URL, GROQ_API_KEY (demo fallback), APP_ENCRYPTION_KEY,
    JWT_SECRET_KEY, FRONTEND_ORIGIN
"""

from __future__ import annotations

from logging import root
import asyncio, sys
import os
import uuid
from contextlib import asynccontextmanager, AsyncExitStack
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from langgraph.types import Command
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage

from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from graphs.action_execute_graph import (
    get_action_execute_graph,
    create_store,
    resolve_app_context,
    build_demo_app_context,
    save_user_credentials,
    initial_state,
)
from security.auth import (
    create_user_account, verify_login, user_exists,
    create_access_token, decode_access_token, AuthError,
)
from security.workspace import (
    extract_zip_safely, zip_folder_for_download, list_projects, delete_project,
    cleanup_stale_guest_workspaces, MAX_UPLOAD_BYTES, WorkspaceSecurityError,
)
from feedbacks.feedback_store import save_feedback, list_all_feedback

load_dotenv()

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8080/mcp")
OWNER_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
GUEST_WORKSPACE_TTL_SECONDS = 24 * 60 * 60  # 24h, confirmed with user

#-----------------------------------------------------------------
# Lifespan: MCP session + store + graph created once; a background loop
# purges stale guest_* workspaces every hour (TTL = 24h).
#-----------------------------------------------------------------
async def _cleanup_loop():
    while True:
        try:
            removed = cleanup_stale_guest_workspaces(GUEST_WORKSPACE_TTL_SECONDS)
            if removed:
                print(f"[cleanup] removed stale guest workspaces: {removed}")
        except Exception as e:
            print(f"[cleanup] error: {e}")
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    stack = AsyncExitStack()
    transport = await stack.enter_async_context(streamable_http_client(MCP_SERVER_URL))
    read_stream, write_stream, _ = transport
    session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
    await session.initialize()

    store, store_conn = await create_store()
    graph, graph_conn = await get_action_execute_graph()

    app.state.session = session
    app.state.store = store
    app.state.graph = graph

    cleanup_task = asyncio.create_task(_cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        await graph_conn.close()
        await store_conn.close()
        await stack.aclose()


app = FastAPI(title="GitHub Automation Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#-----------------------------------------------------------------
# Auth dependency helpers
#-----------------------------------------------------------------
def _extract_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


def require_username(authorization: Optional[str] = Header(None)) -> str:
    token = _extract_bearer(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        return decode_access_token(token)
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))


def optional_username(authorization: Optional[str] = Header(None)) -> Optional[str]:
    token = _extract_bearer(authorization)
    if not token:
        return None
    try:
        return decode_access_token(token)
    except AuthError:
        return None


#-----------------------------------------------------------------
# Request / Response models
#-----------------------------------------------------------------
class SignupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, description="Plaintext at signup — hashed (bcrypt) before storage")
    github_token: str = Field(..., description="GitHub PAT — required at signup so it's never needed mid-conversation")
    groq_api_key: str = Field(..., description="User's own Groq API key — required at signup")


class LoginRequest(BaseModel):
    username: str
    password: str


class StartGoalRequest(BaseModel):
    goal: str = Field(..., description="Natural language goal")


class ResumeGoalRequest(BaseModel):
    thread_id: str
    user_input: str = Field(..., description="Reply to the pending clarification/approval prompt")


class DemoStartRequest(BaseModel):
    goal: str


class DemoResumeRequest(BaseModel):
    guest_id: str
    thread_id: str
    user_input: str


class FeedbackRequest(BaseModel):
    thread_id: str
    guest_id: Optional[str] = Field(None, description="Required only if not authenticated (demo threads)")
    rating: Optional[str] = Field(None, description="Defaults to 'good' if omitted")
    comment: Optional[str] = Field(None, description="Defaults to 'good' if omitted")


class GoalResponse(BaseModel):
    thread_id: str
    status: str  # "awaiting_clarification" | "awaiting_approval" | "completed" | "blocked" | "cancelled"
    prompt: Optional[str] = None
    plan: Optional[List[Dict[str, Any]]] = None
    messages: List[Dict[str, str]]
    completed: bool = False


#-----------------------------------------------------------------
# Helpers
#-----------------------------------------------------------------
def _serialize_messages(messages: list) -> List[Dict[str, str]]:
    out = []
    for m in messages or []:
        role = "human" if isinstance(m, HumanMessage) else "ai"
        out.append({"role": role, "content": m.content})
    return out


def _build_goal_response(thread_id: str, result: dict) -> GoalResponse:
    if result.get("__interrupt__"):
        intr = result["__interrupt__"][0].value
        status = "awaiting_approval" if "plan" in intr else "awaiting_clarification"
        return GoalResponse(
            thread_id=thread_id, status=status, prompt=intr.get("message"),
            plan=intr.get("plan"), messages=_serialize_messages(result.get("messages", [])), completed=False,
        )
    completed = bool(result.get("completed", False))
    is_normal = result.get("is_normal", True)
    if completed:
        status = "completed"
    elif is_normal is False:
        status = "blocked"
    else:
        status = "cancelled"
    return GoalResponse(thread_id=thread_id, status=status,
                         messages=_serialize_messages(result.get("messages", [])), completed=completed)


async def _thread_belongs_to_user(username: str, thread_id: str) -> bool:
    item = await app.state.store.aget(namespace=("users", username), key="user_info")
    if not item:
        return False
    return thread_id in item.value.get("thread_id", [])


#-----------------------------------------------------------------
# Auth endpoints
#-----------------------------------------------------------------
@app.post("/auth/signup")
async def signup(req: SignupRequest):
    """Signup ke waqt hi github_token + groq_api_key le liye jaate hain (encrypted store) —
    isliye baad me kabhi in cheezo ke liye goal beech me rukna nahi padta."""
    if await user_exists(app.state.store, req.username):
        raise HTTPException(status_code=409, detail="Username already exists")
    await create_user_account(app.state.store, req.username, req.password)
    await save_user_credentials(app.state.store, req.username, github_token=req.github_token, groq_api_key=req.groq_api_key)
    token = create_access_token(req.username)
    return {"status": "signed_up", **token}


@app.post("/auth/login")
async def login(req: LoginRequest):
    if not await verify_login(app.state.store, req.username, req.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return create_access_token(req.username)


#-----------------------------------------------------------------
# Goal endpoints (authenticated)
#-----------------------------------------------------------------
@app.post("/goal/start", response_model=GoalResponse)
async def start_goal(req: StartGoalRequest, username: str = Depends(require_username)):
    thread_id = str(uuid.uuid4())
    config = RunnableConfig({"configurable": {"thread_id": thread_id}})
    app_context = await resolve_app_context(app.state.store, username, config, app.state.session, OWNER_GROQ_API_KEY)
    try:
        result = await app.state.graph.ainvoke(initial_state(req.goal), config=config, context=app_context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {e}")
    return _build_goal_response(thread_id, result)


@app.post("/goal/resume", response_model=GoalResponse)
async def resume_goal(req: ResumeGoalRequest, username: str = Depends(require_username)):
    if not await _thread_belongs_to_user(username, req.thread_id):
        raise HTTPException(status_code=404, detail="Thread not found for this user")
    config = RunnableConfig({"configurable": {"thread_id": req.thread_id}})
    app_context = await resolve_app_context(app.state.store, username, config, app.state.session, OWNER_GROQ_API_KEY)
    try:
        result = await app.state.graph.ainvoke(Command(resume={"user_input": req.user_input}), config=config, context=app_context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {e}")
    return _build_goal_response(req.thread_id, result)


#-----------------------------------------------------------------
# Demo endpoints (no signup — write_readme / write_requirements only)
#-----------------------------------------------------------------
@app.post("/demo/start", response_model=GoalResponse)
async def demo_start(req: DemoStartRequest):
    guest_id = f"guest_{uuid.uuid4().hex[:12]}"
    thread_id = str(uuid.uuid4())
    config = RunnableConfig({"configurable": {"thread_id": thread_id}})
    app_context = build_demo_app_context(config, app.state.session, app.state.store, guest_id, OWNER_GROQ_API_KEY)
    try:
        result = await app.state.graph.ainvoke(initial_state(req.goal), config=config, context=app_context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {e}")
    resp = _build_goal_response(thread_id, result).model_dump()
    resp["guest_id"] = guest_id  # frontend must store this — it's the only way back into this session
    return resp


@app.post("/demo/resume", response_model=GoalResponse)
async def demo_resume(req: DemoResumeRequest):
    if not await _thread_belongs_to_user(req.guest_id, req.thread_id):
        raise HTTPException(status_code=404, detail="Thread not found for this guest session")
    config = RunnableConfig({"configurable": {"thread_id": req.thread_id}})
    app_context = build_demo_app_context(config, app.state.session, app.state.store, req.guest_id, OWNER_GROQ_API_KEY)
    try:
        result = await app.state.graph.ainvoke(Command(resume={"user_input": req.user_input}), config=config, context=app_context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {e}")
    return _build_goal_response(req.thread_id, result)


#-----------------------------------------------------------------
# History endpoints (authenticated)
#-----------------------------------------------------------------
@app.get("/history")
async def list_history(username: str = Depends(require_username)):
    item = await app.state.store.aget(namespace=("users", username), key="user_info")
    if not item:
        return {"threads": []}
    data = item.value
    threads = []
    for tid, goal in zip(data.get("thread_id", []), data.get("goal", [])):
        config = RunnableConfig({"configurable": {"thread_id": tid}})
        snapshot = await app.state.graph.aget_state(config)
        state = snapshot.values if snapshot else {}
        msgs = state.get("messages", [])
        threads.append({
            "thread_id": tid, "goal": goal,
            "completed": state.get("completed", False),
            "awaiting_input": bool(snapshot.next) if snapshot else False,
            "last_message": msgs[-1].content if msgs else None,
        })
    threads.reverse()
    return {"threads": threads}


@app.get("/history/{thread_id}")
async def get_thread_detail(thread_id: str, username: str = Depends(require_username)):
    if not await _thread_belongs_to_user(username, thread_id):
        raise HTTPException(status_code=404, detail="Thread not found for this user")
    config = RunnableConfig({"configurable": {"thread_id": thread_id}})
    snapshot = await app.state.graph.aget_state(config)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=404, detail="No state found for this thread")
    state = snapshot.values
    return {
        "thread_id": thread_id, "goal": state.get("goal"),
        "messages": _serialize_messages(state.get("messages", [])),
        "completed": state.get("completed", False),
        "awaiting_input": bool(snapshot.next),
    }


#-----------------------------------------------------------------
# File upload/download (workspace isolation — see security/workspace.py)
#-----------------------------------------------------------------
@app.post("/files/upload")
async def upload_project(project_name: str = Form(...), file: UploadFile = File(...), username: str = Depends(require_username)):
    return await _handle_upload(username, project_name, file)


@app.get("/files/list")
async def list_files(username: str = Depends(require_username)):
    return {"projects": list_projects(username)}


@app.get("/files/download/{project_name}")
async def download_project(project_name: str, username: str = Depends(require_username)):
    return _handle_download(username, project_name)


@app.delete("/files/{project_name}")
async def remove_project(project_name: str, username: str = Depends(require_username)):
    try:
        delete_project(username, project_name)
    except WorkspaceSecurityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "deleted"}


# --- Demo equivalents (guest_id instead of JWT username) ---
@app.post("/demo/files/upload")
async def demo_upload_project(guest_id: str = Form(...), project_name: str = Form(...), file: UploadFile = File(...)):
    return await _handle_upload(guest_id, project_name, file)


@app.get("/demo/files/list/{guest_id}")
async def demo_list_files(guest_id: str):
    return {"projects": list_projects(guest_id)}


@app.get("/demo/files/download/{guest_id}/{project_name}")
async def demo_download_project(guest_id: str, project_name: str):
    return _handle_download(guest_id, project_name)


async def _handle_upload(owner_id: str, project_name: str, file: UploadFile):
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are accepted")
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large (max {MAX_UPLOAD_BYTES // (1024*1024)}MB)")
    try:
        dest, skipped = extract_zip_safely(content, owner_id, project_name)
    except WorkspaceSecurityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "uploaded", "project_name": project_name, "skipped_unsafe_entries": skipped}


def _handle_download(owner_id: str, project_name: str):
    try:
        zip_path = zip_folder_for_download(owner_id, project_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except WorkspaceSecurityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return FileResponse(path=str(zip_path), filename=f"{project_name}.zip", media_type="application/zip")


#-----------------------------------------------------------------
# Feedback
#-----------------------------------------------------------------
@app.post("/feedback")
async def submit_feedback(req: FeedbackRequest, authorization: Optional[str] = Header(None)):
    resolved_username = optional_username(authorization)
    if not resolved_username:
        if not req.guest_id:
            raise HTTPException(status_code=400, detail="guest_id required when not logged in")
        resolved_username = req.guest_id

    if not await _thread_belongs_to_user(resolved_username, req.thread_id):
        raise HTTPException(status_code=404, detail="Thread not found for this user")

    config = RunnableConfig({"configurable": {"thread_id": req.thread_id}})
    snapshot = await app.state.graph.aget_state(config)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=404, detail="Thread state not found")
    state = snapshot.values

    entry = await save_feedback(
        app.state.store, thread_id=req.thread_id, username=resolved_username,
        goal=state.get("goal", ""), goal_achieved=bool(state.get("completed", False)),
        rating=req.rating, comment=req.comment,
    )
    return {"status": "saved", "feedback": entry}


@app.get("/all_feedbacks")
async def all_feedbacks():
    """Public — sabhi users ek dusre ke feedback (goal ke saath) dekh sakte hain."""
    return {"feedbacks": await list_all_feedback(app.state.store)}


@app.get("/health")
async def health():
    return {"status": "ok"}