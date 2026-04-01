/**
 * TasteFlow API Utility
 * Implements CSRF-aware fetch as per integration guide
 */

async function fetchWithCSRF(url, options = {}) {
    // Get CSRF token from meta tag
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfMeta ? csrfMeta.content : '';
    
    const defaultOptions = {
        headers: {
            'X-CSRFToken': csrfToken,
            'Accept': 'application/json'
        }
    };

    // Only set Content-Type to JSON if not sending FormData
    if (!(options.body instanceof FormData)) {
        defaultOptions.headers['Content-Type'] = 'application/json';
    }

    // Deep merge headers if provided in options
    if (options.headers) {
        options.headers = { ...defaultOptions.headers, ...options.headers };
    }

    const mergedOptions = { ...defaultOptions, ...options };
    const response = await fetch(url, mergedOptions);

    // Auto-redirect on unauthorized
    if (response.status === 401) {
        window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
        return;
    }
    
    const data = await response.json();
    
    if (!response.ok) {
        // Log error but throw the data so the caller can handle it
        console.error(`API Error [${response.status}]:`, data);
        const error = new Error(data.error || data.message || 'Server Error');
        error.status = response.status;
        error.data = data;
        throw error;
    }

    return data;
}

// Global Toast Utility (Reusable across templates)
function showToast(msg, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    
    const icon = document.getElementById('toast-icon');
    const msgEl = document.getElementById('toast-msg');
    
    if (icon) {
        icon.className = type === 'success'
          ? 'fa-solid fa-circle-check text-herb text-base'
          : 'fa-solid fa-circle-xmark text-red-400 text-base';
    }
    if (msgEl) msgEl.textContent = msg;
    
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3200);
}
