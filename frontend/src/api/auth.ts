import { apiClient } from './axios';

export const loginAPI = async (username: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    // FastAPI OAuth2PasswordRequestForm expects x-www-form-urlencoded
    const response = await apiClient.post('/auth/login', formData, {
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    });
    return response.data;
};

export const registerAPI = async (username: string, password: string) => {
    const response = await apiClient.post('/auth/register', { username, password });
    return response.data;
};
