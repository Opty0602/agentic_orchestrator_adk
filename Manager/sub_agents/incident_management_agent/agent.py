from google.adk.agents import Agent, SequentialAgent, ParallelAgent, LoopAgent
from google.adk.tools.agent_tool import AgentTool
from pydantic import BaseModel, Field
import sys
from google.adk.utils import instructions_utils
sys.path.append('SharedResources')

async def xyz(contenxt) -> str:
    return await instructions_utils.inject_session_state("my name is {name}")



from .tools import get_historical_incident,exit_loop
from .callbacks import *
from .prompt import *
APP_NAME = "TEST_APP"
SESSION_ID = "123321"
USER_ID = "TEST_USER"

class OutputSchemaForIntentParser(BaseModel):
    needed_email: bool = Field(
        description="Flags if email is requested or not"
    )
    needed_knowledge:bool =Field(
        description="Flags if knowledge article is requested or not "
    )
    needed_summary:bool = Field(
        description="Flag if summary is requested."
    )




initial_session_state ={
        "user_query": None,
        "potential_solution":None,
        "n_retrieval": 3,
        "threshold_confidence": 80,
        "needed_email":False,
        "needed_knowledge": False,
        "needed_summary":False,
        "drafted_mail": None,
        "knowledge_article":None,
        "summary":None,

    
}

fallback_solution_agent = Agent(
    name="fallback_solution_agent",
    model="gemini-2.5-flash",
    description="Call this tool as a final fallback attempt to get user desired solution one last time.",
    include_contents="none",
instruction = '''

You are the fallback solution getter. You are called only when user was unsatified with the previous results.

Your job is to propose a remedy to the current incident query.

📥 Inputs (from state):
- user_query   → {user_query}

🛠️ Step 1: Tool invocation  
Immediately and unconditionally call the retrieval tool:

CALL_TOOL get_historical_incident( incident_query="{user_query}", n_retrieval= 10 )

Wait for the tool's raw returned text (list of incidents with their remedies).

🧠 Step 2: Analysis  
Read the retrieved incidents. Choose the single most semantically relevant incident.

🎯 Step 3: Output  
Return exactly one JSON object **only** with these keys:
```json
{
  "user_incident": {user_query},
  "potential_solution": "<the remedy text from your chosen incident's remedy>",
  "confidence_score": <integer between 0 and 100>,
}

⚠️ Fallback
If the tool returns no incidents or fails, set:

potential_solution → "No solution found"

confidence_score   → 0


Do not include any extra explanation or text.

''',
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    tools=[get_historical_incident],

    output_key="i_fallback_output"

)

solution_generator_agent = Agent(
    name="solution_generator_agent",
    model="gemini-2.5-flash",
    include_contents="none",
instruction = SOLUTION_GENERATOR_PROMPT_v1, 

    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    tools=[

        get_historical_incident 
    ],
    output_key="i_solution_generator_output"

    
)



validator_agent = Agent(
    name="validator_agent",
    model="gemini-2.0-flash",
    include_contents="none",
    instruction='''

You are a Validator Agent responsible for determining whether the solution provided by the solution generator meets the confidence threshold to conclude the incident resolution process.

---

### 🔍 Input Provided:

**Solution State**:

{i_solution_generator_output}

This state includes:

user_ the original user query
potential_solution: the proposed remedy
confidence_score: a float between 0 and 100 indicating match quality

---


🎯 Decision Criteria

ONLY evaluate the confidence_score provided in the solution.

If:
confidence_score >= {threshold_confidence}

Then:
> ✅ STRICTLY and immediately call the tool 'exit_loop' to end the solution generation process.

Else:
> ❌ Return exactly the following JSON:

```json
{
  "result": "Fail",
  "feedback": "<one line feedback>",
  "user_query": {user_query},
  "confidence_threshold": {threshold_confidence},
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
    tools=[exit_loop],output_key="validator_response",
    after_agent_callback=after_agent_callback

    
)

solution_loop_agent = LoopAgent(
    
    name = "solution_loop_agent",
    description="Responsible for iteratively (max iteration = 3) fetching of best potential solution to the provided user's query, loop is triggered  only when solution doesn't meet confidence criteria.",
    sub_agents=[solution_generator_agent,validator_agent],
    max_iterations=3
)

     

knowledge_article_agent = Agent(
    name = "knowledge_article_agent",
    description= "Curates a knowledge Artcile, based on the provided solution",
    model= "gemini-2.5-flash",
    before_agent_callback=skip_call_before_agent_callback,
    before_model_callback=before_model_callback,
    include_contents="none",
    instruction=KB_GENERATOR_AGENTv1,
    output_key="knowledge_article",

)

mail_generator_agent = Agent(
    name = "mail_generator_agent",
    description= "Drafts a mail w.r.t given incident and solution (if given)",
    model= "gemini-2.5-flash",
    before_agent_callback=skip_call_before_agent_callback,
    before_model_callback=before_model_callback,
    include_contents="none",    
    instruction=EMAIL_GENERATOR_AGENTv1,

    output_key="drafted_mail",

)
summary_generator_agent = Agent(
    name = "summary_generator_agent",
    description= "generates the summary of the incident and the provided solution",
    model= "gemini-2.5-flash",
    before_agent_callback=skip_call_before_agent_callback,
    before_model_callback=before_model_callback,
    include_contents="none",
    instruction='''
You are summary generator agent, working in parallel with knowledge artcile generator agent and mail drafter agent, recieving the same input as yours.
Your task is **JUST** to provide a bit elongated summary based on the incident and solution.
Ignore if user asks for other things.

Below is the new user query describing their problem,

User Query : {user_query}

And below is the resolution from a previously resolved similar incident,

Resolution : {potential_solution}

Your task is to,
1. Focus **only on generating a helpful solution** for current user query.
2. Use incident resolution as a refrence but tailor response to user query.
3. do **not** generate email or article - focus only on summarization.
4. If resolution is not relevant, return 'Unable to resolve, Please raise ServiceNow request'

Return output in format:
<your answer here>
''',

    output_key="summary",

)

intent_agent = Agent(
     name= "intent_agent",
     model="gemini-2.0-flash",
     disallow_transfer_to_parent=True,
     disallow_transfer_to_peers=True,
     after_agent_callback=intent_after_agent_callback,
     output_schema=OutputSchemaForIntentParser,
     instruction="""
You are simple intent parser. Your task is to simply know what user is asking.
Does he need mail generation, knowledge article generation, summary or all of it.


Based on the input simply output **JUST** the JSON:
```json
{
"needed_email": True | False ,
"needed_knowledge" : True | False ,
"needed_summary" : True | False
}
```
All of the above fields are flags with boolean values.
""",
output_key="parsed_intent",

)

parallel_agent = ParallelAgent(
    name = 'msk_agent',
    before_agent_callback=before_agent_callback,
    description= "Agent is capable enough to parse user's query and generate mail, knowledge article, summary or all at once.",
    sub_agents=[knowledge_article_agent, mail_generator_agent, summary_generator_agent],
)

sequence_agent = SequentialAgent(
    name = "mail_knowledge_summary_agent",
    sub_agents=[intent_agent,parallel_agent],
    description="Specializes in drafting mail, knowledge Article and summarizing "

)

INCIDENT_MANAGEMENT_v2 = """You are an Incident Management Agent responsible for handling user-reported issues and coordinating with sibling agents and tools. You must behave deterministically, track conversation context, and route tasks correctly.

Your responsibilities:

1. Detect whether the user message is:
   - A NEW incident description.
   - A FOLLOW-UP clarification to an earlier incident (often short, incomplete clauses that modify or correct the earlier incident).
   - A SATISFACTION response to a solution.
   - A SUGGESTION or critique.
   - A non-incident message.

2. If the user provides a NEW INCIDENT:
   - Immediately call the tool `solution_loop_agent` with the complete incident context.

3. When `solution_loop_agent` returns a valid solution:
   - Present the solution AND confidence score to the user.
   - Ask if they are satisfied.

4. When the user responds after a solution:
   
   A. If the response is a clear **YES**:
      - Tell them they may choose to generate: a mail, a KB article, a summary, or all of them or want solution for differrent issue.
      - These tools must ONLY be offered if both `user_incident` AND `solution` are presented to the user for the given query.
      - After they choose, call the corresponding tool.

   B. If the response is a **NO**, followed by the user giving additional details, corrections, or new information about the incident:
      - Treat this as a FOLLOW-UP CLARIFICATION.
      - Reconstruct the full updated incident using earlier context + the new information.
      - Call `solution_loop_agent` again with this updated incident.
      - Present the new solution and once again ask if they are satisfied.
      - If the user STILL says NO after this second attempt:
        - Route to `feedback_agent` and provide full context.

   C. If the response is a **NO** without clarification:
      - Call the fallback tool for a final attempt.
      - Present the fallback’s answer and acknowledge the dissatisfaction.
      - If the user is still not satisfied:
        - Route the case to `feedback_agent` with all context.

   D. If the user provides a suggestion instead of a clear NO:
      - Route directly to `feedback_agent`.

5. If the message is a FOLLOW-UP CLARIFICATION but the user has not yet received a solution:
   - Treat it as part of the initial incident.
   - Call `solution_loop_agent`.

6. If the message is NOT an incident or problem:
   - Do NOT call `solution_loop_agent`.
   - Do NOT offer mail, summary, or KB generation.
   - Politely ask the user to clarify whether they are reporting an incident or need help with something else.
   - Ask clearifying quetion if user's inputs are unclear.

7. Constraints:
   - Never offer follow-up generators unless BOTH `user_incident` and `solution` exist.
   - On any unresolved dissatisfaction, always route to `feedback_agent`.
   - Keep the flow conversational, context-aware, and safe.
   - Never hallucinate tools or skip required steps.
   - Always pass correct context during handoffs.

Your goal is to keep the interaction smooth, correct, and deterministic.
"""



incident_management_agent = Agent(
     
    name="incident_management_agent",
    model="gemini-2.5-flash",
    description="Provides incident's solution based on historical data related to the query belong to banking domain related to online banking and related services. Also, returns summary, mail and Knowledge article based on user's incident",
    instruction=INCIDENT_MANAGEMENT_v2,
    #
    
    sub_agents=[sequence_agent],
    before_tool_callback=before_tool_callback,
    tools = [
        AgentTool(solution_loop_agent),AgentTool(agent= fallback_solution_agent)
    ],
    after_tool_callback= after_tool_callback,

)
