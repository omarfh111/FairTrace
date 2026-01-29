import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const checkHealth = async () => {
    try {
        const response = await api.get('/health');
        return response.data;
    } catch (error) {
        console.error('Health check failed:', error);
        throw error;
    }
};

export const submitDecision = async (data: any) => {
    const response = await api.post('/decisions', data);
    return response.data;
};

export const getDecision = async (id: string) => {
    const response = await api.get(`/decisions/${id}`);
    return response.data;
};

export const getAdvisorAnalysis = async (decisionId: string) => {
    const response = await api.get(`/decisions/${decisionId}/advisor`);
    return response.data;
};

export const getNarrativeAnalysis = async (decisionId: string) => {
    const response = await api.get(`/decisions/${decisionId}/narrative`);
    return response.data;
};

export const getComparatorAnalysis = async (decisionId: string) => {
    const response = await api.get(`/decisions/${decisionId}/comparator`);
    return response.data;
};

export const getScenarioAnalysis = async (decisionId: string, scenarios?: any) => {
    const response = await api.post(`/decisions/${decisionId}/scenario`, { custom_scenarios: scenarios });
    return response.data;
};

export const getChatSuggestions = async (conversationId?: string) => {
    const params = conversationId ? { conversation_id: conversationId } : {};
    const response = await api.get('/chat/regulation/suggestions', { params });
    return response.data;
};

export const clearChatHistory = async (conversationId: string) => {
    const response = await api.delete(`/chat/regulation/${conversationId}`);
    return response.data;
};


export interface StreamingCallbacks {
    onStatus: (status: string, message: string) => void;
    onToken: (token: string) => void;
    onCitation: (citation: any) => void;
    onDone: (metadata: any) => void;
    onError: (error: string) => void;
}

export const sendStreamingChatMessage = async (
    message: string,
    conversationId: string | null,
    callbacks: StreamingCallbacks
) => {
    try {
        const response = await fetch(`${API_BASE_URL}/chat/regulation/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message, conversation_id: conversationId }),
        });

        if (!response.ok) {
            throw new Error('Chat request failed');
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) return;

        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            buffer += chunk;

            const parts = buffer.split('\n\n');
            buffer = parts.pop() || ''; // Keep the last incomplete part

            for (const part of parts) {
                if (!part.trim()) continue;

                const lines = part.split('\n');
                let type = '';
                let data: any = null;

                for (const line of lines) {
                    if (line.startsWith('event: ')) {
                        type = line.substring(7).trim();
                    } else if (line.startsWith('data: ')) {
                        try {
                            data = JSON.parse(line.substring(6));
                        } catch (e) {
                            console.error('Failed to parse data JSON', e);
                        }
                    }
                }

                if (type && data !== null) {
                    switch (type) {
                        case 'status':
                            callbacks.onStatus(data.status, data.message);
                            break;
                        case 'token':
                            callbacks.onToken(data.text);
                            break;
                        case 'citation':
                            callbacks.onCitation(data);
                            break;
                        case 'done':
                            callbacks.onDone(data);
                            break;
                        case 'error':
                            callbacks.onError(data.error);
                            break;
                    }
                } else if (type === 'error') {
                    callbacks.onError('Unknown stream error');
                }
            }
        }
    } catch (error: any) {
        callbacks.onError(error.message || 'Network error');
    }
};

