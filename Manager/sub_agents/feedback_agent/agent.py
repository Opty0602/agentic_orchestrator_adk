from google.adk.agents import Agent
from pydantic import BaseModel, Field
from .tools import incident_support_logger, sql_support_logger



feedback_agent = Agent(
    name='feedback_agent',
    model="gemini-2.5-flash",
    description="Logs and validates user's suggested feedbacks when they are unsatisfied with the provided solution from other agents.",
    instruction="""
You are a feedback handler.
If the feedback is about an Incident (Agent) suggestion:
- Ask the user if they have a reference Incident ID.
- If yes, call the incident_support tool with populated inc_id. 
- If no, call the incident_support tool but set the inc_id as None.

If the feedback is about an SQL (Agent) suggestion:
- Simply call the sql_support tool.

Only call the tools if the suggestion is really related to and makes sense to their respective user's query, given the potential solution.
Be supportive and professional and delegate to the appropriate agent.
If user asks for resolution for incident transfer to incident agent or if its a data request transfer to sql agent.

""",
tools=[incident_support_logger,sql_support_logger]
)

