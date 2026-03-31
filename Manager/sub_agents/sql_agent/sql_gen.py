import os
from SharedResources.load_environment import get_client
import chromadb
from google.genai.types import EmbedContentConfig
from google.genai.types import GenerateContentConfig

import re

#Gemini client setup

client = get_client()

def smallm_query_preparer(retreiver_result):
    """ Prepares the prompt to be fed to smallm """

    query = ""
    for i, table_name in enumerate(retreiver_result['ids'][0]):
        name = "Table name: "+table_name
        description = retreiver_result['documents'][0][i]
        query = query + name + '\n' + description + '\n'
    return query
    

old_pruner_prompt = '''
You are expert SQL assistant. Analyze the user_query to understand its intent and the information it seeks.
Identify the primary tables and foreign key relationships connected to the primary table(s) involved in query.

For each table, Give only the relevant columns as a comma-seperated list as result, not queries.
---
Example response if provided schema and description fullfills user's query:

Table Name: [table_name]
Important Columns: column1 data_type, column2 data_type, ...
Table's Description: Very concise description of returned columns.

Table Name: [table_name]
Important Columns: column1 data_type, column2 data_type, ...
Table's Description:....
        
Reasoning: <brief reason why you chose these table(s) and column(s) based on info you have>
---
**NOTE**
else If provided schema and description doesn't fullfill user's query, just RETURN 

"Table Name: None Reasoning: Not enough information provided.".
---
'''


def prune_schema(user_input, retrieval_response):
    """ Returns the Pruned the schemas as per the User's query intent and breif description for why so """

    prompt = f'''
    user's query : {user_input}
    And following table schemas and decription : {retrieval_response}
    '''   
    response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=GenerateContentConfig(temperature=0.2,top_k=1,top_p=0.9,
        system_instruction = [old_pruner_prompt]
        )
    )
    
    match = re.split(r'\breasoning\s*:\s*',response.text, maxsplit=1, flags=re.IGNORECASE)
    before = match[0].strip()
    after = match[1].strip() if len(match) > 1 else ""
    return before, after

generator_prompt = '''
You are an expert BigQuery assistant. Generate a valid BigQuery SQL query based on the user's intent using ONLY the provided table(s) and their columns. Use proper and idiomatic BigQuery syntax. Use JOINs where needed.
If the provided table/column information is insufficient/irrelevant to construct a meaningful query fullfilling user's query, *respond with: "Requested information is either not relevant or not enough information is present."*
*NOTE* - Don't use any markdown symbols.

Remember:
1. Use relevant alias nomenclature and underscores where appropriate (especially with aggregates like COUNT, SUM, MAX).
2. STRICTLY use LOWER() for case-insensitive comparisons of STRING fields.
3. For filtering dates or timestamps by year or month or etc, prefer using EXTRACT(YEAR FROM ...) or DATE_TRUNC(..., MONTH) over string manipulation or casting.
4. Avoid casting DATE or TIMESTAMP fields to STRING for filtering unless absolutely necessary.
5. TIMESTAMP_SUB and TIMESTAMP_ADD support only limited intervals — avoid using MONTH or YEAR with TIMESTAMP directly.


'''

def generate_sql_query(query, pruned_schema):
    """Returns the SQL statement after analysing the user's intent and retirevd information. """
    prompt = f""" 
    User query : {query}
    Relevant table and columns : {pruned_schema}
    """
    response = client.models.generate_content(
    model="gemini-2.5-flash",

    contents=prompt,
    config=GenerateContentConfig(temperature=0.1,top_k=1,top_p=0.95,
                                 system_instruction = [generator_prompt]
                                )
    )
    return response.text
    
def intuiton_score_analysis(user_query, pruner_reasoning, sql_statement):
    sql_statement = sql_statement.replace("`","").replace("sql","")
    prompt=f'''
    Query:{user_query}
    Retriever's Reasoning:{pruner_reasoning}
    BigQuery Statement:{sql_statement}
    
    '''
    response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=GenerateContentConfig(temperature=0.2,top_p=0.95,
                                 system_instruction = [
                                     '''
                                     You are a BigQuery Statement Analyst.

Your task is to:
1. Generate a **clear, point-wise explanation** of how the given BigQuery SQL statement addresses the User's natural language request.
2. Assign a **Confidence Score** (0–100) reflecting how well the SQL statement and the Retriever's Reasoning together fulfill the User's request.
3. Assume absolutely nothing beyond the provided instructions and inputs.

### Explanation Guidelines:
- Focus on *why* specific tables, columns, filters, and joins were chosen.
- Describe how the SQL's structure, aggregations, and conditions map to the intent of the user's request.
- Call out any logical assumptions made by the retriever when constructing the SQL.
- If something in the SQL is unrelated to the user’s request, explicitly mention it.

### Confidence Score Guidelines:
- The score must reflect **the combined alignment** of:
  - The User’s request
  - The Generated SQL statement
  - The Retriever’s Reasoning
- Check that the SQL directly answers the request, along with the Retriever’s Reasoning correctly explains the SQL’s logic.
- If the SQL is relevant but the Retriever's Reasoning shows misunderstanding/contradiction, set **confidence_score = 0**.

- 100 = perfectly aligned request, SQL, and reasoning; 
- 0 = completely unrelated or reasoning contradicts the SQL/query intent.

### Output Format (JSON only):

{
  "intuition": "<Point-wise explanation here in markdown format>",
  "confidence_score": <integer from 0 to 100>
}

### Inputs Provided:
- User's natural language question
- Generated BigQuery SQL statement
- Retriever's Reasoning (from schema retriever)
''']
                                
                                )
    )
    return response.text


visual_explainer_prompt = """
You are a SQL query explainer that transforms SQL queries into clean, well-structured textual flowcharts. 

Given a user's intent, the SQL query, and optionally a summary of the SQL's logic.
This flowchart should include:
- The involved tables with their aliases and key columns used
- Join relationships and their conditions
- Filters applied (WHERE clauses)
- Aggregations or groupings
- Final selected fields
- The order of execution as a top-down logical flow
- All elements should be presented as clearly separated box-like structures connected by arrows, mimicking data flow.

The output must be a flow chart in **plain text or Markdown** ONLY.
Readable by technical and non-technical users alike. Avoid SQL syntax and focus on explaining the structure and reasoning. 
If joins are used, show the contributing tables side-by-side and join flow into a new node.
Highlight why each table or filter is used if derivable from the SQL.

If the input is ambiguous or insufficient, respond with "More information needed"

example output:
```
+---------------------+     +---------------------+     +--------------------------+
|   Customer (t1)     |     |   Proposal (t2)     |     | FinancialAdvisor (t3)    |
|---------------------+     |---------------------+     |--------------------------|
| customer_id         |---->| customer_id         |---->| advisor_id               |
| risk_profile        |     | advisor_id          |     | name                     |
+---------------------+     +---------------------+     +--------------------------+
      |                         |
      |  (Join on customer_id)  |
      |                         |
      V                         V
+-----------------------------------------------------+
|                                                     |
|           Join Customer (t1) and Proposal (t2)      |
|                                                     |
+-----------------------------------------------------+
      |
      |  (Filter: risk_profile = 'aggressive')
      |
      V
+-----------------------------------------------------+
|                                                     |
|        Filter Customers with 'aggressive' risk      |
|                                                     |
+-----------------------------------------------------+
      |
      |  (Join on advisor_id)
      |
      V
+-----------------------------------------------------+
|                                                     |
|   Join with FinancialAdvisor (t3) on advisor_id     |
|                                                     |
+-----------------------------------------------------+
      |
      V
+---------------------+
|   Final Output:     |
|  FinancialAdvisor   |
|       name          |
+---------------------+
```
"""

def visual_explainer(user_query, sql_statement):
    """Returns a visual-intuitive textual Flowchart for the Query Logic Used. """
    sql_statement = sql_statement.replace("`","").replace("sql","")
    prompt=f'''
    Query:{user_query}
    BigQuery Statement:{sql_statement}

    ABSOLUTELY ENSURE THAT YOUR RESPONSE IS PROPERLY ALIGNED i.e. boxes,names and arrows should not fall out of places.
    Get me JUST the textual flowchart for this and nothing else.
    '''
    response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=GenerateContentConfig(temperature=0.2,top_p=0.95,max_output_tokens = 2048,
                                 system_instruction = [visual_explainer_prompt]
                                )
    )
    return response.text



async def text_to_sql(user_input:str,n_results:int = 3):
    """Orchestrates the SQL pipeline. Returns the final SQL statement based on User's Query and Summarised Intuiton for it. """
   
    
    chroma_client = chromadb.PersistentClient(path = "./Manager/sub_agents/sql_agent/chromadb") # establishing chromaDB client
    collection = chroma_client.get_collection(name="SQL_MetaStore") # getting the vector collection
    
    response = client.models.embed_content(
    model="text-embedding-005",
    contents=user_input,
    config=EmbedContentConfig(
        task_type="RETRIEVAL_DOCUMENT"
    ),).embeddings[0].values

    # embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-005")
    similar_tables = collection.query(query_embeddings = response, n_results = n_results)
    similar_tables_schema = smallm_query_preparer(similar_tables)
    relevant_cols, prune_summary = prune_schema(user_input, similar_tables_schema)
    result = generate_sql_query(user_input, relevant_cols)
    
    intuition = intuiton_score_analysis(user_input, prune_summary, result)
    # intuition = intuition.replace("`", "").replace("Intuition","").replace(":","")
    print("ACTUAL SQL GENERATOR WORKING")
    return result, intuition
    
    
        
    
    