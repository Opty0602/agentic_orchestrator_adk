import re
from google.genai import types

from google.adk.tools.tool_context import ToolContext

import sys
sys.path.append('SharedResources')
from SharedResources.load_environment import get_client
from chromadb import PersistentClient


APP_NAME = "TEST_APP"
SESSION_ID = "123321"
USER_ID = "TEST_USER"
CHROMA_COLLECTION = "incident_embeddingsv2_ss"
CHROMA_PERSIST_PATH = "./Manager/sub_agents/incident_management_agent/chromad_new"

async def session_create(session_service, app_name,user_id, session_id, state):
        await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state = state)
        return 


######## NEW DATA FETCHING IMPLEMENTATION #######
#################################################


chroma_client = PersistentClient(path=CHROMA_PERSIST_PATH)
client = get_client()

# --- helpers for key compatibility and cleaning ---

def _clean(s: str) -> str:
    if s is None:
        return ""
    s = str(s).replace("\u0000", " ")
    return re.sub(r"\s+", " ", s).strip()

def _get(row: dict, *candidates: str) -> str:
    """Try multiple key variants and return the first non-empty value."""
    for k in candidates:
        v = row.get(k)
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return ""


# --- embeddings ---
#while creating incidents
def get_embeddings(incident_data: dict, model_id: str):
    """
    Build the text to embed using either underscore or space keys and return list[float] embedding.
    """
    description = _get(incident_data, "Incident_description", "Incident Description")
    title = _get(incident_data, "Incident_title", "Incident Title")
    cause = _get(incident_data, "Incident_cause", "Root Cause")
    resolution = _get(incident_data, "Incident_resolution", "Resolution")

    contents = f"""
title: {_clean(title)}
Issue occured: {_clean(description)}
"""

    response = client.models.embed_content(
        model=model_id,
        contents=contents,
        config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
    )

    # normalize to list[float]
    emb = response.embeddings[0]
    values = getattr(emb, "values", emb)
    return list(values)

# --- ingestion ---

# def add_document_from_file(file_path: str, collection_name: str, model_id: str = "text-embedding-005"):
#     """
#     Load CSV file and add documents to ChromaDB collection.
#     """
#     try:
#         with open(file_path, 'r', encoding='utf-8') as file:
#             reader = csv.DictReader(file)

#             collection = chroma_client.get_or_create_collection(name=collection_name)

#             count = 0
#             for incident_data in reader:
#                 embedding = get_embeddings(incident_data, model_id)

#                 # Accept both "Incident ID" and "Incident_id"
#                 doc_id = _get(incident_data, "Incident ID", "Incident_id")
#                 if not doc_id:
#                     print("[WARN] Skipping row without Incident ID / Incident_id")
#                     continue

#                 title = _get(incident_data, "Incident_title", "Incident Title")
#                 description = _get(incident_data, "Incident_description", "Incident Description")
#                 cause = _get(incident_data, "Incident_cause", "Root Cause")
#                 resolution = _get(incident_data, "Incident_resolution", "Resolution")

#                 collection.add(
#                     ids=[doc_id],
#                     documents=[
#                         f"""title: {title},
# description: {description},
# """
#                     ],
#                     embeddings=[embedding],
#                     metadatas=[{
#                         'cause': cause,
#                         'resolution': resolution
#                     }]
#                 )
#                 count += 1
#                 print(f"Added document {count}: {doc_id}")

#             print(f"\nSuccessfully added {count} documents to collection '{collection_name}'")
#             return f"Success: {count} documents added"

#     except FileNotFoundError:
#         return f"Error: File not found at {file_path}"
#     except Exception as e:
#         return f"There was an error loading the documents.\n{e}"







def get_relevant_passage(user_query, collection_name, n_results=5, model_id: str = "gemini-embedding-001"):

    collection = chroma_client.get_collection(collection_name)
    text_embedding = client.models.embed_content(
        model=model_id,
        contents=_clean(user_query),
        config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
    )
    q_vec = getattr(text_embedding.embeddings[0], "values", text_embedding.embeddings[0])

    incident = collection.query(
        query_embeddings=[q_vec],
        n_results=n_results,
        include=["documents", "distances", "metadatas"] 
    )
    return incident

# Tool for the incident agent
def get_historical_incident(query: str, n_results: int = 5):
    '''Fetches the most similar historical incident based on the user's incident query.'''

    model_id: str = "gemini-embedding-001"

    collection_name = "incident_embeddingsv2_ss"
    print(f"\n{'='*80}")
    print(f"TESTING QUERY: '{query}'")
    print(f"Collection: {collection_name}")
    print(f"{'='*80}\n")

    try:
        results = get_relevant_passage(query, collection_name, n_results=n_results, model_id=model_id)

        # Handle empty set gracefully
        docs_group = results.get('documents', [[]])[0]
        if not docs_group:
            print("No results found.")
            return {"tool_status":"success","result":"No results found."}

        print(f"Found {len(docs_group)} relevant incidents:\n")

        ids_group = results.get('ids', [[]])[0]
        dists_group = results.get('distances', [[]])[0]
        metas_group = results.get('metadatas', [[]])[0]
        extra_info = retreived_result_string = ""
        for i, (doc_id, document, distance, metadata) in enumerate(zip(
            ids_group,
            docs_group,
            dists_group,
            metas_group
        ), 1):
                           
            print(f"--- Result {i} ---")
            print(f"Incident ID: {doc_id}")
            # Distance -> similarity (approx) if distances are 0..2 range; for cosine this is safe as 1 - distance
            print(f"Similarity Score: {1 - float(distance):.4f}")
            print(f"Distance: {float(distance):.4f}")
            print(f"\nDocument Content:")
            print(document)
            
            if metadata:
                print(f"\nMetadata:")
                if isinstance(metadata, dict):
                    if 'cause' in metadata:
                        cause= metadata['cause']
                        print(f"  Cause: {metadata['cause']}")
                    if 'resolution' in metadata:
                        resolution = metadata['resolution']
                        print(f"  Resolution: {metadata['resolution']}")
                    # Print other keys too
                    other_keys = {k: v for k, v in metadata.items() if k not in ('cause', 'resolution')}
                    for k, v in other_keys.items():
                        extra_info = f"{k}: {v}"
                        print(f"  {k}: {v}")
            print(f"\n{'-'*80}\n")
            retreived_result_string += f"""
--- Result {i} ---
Incident ID: {doc_id}
Document Content:\n{document}
Cause: {metadata.get('cause','')}
Resolution: {metadata.get('resolution','')}"
{extra_info}

---

"""

        return {"tool_status":"pass","user_query":query,"retrieved_incidents":retreived_result_string}

    except Exception as e:
        print("ERROR:\n", {e})
        return {"tool_status": "fail",
                "error_mesage": f"there was some error fetching the data. ERROR: {e}"}
    
def fallback_solution_tool(incident_query:str)-> dict:
    '''Fetches the most similar historical incident based on the user's incident query.
    
    Call this a fallback, fetched 10 similar historical incidents'''


    try:
        

        
        formatted_incidents = get_historical_incident(query = incident_query,n_results=10 )
        return formatted_incidents
    
    except Exception as e: 
        print("ERROR:\n", {e})
        return {"tool_status": "fail",
                "error_mesage": f"there was some error fetching the data. ERROR: {e}"}



async def exit_loop(tool_context: ToolContext) -> dict:
    """
    Call this function ONLY when **Solution State passes** the validation checks,
    signaling the iterative process should end.

    """
    print(f"[Tool Call] exit_loop triggered by {tool_context.agent_name}")
   

    tool_context.actions.escalate = True

    return {}
