#----------------------------
# PHASE 1: Importing Modules
#----------------------------
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from typing import TypedDict, List, Annotated, Any
from langgraph.runtime import Runtime
from langchain_core.runnables import RunnableConfig
from dataclasses import dataclass
from pathlib import Path
import asyncio, os, re, sys
from groq import RateLimitError

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
from config.logging_config import requirement_log

#-------------------------------------------------
# PHASE 2: LLM + Parsers + State + Runtime Context
#-------------------------------------------------
load_dotenv()
llm = ChatGroq(api_key=os.getenv("GROQ_API_KEY3"), model="openai/gpt-oss-120b", temperature=0.2)
parser = StrOutputParser()

class RequirementState(TypedDict):
    folder_name: str
    extension: List
    files: List
    contents: str
    requirements_content: str
    final_answer: str

@dataclass
class AppContext:
    config: dict
    session: Any
#--------------------------------
# PHASE 3: NODES
#--------------------------------
"""GET FILES NODE"""
async def get_files_node(state: RequirementState, runtime: Runtime[AppContext]) -> dict:
    """Get all files of specific folder"""
    try:
        requirement_log.info(f"START 'get_files_node'")
        base_path = Path(state['folder_name']).resolve()
        if base_path.is_file():
            requirement_log.info(f"Path '{state['folder_name']}' is file path")
            requirement_log.info(f"END 'get_files_node'")
            return {"files": [base_path], "folder_name": base_path.parent}
        requirement_log.info("Calling tool 'list_folder_contents'")
        result = await runtime.context.session.call_tool(name="list_folder_contents", arguments={"folder_name": state['folder_name'], "extension": state['extension']})
        requirement_log.info(f"Called tool result is: '{result}'")
        files = []
        for i in range(len(result.content)):
            files.append(result.content[i].text)
        requirement_log.info(f"Returning 'files'")
        requirement_log.info(f"END 'get_files_node'")
        return {"files": files}
    except Exception as e:
        requirement_log.exception(f"Error occurred during get files: '{str(e)}'")
        requirement_log.info(f"END 'get_files_node'")
        return {}

"""READ FILES NODE"""
async def read_files_node(state: RequirementState, runtime: Runtime[AppContext]) -> dict:
    """Read all files concurrently and extract ONLY import statements"""
    requirement_log.info(f"START 'read_files_node'")
    
    if not state.get('files'):
        requirement_log.info(f"No files found in 'state'")
        return {"contents": ""}
        
    import_pattern = re.compile(r'^\s*(?:import\s+.+|from\s+.+\s+import\s+.+)')
    async def fetch_and_extract_imports(file_path):
        try:
            requirement_log.info(f"Calling tool 'read_file'")
            result = await runtime.context.session.call_tool(
                name="read_file", 
                arguments={"file_path": file_path}
            )
            requirement_log.info(f"Called tool result is: '{result}'")
            if result and hasattr(result, 'content') and len(result.content) > 0:
                full_text = result.content[0].text
                file_imports = []
                
                for line in full_text.splitlines():
                    if import_pattern.match(line):
                        file_imports.append(line.strip())
                
                requirement_log.info(f"Returning file_imports")
                requirement_log.info(f"END 'read_files_node'")
                return "\n".join(file_imports)
            
            requirement_log.exception(f"Could not read content from '{file_path}'")
            requirement_log.info(f"END 'read_files_node'")
            return f"# [Error]: Could not read content from '{file_path}'"
        except Exception as e:
            requirement_log.exception(f"Failed to process '{file_path}' due to exception: '{str(e)}'")
            requirement_log.info(f"END 'read_files_node'")
            return {}

    tasks = [fetch_and_extract_imports(file) for file in state['files']]
    extracted_contents = await asyncio.gather(*tasks)
    
    final_contents = "\n\n".join(filter(None, extracted_contents))
    requirement_log.info(f"Returning 'final_contents'")
    requirement_log.info(f"END 'read_files_node'")
    return {"contents": final_contents}

"""GENERATE REQUIREMENTS NODE"""
async def generate_requirements_node(state: RequirementState, runtime: Runtime[AppContext]) -> dict:
    """Generate requirements"""
    try:
        requirement_log.info(f"START 'generate_requirements_node'")
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Tu ek expert code analyzer.
            
            [Code]
            - {code}
            
            [TASK]
            - Step by step code ko analyze karo and requirements.txt file ke liye only content return karo
            
            [OUTPUT FORMAT]
            - must only content
            - no expalination, no examples"""),
            ("human", "Be accurate and concise.")
        ])
        chain = prompt | llm | parser
        requirement_log.info("Chain ainvoking completed")
        result = await chain.ainvoke({
            "code": state['contents']
        }, config=runtime.context.config)
        requirement_log.info(f"Returning 'requirements content'")
        requirement_log.info(f"END 'generate_requirements_node'")
        return {"requirements_content": result}
    except RateLimitError as e:
        requirement_log.exception(f"Rate limit heavily exceeded. Returning fallback status. '{str(e)}'")
        requirement_log.info(f"END 'generate_requirements_node'")
        return {}
    except Exception as e:
        requirement_log.exception(f"Error occurred: '{str(e)}")
        requirement_log.info(f"END 'generate_requirements_node'")
        return {}

"""WRITE REQUIREMENTS FILE NODE"""
async def write_requirements_file_node(state: RequirementState, runtime: Runtime[AppContext]) -> dict:
    """Create requirements file"""
    try:
        requirement_log.info(f"START 'write_requirements_file_node'")
        requirement_log.info(f"Calling tool 'write_requirements'")
        result = await runtime.context.session.call_tool(name="write_requirements", arguments={"requirements": state['requirements_content'], "folder_name": state['folder_name']})
        requirement_log.info(f"Result is: '{result}'")
        requirement_log.info(f"END 'write_requirements_file_node'")
        return {"final_answer": result.content[0].text}
    except Exception as e:
        requirement_log.exception(f"Error occurred: '{str(e)}'")
        requirement_log.info(f"END 'write_requirements_file_node'")
        return {}

#--------------------------------
# PHASE 4: GRAPH
#--------------------------------
async def get_requirements_graph():
    try:
        requirement_log.info("Start 'get_requirements_graph'")
        builder = StateGraph(RequirementState)
        builder.add_node("get_files", get_files_node)
        builder.add_node("read_files", read_files_node)
        builder.add_node("generate_requirements", generate_requirements_node)
        builder.add_node("write_requirements", write_requirements_file_node)
        builder.set_entry_point("get_files")
        builder.add_edge("get_files", "read_files")
        builder.add_edge("read_files", "generate_requirements")
        builder.add_edge("generate_requirements", "write_requirements")
        builder.add_edge("write_requirements", END)
        requirement_log.info("Building completed just need to compile.")
        requirement_log.info(f"END 'get_requirements_graph'")
        return builder
        # graph = builder.compile()
        # requirement_log.info(f"Returning graph with seccess: '{type(graph)}'")
        # requirement_log.info(f"END 'get_requirements_graph'")
        # return graph
    except Exception as e:
        requirement_log.exception(f"Error occuured during building graph: '{str(e)}'")
        requirement_log.info(f"END 'get_requirements_graph'")
        return f"Error: {str(e)}"
#--------------------------------
# PHASE 5: TEST
#--------------------------------
if __name__ == "__main__":
    async def main():
        async with streamable_http_client("http://localhost:8080/mcp") as transport:
            read_stream, write_stream, _ = transport
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                runnable_config = RunnableConfig({"configurable": {"thread_id": "test_0009"}})
                app_context = AppContext(config=runnable_config, session=session)
                graph = await get_requirements_graph()
                result = await graph.ainvoke(
                    {
                        "folder_name": "workspace/MyPrograms/assistant.py",
                        "extension": [".py"],
                        "files": [],
                        "contents": "",
                        "requirements_content": "",
                        "final_answer": ""
                    },
                    config=runnable_config,
                    context=app_context
                )
                print(f"\n\n==================[FINAL RESULT]==================\n{result['contents']}")
    
    asyncio.run(main())