const BASE_URL =
    import.meta.env.VITE_API_BASE_URL || 'https://huggingface.co/spaces/ajaysah-ai/github-automation-api/';

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

    // ---- demo (no auth) ----
    demoStart: (goal) => request('/demo/start', { method: 'POST', body: { goal } }),
    demoResume: (guest_id, thread_id, user_input) =>
        request('/demo/resume', { method: 'POST', body: { guest_id, thread_id, user_input } }),

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
    downloadFileUrl: (projectName) => `${BASE_URL}/files/download/${encodeURIComponent(projectName)}`,
    deleteFile: (token, projectName) => request(`/files/${encodeURIComponent(projectName)}`, { method: 'DELETE', token }),

    // ---- demo files ----
    demoListFiles: (guestId) => request(`/demo/files/list/${guestId}`),
    demoUploadFile: (guestId, projectName, file) => {
        const form = new FormData();
        form.append('guest_id', guestId);
        form.append('project_name', projectName);
        form.append('file', file);
        return request('/demo/files/upload', { method: 'POST', body: form, isForm: true });
    },
    demoDownloadFileUrl: (guestId, projectName) => `${BASE_URL}/demo/files/download/${guestId}/${encodeURIComponent(projectName)}`,

    // ---- feedback ----
    submitFeedback: (token, guestId, payload) =>
        request('/feedback', { method: 'POST', body: {...payload, guest_id: guestId || undefined }, token }),
    allFeedbacks: () => request('/all_feedbacks'),
};

export { ApiError, BASE_URL };
