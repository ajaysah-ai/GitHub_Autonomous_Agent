from mcp.server.fastmcp import FastMCP
from mcp import McpError, ErrorData
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Union
import asyncio, os, base64, time, shutil, httpx, zipfile, io, uvicorn, sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
from config.logging_config import mcp_log

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BASE_URL = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

mcp = FastMCP("GitHub MCP Server")

# Server file ke top mein add karo
WORKSPACE_DIR = Path("workspace").resolve()
WORKSPACE_DIR.mkdir(exist_ok=True)

def resolve_workspace_path(name: str) -> Path:
    """
    Chahe LLM 'MyPrograms' de ya 'workspace/MyPrograms' de —
    yeh function HAMESHA same correct path return karega.
    """
    mcp_log.info(f"START 'resolve_workspace_path'")
    name = name.replace("\\", "/").strip("/")
    if name.startswith("workspace/"):
        name = name[len("workspace/"):]   # Duplicate prefix hatao
    path = (WORKSPACE_DIR / name).resolve()

    # Safety — workspace ke bahar access block karo
    if not str(path).startswith(str(WORKSPACE_DIR)):
        mcp_log.exception(f"Access denied outside workspace: '{name}'")
        raise ValueError(f"Access denied outside workspace: {name}")
    mcp_log.info(f"END 'resolve_workspace_path'")
    return path

@mcp.tool()
async def create_repo(github_personal_access_token: str, repo_name: str, private: bool = False, description: str = "Handled via GitHub Automation Agent") -> str:
    """
    For create new repository on GitHub.

    Args:
        repo_name: Name of repository
        private: Type of repository (default is False means public)
        description: Small description about repository (e.g. "This Repository handled through GitHub Agent")
    """
    HEADERS = {
        "Authorization": f"Bearer {github_personal_access_token}",
        "Accept": "application/vnd.github+json"
    }
    mcp_log.info(f"START 'create_repo'")
    try:
        url = f"{BASE_URL}/user/repos"
        data = {
            "name": repo_name,
            "private": private,
            "description": description,
            "auto_init": False,
            "licence_template": "mit",
        }
        async with httpx.AsyncClient() as client:
            mcp_log.info(f"Fetching with 'POST' method from '{url}'")
            response = await client.post(url, headers=HEADERS, json=data)
        if response.status_code == 201:
            repo_url = response.json()['html_url']
            mcp_log.info(f"Response status code: '{response.status_code}'")
            mcp_log.info(f"END 'create_repo'")
            return f"Repo {repo_name} created at {time.strftime('%A %Y-%m-%d %H:%M:%S', time.localtime(time.time()))}."
        res_data = response.json()
        error_msg = res_data.get("message", "No message")
        if "errors" in res_data:
            detailed_errors = []
            for err in res_data['errors']:
                if isinstance(err, dict):
                    detailed_errors.append(f"{err.get('resource', '')} {err.get('code', '')}: {err.get('message', '')}")
                else:
                    detailed_errors.append(str(err))
            error_msg += f" | Details: {', '.join(detailed_errors)}"
        mcp_log.exception(f"Status code: '{response.status_code}' | Error msg: '{error_msg}'")
        mcp_log.info(f"END 'create_repo'")
        return f"Error: {response.status_code} - {error_msg}"
    except Exception as e:
        mcp_log.exception(f"Error occurred: '{str(e)}'")
        mcp_log.info(f"END 'create_repo'")
        raise McpError(
            ErrorData(
                code=-32602,
                message=str(e)
            )
        )

@mcp.tool()
async def create_local_folder(folder_name: str):
    """For create local folder in 'workspace' folder."""
    mcp_log.info(f"START 'create_local_folder'")
    try:
        target_path = resolve_workspace_path(folder_name)   # ✅ Ek line
        if target_path.exists():
            mcp_log.info(f"Folder '{folder_name}' already exists.")
            mcp_log.info(f"END 'create_local_folder'")
            return f"Folder '{folder_name}' already exists."
        target_path.mkdir(parents=True, exist_ok=True)
        mcp_log.info(f"Folder created at 'workspace/{target_path.name}'")
        mcp_log.info(f"END 'create_local_folder'")
        return f"Folder created at 'workspace/{target_path.name}'"
    except Exception as e:
        mcp_log.exception(f"Error occurred: '{str(e)}'")
        mcp_log.info(f"END 'create_local_folder'")
        raise McpError(ErrorData(code=-32602, message=str(e)))

@mcp.tool()
async def copy_folder(source_folder_path: str, destination_folder_name: str):
    """For copy entire folder into 'workspace' folder."""
    mcp_log.info(f"START 'copy_folder'")
    try:
        source_path = Path(source_folder_path).resolve()   # Source — as-is, external path
        destination_path = resolve_workspace_path(destination_folder_name)  # ✅ Fix
        if destination_path.exists():
            mcp_log.info(f"Folder '{destination_folder_name}' already exists.")
            mcp_log.info(f"END 'copy_folder'")
            return f"Folder '{destination_folder_name}' already exists."
        await asyncio.to_thread(shutil.copytree, source_path, destination_path, dirs_exist_ok=True)
        mcp_log.info(f"Copied folder using 'asyncio.to_thread'")
        mcp_log.info(f"END 'copy_folder'")
        return f"Copied to workspace/{destination_path.relative_to(WORKSPACE_DIR)}"
    except Exception as e:
        mcp_log.exception(f"Error occurred: '{str(e)}'")
        mcp_log.info(f"END 'copy_folder'")
        raise McpError(ErrorData(code=-32602, message=str(e)))

@mcp.tool()
async def write_requirements(requirements: str, folder_name: str):
    """For write 'requirements.txt'."""
    mcp_log.info(f"START 'write_requirements'")
    try:
        folder_path = resolve_workspace_path(folder_name)   # ✅ Fix
        if not folder_path.exists():
            mcp_log.info(f"Folder '{folder_name}' does not exist.")
            mcp_log.info(f"END 'write_requirements'")
            return f"Folder '{folder_name}' does not exist."
        (folder_path / "requirements.txt").write_text(requirements, encoding="utf-8")
        mcp_log.info(f"'requirements.txt' written at 'workspace/{folder_path.relative_to(WORKSPACE_DIR)}/requirements.txt'")
        mcp_log.info(f"END 'write_requirements'")
        return f"requirements.txt written at workspace/{folder_path.relative_to(WORKSPACE_DIR)}/requirements.txt"
    except Exception as e:
        mcp_log.exception(f"Error occurred: '{str(e)}'")
        mcp_log.info(f"END 'write_requirements'")
        raise McpError(ErrorData(code=-32602, message=str(e)))

@mcp.tool()
async def write_readme(content: str, folder_name: str):
    """For write 'README.md'."""
    mcp_log.info(f"START 'write_readme'")
    try:
        folder_path = resolve_workspace_path(folder_name)   # ✅ Fix
        if not folder_path.exists():
            mcp_log.info(f"Folder '{folder_name}' does not exist.")
            mcp_log.info(f"END 'write_readme'")
            return f"Folder '{folder_name}' does not exist."
        (folder_path / "README.md").write_text(content, encoding="utf-8")
        mcp_log.info(f"'README.md' written at 'workspace/{folder_path.relative_to(WORKSPACE_DIR)}/README.md'")
        mcp_log.info(f"END 'write_readme'")
        return f"README.md written at workspace/{folder_path.relative_to(WORKSPACE_DIR)}/README.md"
    except Exception as e:
        mcp_log.exception(f"Error occurred: '{str(e)}'")
        mcp_log.info(f"END 'write_readme'")
        raise McpError(ErrorData(code=-32602, message=str(e)))

@mcp.tool()
async def push_folder(github_personal_access_token: str, workspace_folder_name: str, repo_name: str, commit: str = "initial commit via Agent"):
    """
    For push local folder with files on GitHub repo.

    Args:
        workspace_folder_name: Name of folder which is existing in workspace (e.g. workspace/...)
        repo_name: Name of repository
        commit: Commit message
    """
    HEADERS = {
        "Authorization": f"Bearer {github_personal_access_token}",
        "Accept": "application/vnd.github+json"
    }
    mcp_log.info(f"START 'push_folder'")
    try:
        IGNORE_LIST = [".env", "__pycache__", "venv", ".venv", "env", ".vscode", ".idea", ".DS_Store"]
        if "workspace" in workspace_folder_name:
            local_folder_path = Path(workspace_folder_name).resolve()
        else:
            local_folder_path = Path(f"workspace/{workspace_folder_name}").resolve()
        if not local_folder_path.exists():
            mcp_log.info(f"Local folder '{workspace_folder_name}' does not exist, please re-check.")
            mcp_log.info(f"END 'push_folder'")
            return f"Local folder '{workspace_folder_name}' does not exist, please re-check."
        success_count = 0
        failed_files = []
        async with httpx.AsyncClient() as client:
            mcp_log.info(f"Fetching data with 'GET' method from '{BASE_URL}/user'")
            user_resp = await client.get(f"{BASE_URL}/user", headers=HEADERS)
        username = user_resp.json()['login']
        if "/" not in repo_name:
            repo_name = f"{username}/{repo_name}"
        for file_path in local_folder_path.rglob("*"):
            if any(part in IGNORE_LIST for part in file_path.parts):
                continue
            if file_path.is_file():
                relative_path = file_path.relative_to(local_folder_path).as_posix()
                with open(file_path, "rb") as f:
                    content = f.read()
                base64_content = base64.b64encode(content).decode("utf-8")
                url = f"{BASE_URL}/repos/{repo_name}/contents/{workspace_folder_name}/{relative_path}"
                data = {
                    "message": f"Upload {relative_path} via Agent",
                    "content": base64_content
                }
                async with httpx.AsyncClient() as client:
                    mcp_log.info(f"Fetching data with 'PUT' method from '{url}'")
                    response = await client.put(url, headers=HEADERS, json=data)
                if response.status_code in [200, 201]:
                    success_count += 1
                else:
                    failed_files.append(relative_path)
        if len(failed_files) == 0:
            mcp_log.info(f"All '{success_count}' files pushed successfully at {time.strftime('%A %Y-%m-%d %H:%M:%S')}")
            mcp_log.info(f"END 'push_folder'")
            return f"All {success_count} files pushed successfully at {time.strftime('%A %Y-%m-%d %H:%M:%S')}"
        else:
            mcp_log.info(f"Some files are failed during pushed, failed files: '{failed_files}'")
            mcp_log.info(f"END 'push_folder'")
            return f"Some files are failed during pushed, failed files: {failed_files}"
    except Exception as e:
        mcp_log.exception(f"Error occurred: '{str(e)}'")
        mcp_log.info(f"END 'push_folder'")
        raise McpError(
            ErrorData(
                code=-32602,
                message=str(e)
            )
        )

@mcp.tool()
async def copy_file(source_file_path: str, destination_folder_name: str):
    """For copy file"""
    mcp_log.info(f"START 'copy_file'")
    try:
        target_folder_path = resolve_workspace_path(destination_folder_name)
        target_folder_path.mkdir(parents=True, exist_ok=True)  # Exist ho ya na ho — theek hai
        await asyncio.to_thread(shutil.copy2, source_file_path, target_folder_path)
        mcp_log.info(f"Copied file using 'asyncio.to_thread'")
        mcp_log.info(f"END 'copy_file'")
        return f"File copied to workspace/{target_folder_path.relative_to(WORKSPACE_DIR)}"
    except Exception as e:
        mcp_log.exception(f"Error occurred: '{str(e)}'")
        mcp_log.info(f"END 'copy_file'")
        raise McpError(ErrorData(code=-32602, message=str(e)))

@mcp.tool()
async def delete_repo(github_personal_access_token: str, repo_name: str) -> str:
    """
    ⚠️ DANGEROUS - Repository delete karo.
    Args:
        repo_name: Repository ka naam
    """
    HEADERS = {
        "Authorization": f"Bearer {github_personal_access_token}",
        "Accept": "application/vnd.github+json"
    }
    mcp_log.info(f"START 'delete_repo'")
    try:
        async with httpx.AsyncClient() as client:
            mcp_log.info(f"Fetching data with 'GET' method from '{BASE_URL}/user'")
            user_resp = await client.get(f"{BASE_URL}/user", headers=HEADERS)
        username = user_resp.json()['login']
        if "/" not in repo_name:
            repo_name = f"{username}/{repo_name}"
        url = f"{BASE_URL}/repos/{repo_name}"
        async with httpx.AsyncClient() as client:
            mcp_log.info(f"DELETING data with 'DELETE' method from '{url}'")
            response = await client.delete(url, headers=HEADERS)
        if response.status_code == 204:
            mcp_log.info(f"Deleted: '{repo_name}' | Status code: '{response.status_code}'")
            mcp_log.info(f"END 'delete_repo'")
            return f"Deleted: {repo_name}"
        return f"Error: {response.json().get('message')}"
    except Exception as e:
        mcp_log.exception(f"Error occurred: '{str(e)}'")
        mcp_log.info(f"END 'delete_repo'")
        raise McpError(
            ErrorData(
                code=-32602,
                message=str(e)
            )
        )

@mcp.tool()
async def list_folders():
    """List all folders of workspace"""
    mcp_log.info(f"START 'list_folders'")
    try:
        base_path = Path("workspace").resolve()
        if not base_path.exists():
            mcp_log.info(f"Folder 'workspace' does not exist on local machine, please first use 'create_local_folder' function.")
            mcp_log.info(f"END 'list_folders'")
            return f"Folder 'workspace' does not exist on local machine, please first use 'create_local_folder' function."
        folders = []
        for item in base_path.iterdir():
            if item.name.startswith("."):
                continue
            if item.is_dir():
                folders.append(item.name)
        if len(folders) == 0:
            mcp_log.info(f"No folders available on 'workspace'")
            mcp_log.info(f"END 'list_folders'")
            return f"No folders available on 'workspace'"
        mcp_log.info(f"Available folders are: '{folders}'")
        mcp_log.info(f"END 'list_folders'")
        return f"Available folders are: {folders}"
    except Exception as e:
        mcp_log.exception(f"Error occurred: '{str(e)}'")
        mcp_log.info(f"END 'list_folders'")
        raise McpError(
            ErrorData(
                code=-32602,
                message=str(e)
            )
        )
    
@mcp.tool()
async def list_repos(github_personal_access_token: str) -> str:
    """For list all repositories of user"""
    HEADERS = {
        "Authorization": f"Bearer {github_personal_access_token}",
        "Accept": "application/vnd.github+json"
    }
    mcp_log.info(f"START 'list_repos'")
    try:
        url = f"{BASE_URL}/user/repos"
        async with httpx.AsyncClient() as client:
            mcp_log.info(f"Fetching data with 'GET' method from '{url}'")
            response = await client.get(url, headers=HEADERS, params={"per_page": 20})
        repos = response.json()
        repo_names = [r["name"] for r in repos]
        mcp_log.info(f"END 'list_repos'")
        return f"Total: {len(repo_names)}\n" + "\n".join(repo_names)
    except Exception as e:
        mcp_log.exception(f"Error occurred: '{str(e)}'")
        mcp_log.info(f"END 'list_repos'")
        raise McpError(
            ErrorData(
                code=-32602,
                message=str(e)
            )
        )

@mcp.tool()
async def list_repo_files(github_personal_access_token: str, repo_name: str, sub_folder_name: str = "") -> str:
    """
    For List all files and folders in repo.

    Args:
        repo_name: Name of repository
        sub_folder_name: Specific folder name (empty = root)
    """
    HEADERS = {
        "Authorization": f"Bearer {github_personal_access_token}",
        "Accept": "application/vnd.github+json"
    }
    mcp_log.info(f"START 'list_repo_files'")
    try:
        async with httpx.AsyncClient() as client:
            mcp_log.info(f"Fetching data with 'GET' method from '{BASE_URL}/user'")
            user_resp = await client.get(f"{BASE_URL}/user", headers=HEADERS)
        username = user_resp.json()["login"]
        if "/" not in repo_name:
            repo_name = f"{username}/{repo_name}"
        url = f"{BASE_URL}/repos/{repo_name}/contents/{sub_folder_name}"
        async with httpx.AsyncClient() as client:
            mcp_log.info(f"Fetching data with 'GET' method from '{url}'")
            response = await client.get(url, headers=HEADERS)
        if response.status_code != 200:
            mcp_log.info(f"Error: '{response.json().get('message')}'")
            mcp_log.info(f"END 'list_repo_files'")
            return f"Error: {response.json().get('message')}"
        items = response.json()
        files = [f"{'📂' if i['type']=='dir' else '📄'} {i['name']}" for i in items]
        mcp_log.info(f"Files count is: '{len(files)}'")
        mcp_log.info(f"END 'list_repo_files'")
        return "\n".join(files)
    except Exception as e:
        mcp_log.exception(f"Error occurred: '{str(e)}'")
        mcp_log.info(f"END 'list_repo_files'")
        raise McpError(
            ErrorData(
                code=-32602,
                message=str(e)
            )
        )

@mcp.tool()
def read_file(file_path: str):
    """
    For read files.

    Args: file_path: e.g. 'MyPrograms/script.py' (workspace-relative)
    """
    mcp_log.info(f"START 'read_file'")
    try:
        try:
            file = resolve_workspace_path(file_path)   # ✅ Workspace-relative try karo
        except Exception:
            mcp_log.exception("Sub-Exception...")
            file = Path(file_path).resolve()           # Fallback — absolute path
        if not file.exists():
            mcp_log.info(f"File '{file_path}' is not available.")
            mcp_log.info(f"END 'read_file'")
            return f"File '{file_path}' is not available."
        return f"File content:\n{file.read_text(encoding='utf-8', errors='ignore')}"
    except Exception as e:
        mcp_log.exception(f"Error occurred: '{str(e)}'")
        mcp_log.info(f"END 'read_file'")
        raise McpError(ErrorData(code=-32602, message=str(e)))

@mcp.tool()
async def pull_repo(github_personal_access_token: str, repo_url: str, local_folder_path: str, branch: str = "main"):
    """
    For pull/download github repo via url (link).

    Args:
        repo_url: Url of github repo (e.g., "https://github.com/user_name/repo_name")
        local_folder_path: Path of local folder of 'workspace' (e.g., "workspace/local_folder_name")
        branch: Name of branch (default is "main")
    """
    HEADERS = {
        "Authorization": f"Bearer {github_personal_access_token}",
        "Accept": "application/vnd.github+json"
    }
    mcp_log.info(f"START 'pull_repo'")
    try:
        print(f"\n\nPull repo starting...")
        url_parts = repo_url.rstrip("").split("/")
        print(url_parts)
        repo_name = url_parts[-1]
        repo_owner = url_parts[-2]
        if not "workspace" in local_folder_path:
            base_dir = Path("workspace").resolve()
            target_dir = base_dir / local_folder_path
        else:
            target_dir = Path(local_folder_path).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        api_url = f"https://github.com/{repo_owner}/{repo_name}/archive/refs/heads/{branch}.zip"
        async with httpx.AsyncClient(follow_redirects=True, timeout=120.0) as client:
            mcp_log.info(f"Fetching data with 'GET' method from '{api_url}'")
            response = await client.get(api_url, headers=HEADERS)
            if response.status_code != 200:
                mcp_log.debug(f"Status code: '{response.status_code}'")
                mcp_log.info(f"END 'pull_repo'")
                return {
                    "status": "error",
                    "message": f"GitHub API Error {response.status_code}: {response.text}"
                }
            zip_file_path = target_dir / f"{repo_name}.zip"
            with open(zip_file_path, "wb") as f:
                f.write(response.content)
            mcp_log.info(f"END 'pull_repo'")
            return {
                "status": "success",
                "message": f"Repository successfully pulled and extracted to '{local_folder_path}'"
            }
    except Exception as e:
        mcp_log.exception(f"Error occurred: '{str(e)}'")
        mcp_log.info(f"END 'pull_repo'")
        raise McpError(
            ErrorData(
                code=-32602,
                message=str(e)
            )
        )

@mcp.tool()
async def list_folder_contents(folder_name: str, extensions: Union[List[str], str] = None):
    """
    Workspace ke andar kisi folder ke SAARE files list karo (recursively).
    IMPORTANT: read_file() use karne se PEHLE yeh call karo —
    taaki actual filenames pata chalein, guess na karna pade.

    Args:
        folder_name: Folder ka naam (e.g. "MyPrograms")
        extensions: Optional filter — e.g. [".py", ".md"] ya sirf ".py" multiple extensions ke liye.
    """
    mcp_log.info(f"START 'list_folder_contents'")
    try:
        folder_path = resolve_workspace_path(folder_name)
        if not folder_path.exists():
            mcp_log.info(f"Folder '{folder_name}' does not exist.")
            mcp_log.info(f"END 'list_folder_contents'")
            return f"Folder '{folder_name}' does not exist."
        # Agar user ne single string di hai (e.g. ".py"), toh use list me convert kar rahe hain
        if isinstance(extensions, str):
            ext_list = [extensions]
        elif extensions is None:
            ext_list = []
        else:
            ext_list = list(extensions)
        # Files ki recursive searching aur multiple extension matching
        files = [
            f.relative_to(WORKSPACE_DIR).as_posix()
            for f in folder_path.rglob("*")
            if f.is_file() and (not ext_list or f.suffix in ext_list)
        ]
        if not files:
            mcp_log.info(f"No files found in '{folder_name}'")
            mcp_log.info(f"END 'list_folder_contents'")
            ext_msg = f" with extensions {ext_list}" if ext_list else ""
            return f"No files found in '{folder_name}'" + ext_msg
        mcp_log.info(f"END 'list_folder_contents'")
        return files
    except Exception as e:
        mcp_log.exception(f"Error occurred: '{str(e)}'")
        mcp_log.info(f"END 'list_folder_contents'")
        raise McpError(ErrorData(code=-32602, message=str(e)))

if __name__=="__main__":
    mcp_app = mcp.streamable_http_app()
    uvicorn.run(mcp_app, host="0.0.0.0", port=8080)
    # result = asyncio.run(list_folder_contents("MyPrograms", [".txt"]))
    # print(result)
    