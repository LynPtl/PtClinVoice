import React, { useState } from 'react';
import { TextInput, PasswordInput, Button, Paper, Title, Container, Text, Alert, Anchor } from '@mantine/core';
import { useNavigate } from 'react-router-dom';
import { registerAPI } from '../api/auth';
import { IconAlertCircle, IconCheck } from '@tabler/icons-react';

export const Register: React.FC = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!username || username.length < 3) {
            setError('Username must be at least 3 characters.');
            return;
        }
        if (!password || password.length < 6) {
            setError('Password must be at least 6 characters.');
            return;
        }
        if (password !== confirmPassword) {
            setError('Passwords do not match.');
            return;
        }

        try {
            setLoading(true);
            await registerAPI(username, password);
            setSuccess(true);
            setTimeout(() => navigate('/login'), 2000);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Registration failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Container size={420} my={40}>
            <Title ta="center" fw={900}>
                Create Account
            </Title>
            <Text c="dimmed" size="sm" ta="center" mt={5}>
                Join PtClinVoice Clinical Platform
            </Text>

            <Paper withBorder shadow="md" p={30} mt={30} radius="md">
                {error && (
                    <Alert icon={<IconAlertCircle size={16} />} title="Registration Error" color="red" variant="filled" mb="md">
                        {error}
                    </Alert>
                )}
                {success && (
                    <Alert icon={<IconCheck size={16} />} title="Success!" color="green" variant="filled" mb="md">
                        Account created! Redirecting to login...
                    </Alert>
                )}
                <form onSubmit={handleSubmit}>
                    <TextInput
                        label="Username"
                        placeholder="Choose a medical ID"
                        value={username}
                        onChange={(event) => setUsername(event.currentTarget.value)}
                        disabled={success}
                    />
                    <PasswordInput
                        label="Password"
                        placeholder="At least 6 characters"
                        mt="md"
                        value={password}
                        onChange={(event) => setPassword(event.currentTarget.value)}
                        disabled={success}
                    />
                    <PasswordInput
                        label="Confirm Password"
                        placeholder="Re-enter your password"
                        mt="md"
                        value={confirmPassword}
                        onChange={(event) => setConfirmPassword(event.currentTarget.value)}
                        disabled={success}
                    />
                    <Button fullWidth mt="xl" type="submit" loading={loading} disabled={success} variant="gradient" gradient={{ from: 'teal', to: 'cyan' }}>
                        Create Account
                    </Button>
                </form>
                <Text ta="center" mt="md" size="sm">
                    Already have an account?{' '}
                    <Anchor component="button" type="button" onClick={() => navigate('/login')}>
                        Sign in
                    </Anchor>
                </Text>
            </Paper>
        </Container>
    );
};
