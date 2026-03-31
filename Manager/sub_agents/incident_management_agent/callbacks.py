from google.adk.models import LlmRequest, LlmResponse
from google.adk.agents import Agent, SequentialAgent, ParallelAgent, LoopAgent
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.base_tool import BaseTool
from google.genai import types
from google.adk.agents.callback_context import CallbackContext

from typing import Optional, Dict, Any
APP_NAME = "TEST_APP"
SESSION_ID = "123321"
USER_ID = "TEST_USER"


def before_model_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    
    # if callback_context.agent_name == "solution_generator" and llm_request.contents[-1].parts[]
    print(f"\n--------before model Callback START. Agent Name = {callback_context.agent_name}------")
    if callback_context.agent_name == "solution_generator_agent":
            print(f"\n🧠 [DEBUG] LLM Request for agent: {callback_context.agent_name}")
            print(llm_request.config.system_instruction)
            # # System instructions are usually embedded as the first system message
            # system_messages = [
            #     msg for msg in llm_request.contents
            #     if isinstance(msg, types.Content) and msg.role == "system"
            # ]

            # if system_messages:
            #     print("\n📜 System Instructions:")
            #     for part in system_messages[0].parts:
            #         print("  •", part.text if hasattr(part, "text") else part)

            # print("\n💬 Other Messages:")
            # for msg in llm_request.contents:
    
            #     print(f"  [{msg.role.upper()}]")
            #     for part in msg.parts:
            #         print("   -", part.text if hasattr(part, "text") else part)

            # print("\n🔧 Function Call Hint:", )
    print(f"\n--------Callback END. Agent Name = {callback_context.agent_name}------")
    return None



async def before_tool_callback(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict]:
    
    print(f"\n--------before tool Callback START. Agent Name = {tool_context.agent_name}------")
    # print(tool_context.state, tool)
    if tool.name.lower() == "solution_loop_agent":
        
        user_query = args.get("request", None)
        tool_context.state['user_query'] = user_query

        ## Restting the state values
        tool_context.state["potential_solution"] = None
        tool_context.state["summary"] = None
        tool_context.state["knowledge_article"] = None
        tool_context.state["drafted_mail"] = None

        print("REQUEST",user_query, "STATE",tool_context.state.to_dict(), 'TOOL NAME', tool.name)


    print(f"\n--------tool Callback END. Agent Name = {tool_context.agent_name}------")

    return None



async def after_tool_callback(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Dict
) -> Optional[Dict]:
    
    print(f"[After_tool_callback] triggered by {tool_context.agent_name}")
    if tool.name.lower() == "solution_loop_agent":
        try:
            solution_generator_output = tool_context.state["i_solution_generator_output"]
            solution_generator_output = eval(str(solution_generator_output.replace("```json","").replace("```","")))
            tool_context.state["potential_solution"] = solution_generator_output['potential_solution']
            print("Solution_generator_output: ", solution_generator_output, type(solution_generator_output))
        except Exception as e:
            print(f"there was error in evaluationg state. ERROR: {e}")
            
        
        
                            
                        

        
        # InMemorySessionService().get_session(app_name=APP_NAME,user_id=USER_ID,session_id= SESSION_ID) #TODO 1 update session instead of creating new one.
        # await session_create(InMemorySessionService(),APP_NAME,USER_ID,SESSION_ID,updated_state)

        # print(f"Session {SESSION_ID} created for {USER_ID}")
        return {"result":{"best_similar_solution": solution_generator_output}}




async def after_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    
    
    print(f"\n--------After agent Callback. Agent Name =  {callback_context.agent_name}------")
    print(callback_context.state.to_dict())

    try:
        validator_response = callback_context.state.get('validator_response','{"result":"pass"}')
        validator_response = eval(validator_response.replace("```json","").replace("```",""))

        print("Validator Response: ", validator_response, type(validator_response))
        if isinstance(validator_response,dict) and validator_response['result'].lower() == "fail":
            callback_context.state['n_retrieval'] += 2 
            print(f"Search parameter increased by 2 CURRENT={callback_context.state['n_retrieval']}")
        else:
            print(f"validator_response : {validator_response}")
    except Exception as e:
         print("there was error in evaluationg state", e)
    return None



async def skip_call_before_agent_callback(callback_context: CallbackContext)->Optional[types.Content]:
    try:
        if callback_context.agent_name == "summary_generator_agent": 
            if not callback_context.state["parsed_intent"]["needed_summary"]:
                return types.Content(parts = [types.Part(text="---Summary skipped---")])


        if callback_context.agent_name == "knowledge_article_agent":
                if not callback_context.state["parsed_intent"]["needed_knowledge"]:
                    return types.Content(parts = [types.Part(text="---Article skipped---")])
        
        if callback_context.agent_name == "mail_generator_agent":
                if not callback_context.state["parsed_intent"]["needed_email"]:
                    return types.Content(parts = [types.Part(text="---mail skipped---")])
    except Exception as e:
         print("Problem in parallel agent call back: ", e)
        
    
    return None


def before_agent_callback(callback_context : CallbackContext) -> Optional[types.Content]:
    if callback_context.agent_name=="msk_agent":
        print(f"Request going to the parallel agent:- {callback_context.user_content}")
    return None


async def intent_after_agent_callback(callback_context: CallbackContext)-> Optional[types.Content]:
     
    try:
        # parsed_intent = callback_context.state.get("parsed_intent",{"needed_email": False ,"needed_knowledge" : False ,"needed_summary" : False})
        print(f"Parsed Intent: {callback_context.state['parsed_intent']}")
        # parsed_intent = eval(parsed_intent.replace("```json","").replace("```",""))
        # callback_context.state["parsed_intent"] = parsed_intent
    except Exception as e:
         print("There was some error parsing the intent", e)
    
    return None

from google.adk.models import LlmRequest, LlmResponse
from google.genai import types
async def before_model_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmRequest]:
    print(f"\n--------before model Callback. Agent Name =  {callback_context.agent_name}------")
    # print(f"{callback_context.agent_name} INPUT", llm_request.config.system_instruction)
    print("user_content: ", callback_context.user_content)
    # if len(llm_request.contents)>=2:
    #     for content in llm_request.contents:
    #         if content.parts[0].function_response:
    #             llm_request.contents.insert(0,types.Content(parts=[types.Part(text="Proceed with the given task")],
    #                                           role='user'))
    print(llm_request.contents)

    

async def after_model_callback(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
    print(f"\n--------After model Callback. Agent Name =  {callback_context.agent_name}------")
    print(f"{callback_context.agent_name} OUTPUT", llm_response.content)
    return None