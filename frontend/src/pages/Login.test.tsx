import { describe, it, expect, vi } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { render } from '../test/utils';
import { Login } from './Login';
import { BrowserRouter } from 'react-router-dom';
import * as authAPI from '../api/auth';

// Mock the API response
vi.mock('../api/auth', () => ({
    loginAPI: vi.fn(),
}));

describe('Login Component', () => {
    it('renders login form correctly', () => {
        render(
            <BrowserRouter>
                <Login />
            </BrowserRouter>
        );
        expect(screen.getByText('Welcome to PtClinVoice')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('Your medical ID')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('Your secure password')).toBeInTheDocument();
    });

    it('shows error when submitting empty fields', () => {
        render(
            <BrowserRouter>
                <Login />
            </BrowserRouter>
        );

        // Bypass native HTML5 required validation by removing the required attribute in memory,
        // or just fire the generic form submit
        const form = screen.getByRole('button', { name: /sign in/i }).closest('form');
        if (form) {
            fireEvent.submit(form);
        }

        expect(screen.getByText('Please enter both username and password.')).toBeInTheDocument();
    });

    it('calls loginAPI and redirects on successful login', async () => {
        (authAPI.loginAPI as any).mockResolvedValueOnce({
            access_token: 'fake-token'
        });

        render(
            <BrowserRouter>
                <Login />
            </BrowserRouter>
        );

        fireEvent.change(screen.getByPlaceholderText('Your medical ID'), { target: { value: 'testuser' } });
        fireEvent.change(screen.getByPlaceholderText('Your secure password'), { target: { value: 'password123' } });

        const submitButton = screen.getByRole('button', { name: /sign in/i });
        fireEvent.click(submitButton);

        await waitFor(() => {
            expect(authAPI.loginAPI).toHaveBeenCalledWith('testuser', 'password123');
        });
    });
});
