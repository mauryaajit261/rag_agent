import { supabase } from './supabaseClient';

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';
// Token for the external image-analysis API, loaded from frontend/.env.local (gitignored).
// NOTE: VITE_* values are still embedded in the built client bundle. For true secrecy,
// proxy the image-analysis call through the FastAPI backend (see the secure-backend skill).
const IMAGE_API_TOKEN = import.meta.env.VITE_IMAGE_API_TOKEN;

// API Client
class APIClient {
    constructor(baseURL) {
        this.baseURL = baseURL;
    }

    async getAuthToken() {
        const { data } = await supabase.auth.getSession();
        return data.session?.access_token || null;
    }

    async request(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `${this.baseURL}${endpoint}`;

        // Use custom token if provided, otherwise get session token
        const token = options.customToken || await this.getAuthToken();

        try {
            const response = await fetch(url, {
                ...options,
                headers: {
                    ...options.headers,
                    ...(token ? { Authorization: `Bearer ${token}` } : {})
                }
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ error: 'Request failed' }));
                throw new Error(error.detail || error.error || 'Request failed');
            }

            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    // Health Check
    async healthCheck() {
        return this.request('/health');
    }

    // Upload Document
    async uploadDocument(file, onProgress) {
        const formData = new FormData();
        formData.append('file', file);

        return this.request('/upload', {
            method: 'POST',
            body: formData,
        });
    }

    // Delete Document
    async deleteDocument(docId) {
        return this.request(`/documents/${docId}`, {
            method: 'DELETE',
        });
    }

    // Query Knowledge Base (non-streaming fallback)
    async query(queryText, includeSource = true, sessionId = null, sourceType = 'all') {
        return this.request('/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: queryText,
                include_sources: includeSource,
                session_id: sessionId,
                source_type: sourceType,
            }),
        });
    }

    // Streaming Query — returns an SSE reader for word-by-word output
    // NOTE: For the chat architectural rewrite, the backend uses /api/chat/message with memory now.
    // The previous endpoints exist for backwards-compatibility testing.
    async queryStream(queryText, { includeSource = true, sessionId = null, sourceType = 'all', onToken, onDone, onError }) {
        const url = `${this.baseURL}/query/stream`;
        const token = await this.getAuthToken();

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {})
                },
                body: JSON.stringify({
                    query: queryText,
                    include_sources: includeSource,
                    session_id: sessionId,
                    source_type: sourceType,
                }),
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ error: 'Stream request failed' }));
                throw new Error(error.detail || error.error || 'Stream request failed');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // Parse SSE events from buffer
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Keep incomplete line in buffer

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));

                            if (data.type === 'token' && onToken) {
                                onToken(data.content);
                            } else if (data.type === 'done' && onDone) {
                                onDone(data);
                            } else if (data.type === 'error' && onError) {
                                onError(new Error(data.content));
                            }
                        } catch (parseErr) {
                            // Skip malformed JSON lines
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Stream Error:', error);
            if (onError) onError(error);
        }
    }

    // Connect Database
    async connectDatabase(config) {
        return this.request('/database/connect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(config),
        });
    }

    async deleteDatabase(dbId) {
        return this.request(`/database/${dbId}`, { method: 'DELETE' });
    }

    // List Documents
    async listDocuments() {
        return this.request('/documents');
    }

    // List Databases
    async listDatabases() {
        return this.request('/databases');
    }

    // ── NATIVE SECURE CHAT ENDPOINTS ── //

    async createNewChat(title) {
        return this.request('/api/chat/new', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title }),
        });
    }

    async listChats() {
        return this.request('/api/chat/list', { method: 'GET' });
    }



    async getChatHistory(chatId) {
        return this.request(`/api/chat/${chatId}/history`, { method: 'GET' });
    }

    // Natively interacts with Memory Context RAG pipeline
    async sendChatMessage(chatId, content, sourceType = 'all') {
        return this.request('/api/chat/message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: chatId, content, source_type: sourceType }),
        });
    }

    async deleteChat(chatId) {
        return this.request(`/api/chat/${chatId}`, { method: 'DELETE' });
    }

    // ── External Image Analysis ── //
    async analyzeImage(imageUrl, file) {
        const formData = new FormData();
        formData.append('file', file);

        return this.request(imageUrl, {
            method: 'POST',
            body: formData,
            customToken: IMAGE_API_TOKEN
        });
    }

    /**
     * Archive image analysis results via FastAPI backend.
     * Uses service role key on the backend to bypass Supabase RLS.
     */
    async archiveAnalysis(chatId, file, analysisData) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('analysis_data', JSON.stringify(analysisData));

        return this.request(`/api/chat/archive-analysis?chat_id=${chatId}`, {
            method: 'POST',
            body: formData,
        });
    }
}

export const api = new APIClient(API_BASE_URL);
export default api;
