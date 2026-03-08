import React, { useState } from 'react';
import { TextInput, PasswordInput, Button, Paper, Title, Container, Text, Alert, Anchor } from '@mantine/core';
import { useNavigate, useLocation } from 'react-router-dom';
import { loginAPI } from '../api/auth';
import { useAuthStore } from '../store/useAuthStore';
import { IconAlertCircle } from '@tabler/icons-react';

export const Login: React.FC = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    const location = useLocation();
    const { login } = useAuthStore();

    const from = location.state?.from?.pathname || '/';

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!username || !password) {
            setError('Please enter both username and password.');
            return;
        }

        try {
            setLoading(true);
            setError(null);
            const data = await loginAPI(username, password);
            login(data.access_token, { id: 1, username: username }); // Simplified user payload
            navigate(from, { replace: true });
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Login failed. Please check your credentials.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Container size={420} my={40}>
            <Title ta="center" fw={900}>
                Welcome to PtClinVoice
            </Title>
            <Text c="dimmed" size="sm" ta="center" mt={5}>
                Secure Clinical Transcription & Analysis
            </Text>

            <Paper withBorder shadow="md" p={30} mt={30} radius="md">
                {error && (
                    <Alert icon={<IconAlertCircle size={16} />} title="Authentication Error" color="red" variant="filled" mb="md">
                        {error}
                    </Alert>
                )}
                <form onSubmit={handleSubmit}>
                    <TextInput
                        label="Username"
                        placeholder="Your medical ID"
                        value={username}
                        onChange={(event) => setUsername(event.currentTarget.value)}
                    />
                    <PasswordInput
                        label="Password"
                        placeholder="Your secure password"
                        mt="md"
                        value={password}
                        onChange={(event) => setPassword(event.currentTarget.value)}
                    />
                    <Button fullWidth mt="xl" type="submit" loading={loading} variant="gradient" gradient={{ from: 'indigo', to: 'cyan' }}>
                        Sign in
                    </Button>
                </form>
                <Text ta="center" mt="md" size="sm">
                    Don&apos;t have an account?{' '}
                    <Anchor component="button" type="button" onClick={() => navigate('/register')}>
                        Register here
                    </Anchor>
                </Text>
            </Paper>
        </Container>
    );
};
