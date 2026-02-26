import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { render } from '../test/utils';
import { Dashboard } from './Dashboard';
import { useAuthStore } from '../store/useAuthStore';
import * as tasksAPI from '../api/tasks';

// Mock the API response
vi.mock('../api/tasks', () => ({
    getTasks: vi.fn(),
    uploadAudio: vi.fn(),
}));

describe('Dashboard Component', () => {
    beforeEach(() => {
        // Simulate logged-in user
        useAuthStore.setState({
            token: 'fake-jwt',
            user: { id: 1, username: 'dr_tester' },
            isAuthenticated: true
        });
    });

    it('renders dashboard layout and active user', async () => {
        (tasksAPI.getTasks as any).mockResolvedValueOnce([]);

        render(<Dashboard />);

        expect(screen.getByText('PtClinVoice Dashboard')).toBeInTheDocument();
        expect(screen.getByText('Dr. dr_tester')).toBeInTheDocument();
        expect(screen.getByText('New Transcription')).toBeInTheDocument();

        await waitFor(() => {
            expect(tasksAPI.getTasks).toHaveBeenCalled();
        });
    });

    it('renders task list with correct status badges', async () => {
        const mockTasks = [
            { id: '1111-2222', filename: 'audio1.wav', status: 'COMPLETED', created_at: '2023-01-01' },
            { id: '3333-4444', filename: 'audio2.mp3', status: 'PENDING', created_at: '2023-01-02' }
        ];

        (tasksAPI.getTasks as any).mockResolvedValueOnce(mockTasks);

        render(<Dashboard />);

        await waitFor(() => {
            expect(screen.getByText('1111-222', { exact: false })).toBeInTheDocument();
            expect(screen.getByText('audio1.wav')).toBeInTheDocument();
            expect(screen.getByText('Completed')).toBeInTheDocument();

            expect(screen.getByText('3333-444', { exact: false })).toBeInTheDocument();
            expect(screen.getByText('Pending')).toBeInTheDocument();
        });
    });
});
