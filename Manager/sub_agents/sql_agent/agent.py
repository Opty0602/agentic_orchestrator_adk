from google.adk.agents import Agent, LoopAgent
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool


from .tools import exit_loop, get_sql_query, big_query_output, fallback_solution_tool


from .callbacks import *


APP_NAME = "TEST_APP"
SESSION_ID = "123321"
USER_ID = "TEST_USER"

initial_session_state ={
    's_user_query': None,
    's_generated_sql': None,
    's_threshold_confidence': 80,
    's_dryrun_validated': False,
    's_generated_intuition':None,
    's_n_retrieval': 3,
    's_retreived_data': None  
}

solution_generator_agent = Agent(
    name="solution_generator_agent",
    description="Handles data request related queries and provides output sql query and data from database",
    model="gemini-2.5-flash",
instruction = '''

You are the Solution Generator Agent inside a LoopAgent. Your job is to propose a SQL query and intuition to the current user query using fresh retrieval each iteration.
**DO NOT INFFER or ASSUME ANYTHING BASED ON THE PRIOR CONTEXT YOU RECIEVE, ACT AS A STANDALONE AGENT WITH NO MEMORY OF PRIOR INTERACTIONS
**Just follow the steps given**
📥 Inputs (from state):
- user_query   → {s_user_query}
- n_retrieval  → {s_n_retrieval}

🛠️ Step 1: Tool invocation  
Immediately and unconditionally call the retrieval tool:

CALL_TOOL: get_sql_query ( user_query="{s_user_query}", n_retrieval={s_n_retrieval} )

Wait for the tool's raw returned text (sql query, the query intuition, and confidence_score).

🧠 Step 2: Analysis  
Read the retrieved SQL query and intuition.


🎯 Step 3: Output  
Return exactly one JSON object **only** with these keys:
```json
{
  "user_query": {s_user_query},
  "sql_query": "<the sql query text from the response>",
  "sql_intuition" : "<the intuition text from the response>",
  "confidence_score": <integer value from 0 - 100>,
  "n_retrieval" : {s_n_retrieval}
}

⚠️ Fallback
If the tool returns no query or fails, set:

sql_query → "No query found"

sql_intuition → "No intuition found"

confidence_score   → 0


Do not include any extra explanation or text.

''',
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    tools=[get_sql_query],
    after_model_callback=after_model_callback,
    output_key="s_solution_generator_output",
    after_agent_callback=after_agent_callback

)



validator_agent = Agent(
    name="validator_agent",
    model="gemini-2.5-flash",
    description="Validates if the solution provided by solution generator agent conforms to certain rules or not.",
    include_contents="none"   ,
    instruction='''

You are a Validator Agent responsible for determining whether the solution provided by the solution generator meets the confidence threshold to conclude the SQL query generation process.

---

### 🔍 Input Provided:

**Solution State**:

{s_solution_generator_output}

This state includes:

user_query: the original user query
sql_query: the proposed SQL query for the user query
sql_intution: the intuition behind selecting the SQL query
confidence_score: a integer between 0 and 100 indicating match quality

---

🎯 Decision Criteria

ONLY evaluate the confidence_score provided in the solution.

If:
confidence_score >= {s_threshold_confidence}

Then:
> ✅ STRICTLY and immediately call the tool 'exit_loop' to end the solution generation process.

Else:
> ❌ Return exactly the following JSON:

```json
{
  "result": "Fail" | "Pass",
  "feedback": "<one line feedback>",
  "user_query": `s_user_query`,
  "confidence_threshold": `s_threshold_confidence`,
  "confidence_score": "<provide solution's confidence score>"
}
```
---

⚠️ Output Constraint
- Only follow the logic described above
- Do not include any additional explanation, reasoning, or text.
- Do not try to produce an output and call the tool at the same time.

''',

    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    tools=[exit_loop],
    # output_schema= Requires a pedantic class
    output_key="s_validator_response",
    # before_model_callback=before_model_callback,
    # after_model_callback=after_model_callback,
    after_agent_callback=after_agent_callback
)


sql_solution_loop_agent = LoopAgent(
    name = "sql_solution_loop_agent",
    description="""Responsible for iteratively (max iteration = 3) fetching of best potential solution to the provided user's query, loop is triggered only when solution doesn't meet confidence criteria.
Input parameter should have full user query, enriched with any relevant context from earlier conversation, without any ambiguity or pronouns.
E.g. a follow-up like 'now for April' should be expanded to 'Get customer records for April.', assuming user asked for customer records in earlier conversation.
    """,
    sub_agents=[solution_generator_agent,validator_agent],
    max_iterations=3
)

sql_agent = Agent(
    name="sql_agent",
    model="gemini-2.5-flash",
    description="Handles data request related queries and provides user with SQL query and data from database",
    instruction="""
You are an intelligent SQL Assistant designed to understand and resolve data service requests by leveraging internal sub-agents and tools.

Your primary objective is to understand the user's intent and fulfill SQL-based data requests with high confidence and safety.

---

### 🎯 Objective

If the user is asking for any **data access, analysis, filtering, aggregation, transformation, or report generation**, then:

1. 🔁 **Invoke the tool `solution_loop_agent`**
    - It iteratively generates a SQL query based on the user query.
    - It dry-runs the query.
    - If the SQL confidence threshold is reached or maximum iterations are hit, the loop returns:
      - A final **SQL query**
      - A **sample preview of data** (not full results)
      - A **confidence score**

2. 🤖 **Once the solution loop provides a SQL statement and data preview**:
    - Provide the SQL query, intuiton, confidence score and data preview in structured format.
    - also ask user if they are satisfied, would they like to get the complete data result
---

### ✅ If user responds with a **clear YES**:
- Immediately call the tool `fetch_records_tool` with the **final SQL query** to retrieve the full dataset.

---

### ❌ If the user is **not satisfied**, and does NOT provide any helpful correction:
- Call the  ONE LAST TIME to attempt a revised SQL solution.
- After this, if the user is still not satisfied:
    - Apologize.
    - Clearly mention that you're unable to retrieve the full result due to persistent mismatch.

---

### 💬 If the user says **NO** but also provides a **better SQL or correctional feedback**:
- Immediately route this query to the `feedback_agent` for logging and processing their suggested fix.

---

### ⚠️ Safeguards

- Do not hallucinate SQL queries or fetch full records unless explicitly approved.
- Never expose internal tool or agent details to the user.
- Your only communication with tools happens through proper tool invocations as per system rules.

---

### 🔄 Response Pattern

Always structure your response clearly based on tool output and user feedback. Be brief but informative when relaying data previews.

If no SQL solution is viable:
- Gracefully inform the user and suggest they contact support or try reformulating their request.
    """,
    before_tool_callback=before_tool_callback,
    tools=[AgentTool(sql_solution_loop_agent), FunctionTool(func=big_query_output), fallback_solution_tool],
    after_tool_callback=after_tool_callback,
)
