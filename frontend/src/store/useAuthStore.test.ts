import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from '../store/useAuthStore';

describe('useAuthStore', () => {
    beforeEach(() => {
        // Clear the store and localStorage before each test
        localStorage.clear();
        useAuthStore.setState({ token: null, user: null, isAuthenticated: false });
    });

    it('should initialize with default empty state when localStorage is clean', () => {
        const state = useAuthStore.getState();
        expect(state.token).toBeNull();
        expect(state.user).toBeNull();
        expect(state.isAuthenticated).toBe(false);
    });

    it('should securely register token and user profile on successful login', () => {
        const mockToken = 'mock.jwt.token';
        const mockUser = { id: 1, username: 'dr_bob' };

        useAuthStore.getState().login(mockToken, mockUser);

        const state = useAuthStore.getState();
        expect(state.token).toBe(mockToken);
        expect(state.user).toEqual(mockUser);
        expect(state.isAuthenticated).toBe(true);

        // Verify side-effects
        expect(localStorage.getItem('token')).toBe(mockToken);
        expect(JSON.parse(localStorage.getItem('user')!)).toEqual(mockUser);
    });

    it('should purge all local session data upon logout', () => {
        const mockToken = 'mock.jwt.token';
        const mockUser = { id: 1, username: 'dr_bob' };

        useAuthStore.getState().login(mockToken, mockUser);
        useAuthStore.getState().logout();

        const state = useAuthStore.getState();
        expect(state.token).toBeNull();
        expect(state.user).toBeNull();
        expect(state.isAuthenticated).toBe(false);

        // Verify side-effects
        expect(localStorage.getItem('token')).toBeNull();
        expect(localStorage.getItem('user')).toBeNull();
    });
});
