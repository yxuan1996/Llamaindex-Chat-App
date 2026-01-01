"""
Simple AI Agent App with LlamaIndex, FastAPI, HTMX, and Supabase
This application provides a chat interface with AI using Azure OpenAI
"""

from fastapi import FastAPI, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from supabase import create_client, Client
from llama_index.core import Settings
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.core.chat_engine import SimpleChatEngine
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.storage.chat_store import SimpleChatStore
from llama_index.storage.chat_store.postgres import PostgresChatStore
import os
from dotenv import load_dotenv
from typing import Optional
import json

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="AI Chat Agent")
templates = Jinja2Templates(directory="templates")

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Postgres Connection
POSTGRES_CONNECTION_STRING = os.getenv("POSTGRES_CONNECTION_STRING")

# Initialize Azure OpenAI with LlamaIndex
llm = AzureOpenAI(
    engine=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    model=os.getenv("AZURE_OPENAI_MODEL", "gpt-4o"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
)

# Set global LlamaIndex settings
Settings.llm = llm

# initialize Postgres Chat Store
chat_store = PostgresChatStore.from_uri(
    uri=POSTGRES_CONNECTION_STRING,
    table_name="llamaindex_simple_chat_history"
)


# Dependency: Verify authentication
async def get_current_user(request: Request):
    """
    Verify the user is authenticated by checking the Authorization header
    Returns the user data from Supabase
    """
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        # Verify the token with Supabase
        user = supabase.auth.get_user(token)
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


# Store chat engines per user/thread (in-memory for simplicity)
user_chat_engines = {}


def get_chat_engine(user_id: str, thread_id: str = "default"):
    """
    Get or create a chat engine for a specific user and thread
    Each thread maintains its own conversation history
    """
    key = f"{user_id}_{thread_id}"
    
    if key not in user_chat_engines:
        # Load existing messages from database
        existing_messages = chat_store.get_messages(key)
        
        # Create memory buffer for this thread with existing messages
        memory = ChatMemoryBuffer.from_defaults(
            token_limit=3000,
            chat_store=chat_store,
            chat_store_key=key
        )
        
        # If there are existing messages, set them in memory
        if existing_messages:
            chat_store.set_messages(key, existing_messages)
        
        # Create chat engine with memory
        chat_engine = SimpleChatEngine.from_defaults(
            llm=llm,
            memory=memory
        )
        
        user_chat_engines[key] = chat_engine
    
    return user_chat_engines[key]


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main chat interface"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/chat")
async def chat(
    message: str = Form(...),
    thread_id: str = Form("default"),
    user = Depends(get_current_user)
):
    """
    Handle chat messages from the user
    - Verifies authentication
    - Gets the appropriate chat engine for user/thread
    - Streams the response back
    """
    user_id = user.user.id
    
    # Get chat engine for this user and thread
    chat_engine = get_chat_engine(user_id, thread_id)
    
    # Get streaming response from LlamaIndex
    response = chat_engine.stream_chat(message)
    
    # Stream the response back to the client
    async def generate():
        """Generator function to stream AI response with DaisyUI styling"""
        yield '<div class="chat chat-start" hx-swap-oob="beforeend:#messages">'
        yield '<div class="chat-bubble chat-bubble-secondary">'
        
        for token in response.response_gen:
            # Escape HTML in tokens
            safe_token = token.replace("<", "&lt;").replace(">", "&gt;")
            yield safe_token
        
        yield '</div></div>'
    
    return StreamingResponse(generate(), media_type="text/html")


@app.post("/api/auth/login")
async def login(email: str = Form(...), password: str = Form(...)):
    """
    Login endpoint - authenticates user with Supabase
    Returns the session token
    """
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        return {
            "success": True,
            "access_token": response.session.access_token,
            "user": {
                "id": response.user.id,
                "email": response.user.email
            }
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Login failed: {str(e)}")


# @app.post("/api/auth/signup")
# async def signup(email: str = Form(...), password: str = Form(...)):
#     """
#     Signup endpoint - creates new user in Supabase
#     """
#     try:
#         response = supabase.auth.sign_up({
#             "email": email,
#             "password": password
#         })
        
#         return {
#             "success": True,
#             "message": "Account created successfully",
#             "user": {
#                 "id": response.user.id,
#                 "email": response.user.email
#             }
#         }
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Signup failed: {str(e)}")


@app.get("/api/threads")
async def get_threads(user = Depends(get_current_user)):
    """
    Get list of chat threads for the current user
    Returns available thread IDs from the database
    """
    user_id = user.user.id
    
    # Get all keys from database
    all_keys = chat_store.get_keys()
    
    # Filter keys for this user
    user_prefix = f"{user_id}_"
    threads = []
    
    for key in all_keys:
        if key.startswith(user_prefix):
            thread_id = key.replace(user_prefix, "", 1)
            threads.append(thread_id)
    
    # Always include default thread
    if "default" not in threads:
        threads.insert(0, "default")
    
    return {"threads": threads}


@app.get("/api/threads/{thread_id}/messages")
async def get_thread_messages(thread_id: str, user = Depends(get_current_user)):
    """
    Get all messages for a specific thread
    Returns the conversation history in HTML format
    """
    user_id = user.user.id
    key = f"{user_id}_{thread_id}"
    
    # Get messages from database
    messages = chat_store.get_messages(key)
    
    # Convert messages to HTML
    html_messages = []
    for msg in messages:
        if msg.role == "user":
            html_messages.append(f'''
                <div class="chat chat-end">
                    <div class="chat-bubble chat-bubble-primary">{msg.content}</div>
                </div>
            ''')
        elif msg.role == "assistant":
            html_messages.append(f'''
                <div class="chat chat-start">
                    <div class="chat-bubble chat-bubble-secondary">{msg.content}</div>
                </div>
            ''')
    
    return {"messages": html_messages}


@app.delete("/api/threads/{thread_id}")
async def delete_thread(thread_id: str, user = Depends(get_current_user)):
    """
    Delete a chat thread
    Removes the chat history from database and engine cache
    """
    user_id = user.user.id
    key = f"{user_id}_{thread_id}"
    
    # Delete from database
    chat_store.delete_messages(key)
    
    # Remove from engine cache if exists
    if key in user_chat_engines:
        del user_chat_engines[key]
    
    return {"success": True, "message": f"Thread {thread_id} deleted"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)