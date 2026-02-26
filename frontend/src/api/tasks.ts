import { apiClient } from './axios';

export interface TranscriptionTask {
    id: string;
    status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
    filename: string;
    created_at: string;
}

export const getTasks = async (): Promise<TranscriptionTask[]> => {
    const response = await apiClient.get('/tasks');
    return response.data;
};

export const getTask = async (id: string): Promise<TranscriptionTask> => {
    const response = await apiClient.get(`/tasks/${id}`);
    return response.data;
};

export const uploadAudio = async (file: File): Promise<{ task_id: string; status: string }> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};
