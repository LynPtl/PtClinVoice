import { apiClient } from './axios';

export interface TranscriptionTask {
    id: string;
    status: 'PENDING' | 'TRANSCRIBING' | 'ANALYZING' | 'COMPLETED' | 'FAILED';
    filename?: string;
    patient_name?: string;
    transcript?: string;
    soap_note?: string;
    error_message?: string;
    created_at: string;
}

export const getTasks = async (): Promise<TranscriptionTask[]> => {
    // SRE Note: Append timestamp to aggressively bust browser cache, ensuring we don't 
    // load stale empty task lists when navigating back from Workspace.
    const response = await apiClient.get(`/tasks?t=${Date.now()}`);
    return response.data;
};

export const getTask = async (id: string): Promise<TranscriptionTask> => {
    const response = await apiClient.get(`/tasks/${id}`);
    return response.data;
};

export const uploadAudio = async (file: File, language: string = 'auto', patientName: string = ''): Promise<{ task_id: string; status: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('language', language);
    formData.append('patient_name', patientName);

    const response = await apiClient.post('/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};

export const deleteTask = async (id: string): Promise<{ message: string }> => {
    const response = await apiClient.delete(`/tasks/${id}`);
    return response.data;
};
