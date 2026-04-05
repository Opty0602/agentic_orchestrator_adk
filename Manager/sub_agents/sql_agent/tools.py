from google.adk.tools import ToolContext
from .sql_gen import text_to_sql
from google.cloud import bigquery as bq
import pandas as pd
import os


APP_NAME = "TEST_APP"
SESSION_ID = "123321"
USER_ID = "TEST_USER"
PROJECT_ID= os.environ.get("DATABASE_ID")


async def dry_run_check(query:str)->bool:
    """Validates and return the result for the SQL statement.
     Returns Boolean  """
    dataset = PROJECT_ID
    client = bq.Client()
    query = query.replace("`","").replace("sql","")
    try:
        job_config = bq.QueryJobConfig()
        if dataset:
            job_config.dry_run=True
            job_config.use_query_cache=False
            job_config.default_dataset = dataset
        query_job = client.query(query, job_config=job_config)
 
        return True
    except Exception as e:
        print("error : ", e)
        return False
    
async def preview_big_query_output(query:str)->str:
    """Validates and return the result for the SQL statement. """
    dataset = PROJECT_ID
    client = bq.Client()
    query = query.replace("`","").replace("sql","")
    
    try:
        job_config = bq.QueryJobConfig()
        if dataset:
            job_config.use_query_cache=True
            job_config.default_dataset = dataset
        query_job = client.query(query, job_config=job_config)
        result = query_job.result()
        df = result.to_dataframe().head(5) # limiting the response to 5
        if df.empty:
            return "Query returned empty result set from the database."
        return df.to_markdown()
    except Exception as e:
        print("error : ", e)
        return "Preview data cannot be shown at moment, please try again later."

async def big_query_output(query:str,tool_context:ToolContext)->dict:
    """Returns the Database result for the SQL statement provided.
**Note** - Invoke tool only if potential solution if given to the user

Input:
- query : str -> Big Query statement
- dataset: str -> Location of the residing database in cloud (default: PROJECT_ID)

Returns:
- Tool status
- Fetched Results, if successfull data will be displayed to the user directly.
    """

    dataset = PROJECT_ID
    client = bq.Client()
    query = query.replace("`","").replace("sql","")
    try:
        job_config = bq.QueryJobConfig()
        if dataset:
            job_config.use_query_cache=True
            job_config.default_dataset = dataset
        query_job = client.query(query, job_config=job_config)
        result = query_job.result()
        df = result.to_dataframe() 
        if df.empty:
            return {"tool_status":"pass","result":"Query returned empty result set from the datastore."}
        tool_context.state["s_retreived_data"]= df.to_markdown()
        return {"tool_status":"pass","result":"Data is being displayed on the screen."}
    except Exception as e:
        print("error : ", e)
        return {"tool_status":"fail","result":f"There was some error {e}"}
    
#Get relevant document from the vector store
async def get_sql_query(user_query:str, n_retrieval:int)-> dict:
    '''Fetches the SQL query and the intuition behind the query based on the user's query. '''
    dry_run_result = False
    try:
        sql_query, intuition = await text_to_sql(user_query, n_retrieval or 3)
        dry_run_result = await dry_run_check(sql_query)
 
        if dry_run_result:
            
            return {"tool_status":"pass","user_query":user_query,"sql_query":sql_query, "query_intuition and confidence":intuition}
        return {"tool_status":"fail","message":"The generated query didnt pass dry run check."}
    
    except Exception as e: 
        print("ERROR:\n", {e})
        return {"tool_status": "fail",
                "error_mesage": f"there was some error fetching the data. ERROR: {e}"}
    
async def fallback_solution_tool(user_query:str)-> dict:
    '''Fallback tool to retrieve solution with wider search area for one last time
    Input:
    user_query (str): Complete user query for data request.

    Returns:
    SQL Statement, Intuiton, Confidence Score and data preview
    '''
    
    try:
        sql_query, intuition =  await text_to_sql(user_query, n_results=9)
        dry_run_result = await dry_run_check(sql_query)
        if dry_run_result:
            return {"tool_status":"pass","user_query":user_query,"sql_query":sql_query, "query_intuition":intuition}
        return {"tool_status":"fail","message":"The generated query didnt pass dry run check."}
    
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
    tool_context.state["s_dryrun_validated"] = True

    tool_context.state['s_threshold_confidence'] = 3
    tool_context.actions.escalate = True

    return {}
