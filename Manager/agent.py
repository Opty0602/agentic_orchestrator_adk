from google.adk.agents import Agent
import sys
from google.adk.sessions import InMemorySessionService
from .sub_agents.incident_management_agent.agent import incident_management_agent
from .sub_agents.sql_agent.agent import sql_agent
from .sub_agents.feedback_agent.agent import feedback_agent

sys.path.append('SharedResources')


async def create_session(app_name,user_id, session_id, state,session_service = InMemorySessionService()):
        session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state = state)
        return session


root_agent = Agent(
    name="Manager",
    model="gemini-2.5-flash",
    description="Manager agent",
    instruction="""
You are a manager agent that is responsible for overseeing the work of the other agents.

Always delegate the task to the appropriate agent. Use your best judgement 
to determine which agent to delegate to and whats the user intention is.

You are responsible for delegating tasks to the following agent:
- incident_management_agent
- sql_agent


Be helpfull, smarlty delegate work, structure you responses and if uncertain ask clearly.
    """,
    
    sub_agents=[
        incident_management_agent,
                sql_agent,feedback_agent,
          
                ],
)