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
from config.logging_config import readme_log

#-------------------------------------------------
# PHASE 2: LLM + Parsers + State + Runtime Context
#-------------------------------------------------
load_dotenv()
llm = ChatGroq(api_key=os.getenv("GROQ_API_KEY2"), model="openai/gpt-oss-120b", temperature=0.2)
parser = StrOutputParser()

class ReadmeState(TypedDict):
    folder_name: str
    extension: List
    files: List
    contents: str
    readme_content: str
    final_answer: str

@dataclass
class AppContext:
    config: dict
    session: Any
#--------------------------------
# PHASE 3: NODES
#--------------------------------
"""GET FILES NODE"""
async def get_files_node(state: ReadmeState, runtime: Runtime[AppContext]) -> dict:
    """Get all files of specific folder"""
    try:
        readme_log.info(f"START 'get_files_node'")
        base_path = Path(state['folder_name']).resolve()
        if base_path.is_file():
            readme_log.info(f"Path '{state['folder_name']}' is file path")
            readme_log.info(f"END 'get_files_node'")
            return {"files": [base_path], "folder_name": base_path.parent}
        readme_log.info("Calling tool 'list_folder_contents'")
        result = await runtime.context.session.call_tool(name="list_folder_contents", arguments={"folder_name": state['folder_name'], "extension": state['extension']})
        readme_log.info(f"Called tool result is: '{result}'")
        files = []
        for i in range(len(result.content)):
            files.append(result.content[i].text)
        readme_log.info(f"Returning 'files'")
        readme_log.info(f"END 'get_files_node'")
        return {"files": files}
    except Exception as e:
        readme_log.exception(f"Error occurred during get files: '{str(e)}'")
        readme_log.info(f"END 'get_files_node'")
        return {}

"""READ FILES NODE"""
async def read_files_node(state: ReadmeState, runtime: Runtime[AppContext]) -> dict:
    """Read all files concurrently and extract FULL content (including imports)"""
    readme_log.info(f"START 'read_files_node'")
    
    if not state.get('files'):
        readme_log.info(f"No files found in 'state'")
        readme_log.info(f"END 'read_files_node'")
        return {"contents": ""}
        
    async def fetch_full_content(file_path):
        try:
            readme_log.info(f"Calling tool 'read_file' for path: {file_path}")
            result = await runtime.context.session.call_tool(
                name="read_file", 
                arguments={"file_path": file_path}
            )
            readme_log.info(f"Called tool result received for: {file_path}")
            
            if result and hasattr(result, 'content') and len(result.content) > 0:
                full_text = result.content[0].text
                
                # Puri file ka content name ke tag ke sath format kar rahe hain 
                # taaki LLM ko pata chale kaun sa code kis file ka hai
                formatted_content = f"--- File: {file_path} ---\n{full_text}\n"
                return formatted_content
            
            readme_log.error(f"Could not read content from '{file_path}'")
            return f"# [Error]: Could not read content from '{file_path}'"
            
        except Exception as e:
            readme_log.exception(f"Failed to process '{file_path}' due to exception: '{str(e)}'")
            return {}

    # Saari files ke liye tasks create kiye
    tasks = [fetch_full_content(file) for file in state['files']]
    
    # Concurrently saare files ka content load kiya
    extracted_contents = await asyncio.gather(*tasks)
    
    # Saare contents ko combine kiya
    final_contents = "\n\n".join(filter(None, extracted_contents))

    readme_log.info(f"Returning 'final_contents' (Total length: {len(final_contents)})")
    readme_log.info(f"END 'read_files_node'")
    return {"contents": final_contents}

"""GENERATE REQUIREMENTS NODE"""
async def generate_readme_node(state: ReadmeState, runtime: Runtime[AppContext]) -> dict:
    """Generate requirements"""
    try:
        readme_log.info(f"START 'generate_readme_node'")
        system_instruction = (
    "You are an expert technical writer and elite software engineer. Your task is to analyze "
    "the provided source code thoroughly and generate a professional, comprehensive, and clean "
    "README.md file for the GitHub repository.\n\n"
    
    "Strictly follow this structure for the README.md:\n"
    "1. # Project Title - A catchy title followed by a crisp 1-2 sentence description.\n"
    "2. ## Features - Bullet points explaining the core functionalities identified from the code.\n"
    "3. ## Tech Stack - Clearly list the Programming Languages, Libraries, Frameworks, and Tools used.\n"
    "4. ## Getting Started - Step-by-step instructions (Prerequisites, Installation using venv/npm, and Setup).\n"
    "5. ## Environment Variables - If the code uses `os.getenv` or `.env` files, list the keys with placeholders.\n"
    "6. ## Usage - Give exact terminal commands to run the application based on the entry points in the code.\n"
    "7. ## API Endpoints / Architecture (If applicable) - A brief markdown table or list of key functions/routes.\n"
    "8. ## License - Use the MIT License as default.\n\n"
    
    "Guidelines:\n"
    "- Do not make up features; only include what is evident from the code.\n"
    "- Use appropriate emojis for headings to make it visually appealing (e.g., 🚀, 📦, 🛠️).\n"
    "- Wrap all terminal commands and code configurations inside proper markdown code blocks (e.g., ```bash, ```python).\n"
    "- Do not include any conversational text or explanation outside the markdown. Return ONLY the README.md content."
)
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_instruction),
            ("human", "Here is the source code of my project:\n\n```{code_content}\n```\n\nPlease generate the professional README.md based on this.")
        ])
        chain = prompt | llm | parser
        readme_log.info("Chain ainvoking completed")
        result = await chain.ainvoke({
            "code_content": state['contents']
        }, config=runtime.context.config)
        readme_log.info(f"Returning 'requirements content'")
        readme_log.info(f"END 'generate_readme_node'")
        return {"readme_content": result}
    except RateLimitError as e:
        readme_log.exception(f"Rate limit heavily exceeded. Returning fallback status. '{str(e)}'")
        readme_log.info(f"END 'generate_readme_node'")
        return {}
    except Exception as e:
        readme_log.exception(f"Error occurred: '{str(e)}")
        readme_log.info(f"END 'generate_readme_node'")
        return {}

"""WRITE REQUIREMENTS FILE NODE"""
async def write_readme_file_node(state: ReadmeState, runtime: Runtime[AppContext]) -> dict:
    """Create requirements file"""
    try:
        readme_log.info(f"START 'write_readme_file_node'")
        readme_log.info(f"Calling tool 'write_readme'")
        result = await runtime.context.session.call_tool(name="write_readme", arguments={"content": state['readme_content'], "folder_name": state['folder_name']})
        readme_log.info(f"Result is: '{result}'")
        readme_log.info(f"END 'write_readme_file_node'")
        return {"final_answer": result.content[0].text}
    except Exception as e:
        readme_log.exception(f"Error occurred: '{str(e)}'")
        readme_log.info(f"END 'write_readme_file_node'")
        return {}

#--------------------------------
# PHASE 4: GRAPH
#--------------------------------
async def get_readme_graph():
    try:
        readme_log.info("Start 'get_readme_graph'")
        builder = StateGraph(ReadmeState)
        builder.add_node("get_files", get_files_node)
        builder.add_node("read_files", read_files_node)
        builder.add_node("generate_requirements", generate_readme_node)
        builder.add_node("write_requirements", write_readme_file_node)
        builder.set_entry_point("get_files")
        builder.add_edge("get_files", "read_files")
        builder.add_edge("read_files", "generate_requirements")
        builder.add_edge("generate_requirements", "write_requirements")
        builder.add_edge("write_requirements", END)
        readme_log.info("Building completed just need to compile.")
        readme_log.info(f"END 'get_readme_graph'")
        return builder
        # graph = builder.compile()
        # readme_log.info(f"Returning graph with seccess: '{type(graph)}'")
        # readme_log.info(f"END 'get_readme_graph'")
        # return graph
    except Exception as e:
        readme_log.exception(f"Error occuured during building graph: '{str(e)}'")
        readme_log.info(f"END 'get_readme_graph'")
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
                graph = await get_readme_graph()
                result = await graph.ainvoke(
                    {
                        "folder_name": "workspace/MyPrograms/assistant.py",
                        "extension": [".py"],
                        "files": [],
                        "contents": "",
                        "readme_content": "",
                        "final_answer": ""
                    },
                    config=runnable_config,
                    context=app_context
                )
                print(f"\n\n==================[FINAL RESULT]==================\n{result['contents']}")
    
    asyncio.run(main())