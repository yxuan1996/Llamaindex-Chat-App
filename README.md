# Llamaindex-Chat-App

AI Chat Agent with LlamaIndex, FastAPI, and HTMX

A simple AI-powered chat application with user authentication, conversation history, and streaming responses. Features a modern UI with DaisyUI components including a sidebar for managing conversation threads.

## Features

- 🔐 **Supabase Authentication** - Secure user signup and login
- 💬 **AI Chat** - Powered by Azure OpenAI GPT-4o via LlamaIndex
- 📝 **Conversation History** - Maintains chat context per user and thread
- ⚡ **Real-time Streaming** - Responses stream in real-time
- 🎨 **Modern UI with DaisyUI** - Beautiful, responsive interface with Tailwind CSS
- 🗂️ **Sidebar Navigation** - Easy thread management and switching
- 🧵 **Multiple Threads** - Create and manage separate conversation threads
- 📌 **Pinned Chat Input** - Chat bar stays at the bottom while scrolling

## Project Structure

```
ai-chat-agent/
├── main.py              # FastAPI application
├── templates/
│   └── index.html       # HTMX frontend
├── .env                 # Environment variables (create this)
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Setup Instructions

### Install Dependencies

```bash
# Install dependencies
pip install -r requirements.txt
```

### Configure Environment Variables

Create a `.env` file in the project root:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_MODEL=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```



## Usage

```bash
python main.py
```

The application will start at `http://localhost:8000`


### Chatting

1. Once logged in, you'll see the chat interface with:
   - **Sidebar (left)**: Lists all your conversation threads
   - **Main panel (center)**: Displays your chat messages
   - **Chat bar (bottom)**: Pinned input area for typing messages

2. Type your message in the input box at the bottom
3. Press "Send" or hit Enter
4. Watch the AI response stream in real-time

### Managing Threads

- **Create New Thread**: Click the "New Chat" button in the sidebar
- **Switch Threads**: Click on any thread in the sidebar to switch to it
- **Delete Thread**: Click the trash icon next to any thread (except default)
- Each thread maintains its own conversation history

### Interface Features

- The chat input bar is **pinned at the bottom** and stays visible while scrolling
- The sidebar shows all your conversation threads
- Messages are displayed in a chat bubble format (user on right, AI on left)
- Auto-scrolls to the latest message
- Responsive design that works on different screen sizes

## API Endpoints

### Authentication

- `POST /api/auth/signup` - Create new user account
- `POST /api/auth/login` - Login and get access token

### Chat

- `POST /api/chat` - Send message and get streaming response
  - Requires: `Authorization: Bearer <token>` header
  - Form data: `message`, `thread_id`

### Threads

- `GET /api/threads` - List all threads for current user
- `DELETE /api/threads/{thread_id}` - Delete a thread

## How It Works

### Authentication Flow

1. User signs up/logs in via Supabase
2. Access token is stored in localStorage
3. Token is sent with each API request via Authorization header
4. FastAPI verifies token with Supabase before processing requests

### Chat Flow

1. User types message in HTMX form
2. HTMX sends POST request to `/api/chat` with auth token
3. FastAPI verifies authentication
4. LlamaIndex chat engine processes message with conversation history
5. Response streams back to browser in real-time
6. HTMX appends response to chat messages

### Memory Management

- **SimpleChatStore**: Stores conversation messages in memory
- **ChatMemoryBuffer**: Manages conversation context per user/thread
- **SimpleChatEngine**: Handles chat interactions with LLM

## Extending the Application

### Customize DaisyUI Theme

Change the theme in `index.html`:

```html
<html lang="en" data-theme="dark">  <!-- or: light, cupcake, cyberpunk, etc. -->
```

Available themes: light, dark, cupcake, bumblebee, emerald, corporate, synthwave, retro, cyberpunk, valentine, halloween, garden, forest, aqua, lofi, pastel, fantasy, wireframe, black, luxury, dracula, cmyk, autumn, business, acid, lemonade, night, coffee, winter

### Add Persistent Storage

Replace `SimpleChatStore` with Supabase Postgres:

```python
from llama_index.storage.chat_store import PostgresChatStore

chat_store = PostgresChatStore(
    connection_string=os.getenv("POSTGRES_CONNECTION_STRING")
)
```

### Customize Sidebar Width

Modify the sidebar width class in `index.html`:

```html
<aside id="sidebar" class="w-96 bg-base-100...">  <!-- Change w-80 to w-96, etc. -->
```

### Add Message Timestamps

Modify the message generation in `main.py`:

```python
from datetime import datetime

async def generate():
    timestamp = datetime.now().strftime("%H:%M")
    yield f'<div class="chat chat-start">'
    yield f'<div class="chat-header text-xs opacity-50">{timestamp}</div>'
    yield '<div class="chat-bubble chat-bubble-secondary">'
    # ... rest of the code
```

### Add RAG (Retrieval Augmented Generation)

Index documents and add context to conversations:

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

documents = SimpleDirectoryReader("./data").load_data()
index = VectorStoreIndex.from_documents(documents)
chat_engine = index.as_chat_engine()
```

