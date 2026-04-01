// Shared utilities for all pages
const API_BASE = '';  // same origin

async function apiFetch(url, options = {}) {
    const token = document.querySelector('meta[name="csrf-token"]')?.content;
    
    const config = {
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': token
        },
        ...options
    };

    if (options.body && !(options.body instanceof FormData)) {
        config.body = JSON.stringify(options.body);
    }

    try {
        const response = await fetch(url, config);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || errorData.message || `HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (err) {
        if (err.message.includes('401') || err.message.includes('Unauthorized')) {
            window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
        }
        throw err;
    }
}

// Toast notification (reuse your existing toast if you have one)
function showToast(message, type = 'success') {
    // Implement your toast UI here or use alert for now
    console.log(`[${type.toUpperCase()}] ${message}`);
    // You can enhance this with your existing toast element
}