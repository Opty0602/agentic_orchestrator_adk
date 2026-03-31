import re
from google.genai import types
from typing import Optional, Dict, Any
import sys, os
from SharedResources.load_environment import get_client
from chromadb import PersistentClient


APP_NAME = "TEST_APP"
SESSION_ID = "123321"
USER_ID = "TEST_USER"



from google import  genai
import chromadb

import csv
import io

# from IPython.display import Markdown
from chromadb import Documents, EmbeddingFunction, Embeddings
client = get_client()




import uuid, io
import time
import numpy as np


# ---------------------------
# CONFIG (tune these)
# ---------------------------
 
CHROMA_COLLECTION = "incident_embeddingsv2_ss"
CHROMA_PERSIST_PATH = "./Manager/sub_agents/incident_management_agent/chromad_new"
# ---------------------------
# PLACEHOLDER HELPERS (replace these)
# ---------------------------

async def get_embbed(text:str, model_id:str = "text-embedding-005"):
   
    response = client.models.embed_content(
    model=model_id,
    contents=text,
    config=types.EmbedContentConfig(
        task_type="SEMANTIC_SIMILARITY"
    ),)
    return response.embeddings[0].values

# async def add_document(incident_data:dict, id:str,timestamp,  collection_name: str, model_id: str = "text-embedding-005",):

#     try:
#         chroma_client = PersistentClient(path="/home/shared/Symbiose/adk_usecase/serviceNow_chat_adk/test_chromad")
#         collection = chroma_client.get_or_create_collection(name=collection_name)

#         embedding = await get_doc_embeddings(incident_data,model_id)
#         collection.add(ids = [id],
#                         documents =
#                             f"""
#                             title: {incident_data['title']},
#                             application_id: {incident_data['application_id']},
#                             incident_creation_time: {timestamp},
#                             resolution_timestamp: {int(time.time())},
#                             description: {incident_data['description']},
#                             cause : {incident_data['cause']},
#                             resolution: {incident_data['resolution']},
#                             severity: {incident_data['severity']}
#                             """,
#                         embeddings = [embedding],
                    
#                         # ----- METADATA CANNOT BE OF DICTIONARY TYPE
#                         )
#     except Exception as e:
#         return f"There was a error loading the documents. \n{e}"



async def llm_validate_conformance(
        user_query:str,
    retrieved_solution: str,
    potential_solution: str,
    suggested_solution: Optional[str]
) -> Dict[str, Any]:
    

    system_instructions = """You are an incident feedback processor.

Inputs:
1. canonical_text — factual description of a historical incident from records.
2. incident_solution — the stored resolution for that incident.
3. suggested_solution — a new resolution proposed by a user.

Your task:
- Determine if suggested_solution is:
  (a) equivalent to incident_solution,
  (b) an improvement or valid variation,
  (c) unrelated or incorrect.
- If (a) or (b), produce a JSON object in the exact canonical format used for storing incidents in the database, integrating the suggested_solution in place of `resolution` where appropriate.
- If (c), output {"status": "discard"}.

Important:
- Preserve metadata fields that exist in canonical_text if available (e.g., incident_id, category, severity).
- If no metadata is in canonical_text, fill with `null` or defaults.
- Ensure final "resolution" field contains a clean, concise, complete resolution.
---

Example Input in the database:
```json
{ 
'title': 'Service Crash on cache5.prod.net',
'application_id': 'APP-105',
'incident_creation_time': '2025-05-22 08:47 UTC',
'cause':"Resource exhaustion on cache5.prod.net",
'resolution': 'Flushed DNS cache on cache5.prod.net:1045',
'description': 'On 2025-05-22 08:47 UTC, the message-queue running on cache5.prod.net:1045 experienced a service crash. The issue led to connection errors, impacting approximately 77%/ of service traffic. Severity: Low.',
'severity': 'Low'}
```

---
Output format for accepted incidents:
```json
{
"title" : <a suitable title>,
"application_id": <random string like APP-821>,
"cause" : <your inferred reasoning here>,
"resolution": < resolution here >,
"description": <user query in proper manner>,
"severity": <low | medium | high>
                        
}
```
---
If unrelated:
{"status": "discard"}
"""
    prompt = f"""Here is the Input:
incident — {user_query}
canonical_text — {retrieved_solution}
incident_solution — {potential_solution}
suggested_solution — {suggested_solution}
"""
    # --- PLACEHOLDER: call your LLM here and parse output ---
    client = get_client()
    response = client.models.generate_content(model="gemini-2.0-flash",contents = prompt,
                                                    config=types.GenerateContentConfig(response_mime_type="application/json",
                                                                                       system_instruction=system_instructions,
                                                                                    #    thinking_config=types.ThinkingConfig(thinking_budget=256)
                                                                                       )
                                                    )
    try:
        response = eval(response.text)

    except Exception as e:
        print("There wa some error cvaluating in llm_validate_conformance call.")
        return response.text
    return response


import json
from datetime import datetime
from pathlib import Path

LOG_FILE = "incident_feedback_log.jsonl"

def log_feedback(log_entry):
    """
    Append feedback data to a JSONL file for POC logging.
"""
    try:
        with open(file=LOG_FILE,mode= "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        print(f"[log_feedback] Entry logged at {LOG_FILE}")
    except Exception as e:
        print(f"[log_feedback] Failed to log entry: {e}")



# ---------------------------
# Utility functions
# ---------------------------

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return float(np.dot(a, b) / (a_norm * b_norm))


def get_chroma_collection() -> chromadb.Collection:
    # Use the PersistentClient (you used earlier). Adapt path if needed.
    client = PersistentClient(path=CHROMA_PERSIST_PATH)
    collection = client.get_collection(CHROMA_COLLECTION)
    return collection


# ---------------------------
# The actual tool
# ---------------------------
import uuid, time
from typing import Optional, Dict, Any
from google.adk.tools.tool_context import ToolContext

# thresholds (tune as needed)
HIGH_THRESHOLD = 0.82
MEDIUM_THRESHOLD = 0.60

async def incident_support_logger(
    user_query: str,
    potential_solution: str,
    suggested_solution: Optional[str] = None,
    inc_id: Optional[str] = None,
) -> Dict[str, Any]:
    
    """
Handles feedback on incident solutions.

Call only when the user provides a suggestion and preferably an incident ID.
- user_query: Original user request or problem description.
- potential_solution: Current best-known solution retrieved from the system.
- suggested_solution: User-proposed solution (optional).
- inc_id: Associated incident ID (optional).

Returns:
- Logging status done via tool
"""




    timestamp = time.asctime()
    log_id = str(uuid.uuid4())
    log_entry = {
        "log_id": log_id,
        "timestamp": timestamp,
        "user_query": user_query,
        "potential_solution": potential_solution,
        "suggested_solution": suggested_solution,
        "provided_incident_id": inc_id,}

    # quick sanity
    if not suggested_solution:
        log_entry["result"] = "no_suggestion_provided"
        log_feedback(log_entry)
        return {"status": "no_suggestion", "log_id": log_id}

    # if inc_id supplied -> validate against canonical incident
    if inc_id:
        collection = get_chroma_collection()
        try:
            res = collection.get(ids=[inc_id])
            docs = res.get("documents", [])
            metas = res.get("metadatas", [])
            if not docs:
                log_entry["result"] = "inc_id_not_found"
                log_feedback(log_entry)
                return {"status": "inc_id_not_found", "log_id": log_id}
            canonical_text = docs[0]


            # embed and compare
            emb_truth = await get_embbed(canonical_text)
            emb_sugg = await get_embbed(suggested_solution)
            sim = cosine_sim(emb_truth, emb_sugg)

            log_entry.update({
                
                "similarity_suggested_to_truth": sim
            })

            if sim >= MEDIUM_THRESHOLD:
                # borderline -> call LLM verifier (optional)
                print()
                llm_v = await llm_validate_conformance(user_query,canonical_text, potential_solution, suggested_solution)
                
                match = llm_v.get("status", "add")
                print(match)
 
                if match.lower() == "add":
                    # insert but mark provenance add timestamp
                    incident_data = llm_v
                    # await add_document(incident_data=incident_data, timestamp=timestamp, id = id, collection_name="test_collection")
                    log_entry["llm_verdict"] = llm_v
                    log_entry["result"] = "inserted_after_llm"
                    log_feedback(log_entry)
                    return {"status": "inserted_after_llm", "similarity": sim, "log_id": log_id}
                else:
                    log_entry["result"] = "llm_rejected"
                    log_entry["llm_verdict"] = llm_v
                    log_feedback(log_entry)
                    return {"status": "rejected_by_llm", "similarity": sim, "llm": llm_v, "log_id": log_id}
            else:
                log_entry["result"] = "low_similarity_no_insert"
                log_feedback(log_entry)
                return {"status": "no_insert_low_similarity", "similarity": sim, "log_id": log_id}

        except Exception as e:
            log_entry["error"] = str(e)
            log_feedback(log_entry)
            return {"status": "error", "error": str(e), "log_id": log_id}

    # if inc_id not supplied -> just structure & log, do NOT insert
    else:
        log_entry["result"] = "logged_no_inc_id"
        # add a flag so humans can review later if desired
        log_entry["review_required"] = True
        log_feedback(log_entry)
        return {"status": "logged_for_review", "log_id": log_id}
    


def sql_support_logger(
    user_query: str,
    potential_sql: str,
    issue_or_suggestion: str,
    log_file: str = "sql_feedback_log.jsonl"
) -> dict:
    """
    Logs SQL agent feedback into a JSON file.

    Args:
        user_query (str): The query provided by the user that led to the SQL generation.
        potential_sql (str): The SQL query generated by the agent.
        issue_or_suggestion (str): The issue faced or suggestion given by the user.
        log_file (str): Path to the JSON log file (default: 'sql_feedback_log.json').
    """


    try:
        feedback_entry = {
        "feedback_id": str(uuid.uuid4()),
        "timestamp": time.asctime(),
        "user_query": user_query,
        "potential_sql": potential_sql,
        "issue_or_suggestion": issue_or_suggestion
    }
        # Load existing logs if file exists
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logs = []

        logs.append(feedback_entry)

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=4)

        print(f"[LOGGED] Feedback recorded with ID: {feedback_entry['feedback_id']}")
        return {"status":f"Feedback recorded with ID: {feedback_entry['feedback_id']}"}
    except Exception as e:
        print(f"[ERROR] Failed to log feedback: {e}")
        return {"status": "[ERROR] Failed to log feedback: {e}"}

