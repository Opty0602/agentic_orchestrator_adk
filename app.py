import asyncio, sys
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
sys.path.append('/SharedResources')
from Manager import root_agent
from google.adk.sessions import InMemorySessionService, Session
from google.adk.runners import Runner
from google.genai.types import Content, Part
import uuid, json
from logging import warning,info
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

# initial_state

# creating session
session_service = InMemorySessionService()

# --------------------------
# CONFIG
# --------------------------
APP_NAME = "Manager"
SESSION_ID = "123321"
USER_ID = "user"

ROOT_AGENT = root_agent
INITIAL_STATE = {
  "user_query": None,
  "potential_solution": None,
  "n_retrieval": 3,
  "threshold_confidence": 60,
  "needed_email": False,
  "needed_knowledge": False,
  "needed_summary": False,
  "drafted_mail": None,
  "knowledge_article": None,
  "summary": None,
  "s_user_query": None,
  "s_generated_sql": None,
  "s_threshold_confidence": 80,
  "s_dryrun_validated": False,
  "s_generated_intuition": None,
  "s_n_retrieval": 3,
  "s_retreived_data": None
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    All startup logic goes before `yield`.
    All shutdown/cleanup logic goes after `yield`.
    """

    # 1) create services and persist them on app.state
    app.state.session_service = InMemorySessionService()

    # create the session (your create_session signature may differ)
    await app.state.session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
        state=INITIAL_STATE,
    )

    # 2) create a Runner bound to the app/session
    app.state.runner = Runner(
        agent=ROOT_AGENT,
        app_name=APP_NAME,
        session_service=app.state.session_service,
    )

    # Optionally start a background helper task and keep its handle
    app.state._bg_tasks = []
    # Example: a periodic cleanup or monitor
    async def _bg_worker():
        try:
            while True:
                await asyncio.sleep(60)
                # do optional periodic work, e.g., flush logs, metrics
        except asyncio.CancelledError:
            return

    bg = asyncio.create_task(_bg_worker())
    app.state._bg_tasks.append(bg)

    try:
        # the app starts serving after this yield
        yield
    finally:
        # shutdown: cancel background tasks
        for t in getattr(app.state, "_bg_tasks", []):
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass

        # best-effort runner/session cleanup
        runner = getattr(app.state, "runner", None)
        if runner is not None:
            # call whichever cleanup method exists
            close_fn = getattr(runner, "close", None) or getattr(runner, "shutdown", None)
            if callable(close_fn):
                try:
                    await close_fn()
                except Exception:
                    # swallow, but you could log
                    pass

        # session_service teardown if needed (InMemory may not need explicit close)
        svc = getattr(app.state, "session_service", None)
        if svc is not None:
            close_svc = getattr(svc, "close", None)
            if callable(close_svc):
                try:
                    await close_svc()
                except Exception:
                    pass



# --------------------------
# FASTAPI INIT
# --------------------------
app = FastAPI(title="ADK Agent API", version="1.0.0", lifespan=lifespan)
# Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# --------------------------
# REQUEST MODELS
# --------------------------
class ChatRequest(BaseModel):
    user_message: str
    # session_id :str


# --------------------------
# ENDPOINT — CHAT WITH AGENT
# --------------------------
@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    runner = app.state.runner

    # Prepare user message in ADK Content format
    content = Content(
        parts=[Part(text=req.user_message)],
        role="user"
    )

    # Run async agent pipeline
    events = []
    model_name = ""
    final_texts = []
    try:
        
        async for event in runner.run_async(user_id=USER_ID, session_id=SESSION_ID,new_message = content):
            events.append(event)
            # event_type_order.append((event.__class__,event.__class__.__name__ ))
            for event in events:
                if event.content and event.content.parts:
                    if event.is_final_response():
                        model_name = event.author
                    for part in event.content.parts:
                        if part.text:
                            if part.text not in final_texts:
                                final_texts.append({"model_name":model_name,"response":part.text})


        cleaned_final_texts = remove_duplicate_dicts(final_texts)             
        session_state = app.state.session_service.get_session_sync(app_name=APP_NAME,user_id=USER_ID,session_id=SESSION_ID).state
        print({
            "success": True,
            "responses": cleaned_final_texts or "*No response generated.*",
            
            "session_state": session_state
        })

        return {
            "success": True,
            "responses": cleaned_final_texts or "No response generated.",
            "model_name": model_name,
            "session_state": session_state
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# --------------------------
# HEALTH CHECK ENDPOINT
# --------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "session_id": SESSION_ID}

# --------------------------
# CREATE SESSION ENDPOINT
# --------------------------
@app.get("/create_session")
async def create_session():

    session_id = str(uuid.uuid4())

    try:
        await app.state.session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
        state=INITIAL_STATE,)

        info(f"SESSION CREATED WITH ID: {session_id}")
        return {"success":True, "session_id":session_id}

    except Exception as e:
        warning("SESSION NOT CREATED")
        return None
    



    ### UTILITY TOOL

def remove_duplicate_dicts(data_list):
    """
    Removes duplicate dictionaries while maintaining relative order.
    Works by serializing each dictionary to a sorted JSON string.
    """
    seen = set()
    result = []
    
    for item in data_list:
        # sort_keys=True ensures {'a': 1, 'b': 2} and {'b': 2, 'a': 1} are treated as equal
        # This handles your nested JSON strings and large text blocks efficiently
        serialized = json.dumps(item, sort_keys=True)
        
        if serialized not in seen:
            seen.add(serialized)
            result.append(item)
            
    return result

