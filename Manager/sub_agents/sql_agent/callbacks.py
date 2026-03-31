
from google.adk.tools.tool_context import ToolContext

from google.adk.tools.base_tool import BaseTool
from google.genai import types
from google.adk.agents.callback_context import CallbackContext
from google.adk.sessions import InMemorySessionService
from .tools import preview_big_query_output
from typing import Optional, Dict, Any



APP_NAME = "TEST_APP"
SESSION_ID = "123321"
USER_ID = "TEST_USER"



async def session_create(session_service: InMemorySessionService, app_name,user_id, session_id, state):
        await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state = state)
        return 

def before_tool_callback(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict]:
    
    print(f"\n--------before tool Callback START. Agent Name = {tool_context.agent_name}------")
    # print(tool_context.state, tool)
    if tool.name.lower() == "sql_solution_loop_agent":
        
        user_query = args.get("request", None)
        tool_context.state['s_user_query'] = user_query

        print("REQUEST",user_query, "STATE",tool_context.state.to_dict(), 'TOOL NAME', tool.name)


    print(f"\n--------tool Callback END. Agent Name = {tool_context.agent_name}------")

    return None
    
async def after_tool_callback(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Dict
) -> Optional[Dict]:
    
    print(f"[After_tool_callback] triggered by {tool_context.agent_name}")
    if tool.name.lower() == "sql_solution_loop_agent":
        
        solution_generator_output = tool_context.state["s_solution_generator_output"]
        data_preview_result = "Data preview is currently not available."
        try:
            solution_generator_output = eval(solution_generator_output.replace("```json","").replace("```",""))
            tool_context.state["s_generated_sql"] = solution_generator_output['sql_query']
            tool_context.state["s_generated_intuition"] = solution_generator_output['sql_intuition']
            print("Solution_generator_output: ", solution_generator_output, type(solution_generator_output))
            if isinstance(solution_generator_output,dict) and solution_generator_output["sql_query"] != "" and tool_context.state['s_dryrun_validated']:
                print("dryrun validated")
                data_preview_result= await preview_big_query_output(query=solution_generator_output["sql_query"])

                #previewing the data on the right window
                tool_context.state["s_retreived_data"]= data_preview_result
            
        except Exception as e:
            print(f"Fetching the preview was not succesfful. ERROR: {e}")
            
        return {"result":{"potential_sql_solution": solution_generator_output, "data_preview":"Data preview must be visible to on the screen now."}}
    
    if tool.name.lower() == "big_query_output":

        final_data = tool_response.get("result","Data cannot be displayed.")
        tool_context.actions.skip_summarization=False

        return {"result": final_data}

    return None
    
async def after_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    print(f"\n--------After agent Callback. Agent Name =  {callback_context.agent_name}------")
    if callback_context.agent_name=="validator_agent":
        try:
            validator_response = str(callback_context.state.get('s_validator_response','{"result":"pass"}'))
            validator_response = eval(validator_response.replace("```json","").replace("```",""))
        except Exception as e:
            print("there was some error in evaluating validator's response.", e)
        try:
            print("Validator Response: ", validator_response, type(validator_response))
            if isinstance(validator_response,dict) and validator_response['result'].lower() == "fail":
                callback_context.state['s_n_retrieval'] += 1 
                print(f"Search parameter increased by 1 CURRENT={callback_context.state['s_n_retrieval']}")
            else:
                print(f"validator_response : {validator_response}")
        except Exception as e:
            print("there was error in increasing search criteria", e)
    # print(callback_context.state.to_dict())
    return None

from google.adk.models import LlmRequest, LlmResponse
from google.genai import types
async def before_model_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmRequest]:
    print(f"\n--------before model Callback. Agent Name =  {callback_context.agent_name}------")
    # print(f"{callback_context.agent_name} INPUT", llm_request.config.system_instruction)
    print("user_content: ", callback_context.user_content)
    if len(llm_request.contents)>=2:
        for content in llm_request.contents:
            if content.parts[0].function_response:
                llm_request.contents.append(types.Content(parts=[types.Part(text="Proceed with the given task")],
                                              role='user'))
    print(llm_request.contents)

    

def after_model_callback(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
    print(f"\n--------After model Callback. Agent Name =  {callback_context.agent_name}------")
    print(f"{callback_context.agent_name} OUTPUT", llm_response.content)
    return None