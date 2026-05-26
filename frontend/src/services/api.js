import axios from 'axios';

const api = axios.create({
  baseURL: '',
});

let authToken = null;

export const setAuthToken = (token) => {
  authToken = token;
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common['Authorization'];
  }
};

api.interceptors.request.use(
  (config) => {
    if (authToken) {
      config.headers.Authorization = `Bearer ${authToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export const authAPI = {
  login: async (email, password) => {
    const response = await api.post('/api/v1/auth/login', { email, password });
    return response.data;
  },
  signup: async (email, password, full_name) => {
    const response = await api.post('/api/v1/auth/signup', { email, password, full_name });
    return response.data;
  },
  me: async () => {
    const response = await api.get('/api/v1/auth/me');
    return response.data;
  },
};

export const adminAPI = {
  getPlatformStats: async () => {
    const response = await api.get('/api/v1/admin/analytics');
    return response.data;
  },
  getUserStats: async () => {
    const response = await api.get('/api/v1/admin/analytics/users');
    return response.data;
  },
  getTokenStats: async () => {
    const response = await api.get('/api/v1/admin/analytics/tokens');
    return response.data;
  },
  getLogs: async (params = {}) => {
    // build query string
    const query = new URLSearchParams();
    if (params.endpoint) query.append('endpoint', params.endpoint);
    if (params.status_code) query.append('status_code', params.status_code);
    if (params.user_id) query.append('user_id', params.user_id);
    if (params.limit) query.append('limit', params.limit);
    
    const response = await api.get(`/api/v1/admin/logs?${query.toString()}`);
    return response.data;
  },
  getUsers: async () => {
    const response = await api.get('/api/v1/admin/users');
    return response.data;
  },
};

export const chatAPI = {
  getSessions: async () => {
    const response = await api.get('/api/v1/chat/sessions');
    return response.data;
  },
  createSession: async (title) => {
    const response = await api.post('/api/v1/chat/sessions', { title });
    return response.data;
  },
  updateSession: async (sessionId, title) => {
    const response = await api.put(`/api/v1/chat/sessions/${sessionId}`, { title });
    return response.data;
  },
  deleteSession: async (sessionId) => {
    const response = await api.delete(`/api/v1/chat/sessions/${sessionId}`);
    return response.data;
  },
  getMessages: async (sessionId) => {
    const response = await api.get(`/api/v1/chat/sessions/${sessionId}`);
    return response.data.messages || [];
  },
  sendMessage: async (sessionId, content) => {
    const response = await api.post(`/api/v1/chat/sessions/${sessionId}/messages`, { content });
    return response.data;
  },
};

export default api;
