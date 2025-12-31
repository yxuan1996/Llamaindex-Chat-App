// Store authentication token and current thread
let authToken = localStorage.getItem('authToken');
let currentThread = 'default';

// Check if user is already authenticated
if (authToken) {
    showChat();
    loadThreads();
}

// Add auth token to all HTMX requests
document.body.addEventListener('htmx:configRequest', (event) => {
    if (authToken) {
        event.detail.headers['Authorization'] = 'Bearer ' + authToken;
    }
});

// Handle authentication errors
document.body.addEventListener('htmx:responseError', (event) => {
    if (event.detail.xhr.status === 401) {
        logout();
    }
});

function showLogin() {
    document.getElementById('login-form').classList.remove('hidden');
    document.getElementById('signup-form').classList.add('hidden');
    document.getElementById('login-error').textContent = '';
}

function showSignup() {
    document.getElementById('login-form').classList.add('hidden');
    document.getElementById('signup-form').classList.remove('hidden');
    document.getElementById('signup-error').textContent = '';
}

function showChat() {
    document.getElementById('auth-container').classList.add('hidden');
    document.getElementById('chat-container').classList.remove('hidden');
}

async function handleLogin(event) {
    event.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    const formData = new FormData();
    formData.append('email', email);
    formData.append('password', password);

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            authToken = data.access_token;
            localStorage.setItem('authToken', authToken);
            showChat();
            loadThreads();
        } else {
            document.getElementById('login-error').textContent = 'Login failed';
        }
    } catch (error) {
        document.getElementById('login-error').textContent = 'Login failed: ' + error.message;
    }
}

async function handleSignup(event) {
    event.preventDefault();
    const email = document.getElementById('signup-email').value;
    const password = document.getElementById('signup-password').value;

    const formData = new FormData();
    formData.append('email', email);
    formData.append('password', password);

    try {
        const response = await fetch('/api/auth/signup', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            // Show success toast
            showToast('Account created successfully! Please login.', 'success');
            showLogin();
        } else {
            document.getElementById('signup-error').textContent = 'Signup failed';
        }
    } catch (error) {
        document.getElementById('signup-error').textContent = 'Signup failed: ' + error.message;
    }
}

function logout() {
    localStorage.removeItem('authToken');
    authToken = null;
    currentThread = 'default';
    document.getElementById('auth-container').classList.remove('hidden');
    document.getElementById('chat-container').classList.add('hidden');
    document.getElementById('messages').innerHTML = '';
    document.getElementById('thread-list').innerHTML = '';
    showLogin();
}

async function loadThreads() {
    try {
        const response = await fetch('/api/threads', {
            headers: {
                'Authorization': 'Bearer ' + authToken
            }
        });

        const data = await response.json();
        const threadList = document.getElementById('thread-list');
        threadList.innerHTML = '';

        data.threads.forEach(thread => {
            const isActive = thread === currentThread;
            threadList.innerHTML += `
                <div class="thread-item p-3 rounded-lg cursor-pointer ${isActive ? 'active' : ''}" 
                        onclick="switchThread('${thread}')">
                    <div class="flex items-center justify-between">
                        <div class="flex-1">
                            <div class="font-semibold text-sm">${formatThreadName(thread)}</div>
                            <div class="text-xs text-base-content/60 truncate">Conversation thread</div>
                        </div>
                        ${thread !== 'default' ? `
                        <button class="btn btn-ghost btn-xs" onclick="deleteThread(event, '${thread}')">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                            </svg>
                        </button>
                        ` : ''}
                    </div>
                </div>
            `;
        });
    } catch (error) {
        console.error('Failed to load threads:', error);
    }
}

function formatThreadName(thread) {
    if (thread === 'default') return 'Default Chat';
    return thread.split('-').map(word => 
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
}

function switchThread(threadId) {
    currentThread = threadId;
    document.getElementById('thread-id-input').value = threadId;
    document.getElementById('current-thread-name').textContent = formatThreadName(threadId);
    document.getElementById('messages').innerHTML = '';
    
    // Update active state in sidebar
    document.querySelectorAll('.thread-item').forEach(item => {
        item.classList.remove('active');
    });
    event.currentTarget.classList.add('active');
}

function createNewThread() {
    const threadName = prompt('Enter a name for the new chat:');
    if (threadName) {
        const threadId = threadName.toLowerCase().replace(/\s+/g, '-');
        switchThread(threadId);
        loadThreads();
    }
}

async function deleteThread(event, threadId) {
    event.stopPropagation();
    
    if (threadId === 'default') {
        showToast('Cannot delete the default thread', 'error');
        return;
    }

    if (!confirm(`Delete thread "${formatThreadName(threadId)}"?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/threads/${threadId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': 'Bearer ' + authToken
            }
        });

        if (response.ok) {
            showToast('Thread deleted successfully', 'success');
            if (currentThread === threadId) {
                switchThread('default');
            }
            loadThreads();
        }
    } catch (error) {
        console.error('Failed to delete thread:', error);
        showToast('Failed to delete thread', 'error');
    }
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} fixed top-4 right-4 w-96 z-50 shadow-lg`;
    toast.innerHTML = `
        <span>${message}</span>
    `;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// Add user message to chat before sending
document.getElementById('chat-form').addEventListener('submit', (event) => {
    const input = document.getElementById('message-input');
    const message = input.value.trim();
    
    if (message) {
        const userMessageDiv = document.createElement('div');
        userMessageDiv.className = 'chat chat-end';
        userMessageDiv.innerHTML = `
            <div class="chat-bubble chat-bubble-primary">${escapeHtml(message)}</div>
        `;
        document.getElementById('messages').appendChild(userMessageDiv);
        
        // Scroll to bottom
        scrollToBottom();
    }
});

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom() {
    const container = document.getElementById('messages-container');
    container.scrollTop = container.scrollHeight;
}

// Auto-scroll to bottom when new messages arrive
const observer = new MutationObserver(() => {
    scrollToBottom();
});

observer.observe(document.getElementById('messages'), {
    childList: true,
    subtree: true
});