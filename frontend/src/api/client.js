const BASE_URL =
    import.meta.env.VITE_API_BASE_URL || 'https://ajaysah-ai-github-automation-api.hf.space';

class ApiError extends Error {
    constructor(message, status) {
        super(message);
        this.status = status;
    }
}

async function request(path, { method = 'GET', body, token, isForm = false } = {}) {
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (!isForm && body !== undefined) headers['Content-Type'] = 'application/json';

    const res = await fetch(`${BASE_URL}${path}`, {
        method,
        headers,
        body: isForm ? body : body !== undefined ? JSON.stringify(body) : undefined,
    });

    let data = null;
    try {
        data = await res.json();
    } catch {
        /* no body */
    }

    if (!res.ok) {
        throw new ApiError((data && data.detail) || `Request failed (${res.status})`, res.status);
    }
    return data;
}

export const api = {
    // ---- auth ----
    signup: (payload) => request('/auth/signup', { method: 'POST', body: payload }),
    login: (payload) => request('/auth/login', { method: 'POST', body: payload }),

    // ---- goals (authenticated) ----
    startGoal: (token, goal) => request('/goal/start', { method: 'POST', body: { goal }, token }),
    resumeGoal: (token, thread_id, user_input) =>
        request('/goal/resume', { method: 'POST', body: { thread_id, user_input }, token }),

    // ---- history ----
    getHistory: (token) => request('/history', { token }),
    getThread: (token, threadId) => request(`/history/${threadId}`, { token }),

    // ---- files (authenticated) ----
    listFiles: (token) => request('/files/list', { token }),
    uploadFile: (token, projectName, file) => {
        const form = new FormData();
        form.append('project_name', projectName);
        form.append('file', file);
        return request('/files/upload', { method: 'POST', body: form, token, isForm: true });
    },
    deleteFile: (token, projectName) => request(`/files/${encodeURIComponent(projectName)}`, { method: 'DELETE', token }),

    // ---- feedback ----
    submitFeedback: (token, payload) => request('/feedback', { method: 'POST', body: payload, token }),
    allFeedbacks: () => request('/all_feedbacks'),
};

export { ApiError, BASE_URL };