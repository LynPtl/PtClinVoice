import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { MainLayout } from '../layouts/MainLayout';
import { Grid, Paper, Title, Text, Button, Badge } from '@mantine/core';
import { getTask, type TranscriptionTask } from '../api/tasks';
import { useAuthStore } from '../store/useAuthStore';

export const Workspace: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { token } = useAuthStore();
    const [task, setTask] = useState<TranscriptionTask | null>(null);
    const [status, setStatus] = useState<string>('LOADING');
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!id) return;

        // Initial fetch
        getTask(id).then((t: TranscriptionTask) => {
            setTask(t);
            setStatus(t.status);
        }).catch((e: any) => {
            setError(e.response?.data?.detail || 'Failed to load task');
            setStatus('FAILED');
        });

        if (!token) return;

        // Open SSE connection
        const eventSource = new EventSource(`/api/stream/${id}?token=${token}`);

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                setStatus(data.status);
                if (data.status === 'COMPLETED' || data.status === 'FAILED') {
                    eventSource.close();
                }
            } catch (err) {
                console.error('SSE Error:', err);
            }
        };

        eventSource.onerror = () => {
            console.error('SSE connection lost');
            eventSource.close();
        };

        return () => {
            eventSource.close();
        };
    }, [id, token]);

    if (error) {
        return (
            <MainLayout>
                <Paper p="md" c="red">{error}</Paper>
            </MainLayout>
        );
    }

    return (
        <MainLayout>
            <div style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between' }}>
                <Title order={3}>Clinical Workspace</Title>
                <Button variant="default" onClick={() => navigate('/')}>Back to Dashboard</Button>
            </div>

            <div style={{ marginBottom: '1rem' }}>
                <Text fw={500}>Task ID: {task?.id || id}</Text>
                <Text>Status: <Badge color={status === 'COMPLETED' ? 'green' : status === 'FAILED' ? 'red' : 'blue'}>{status}</Badge></Text>
            </div>

            <Grid>
                <Grid.Col span={{ base: 12, md: 6 }}>
                    <Paper withBorder p="md" h="70vh" style={{ overflowY: 'auto' }}>
                        <Title order={5} mb="md">Original Transcript (Redacted)</Title>
                        <Text c="dimmed">
                            {status === 'COMPLETED' ? (
                                // In a real app, we would fetch the actual transcript here.
                                "[Mock Transcript Data]"
                            ) : (
                                "Waiting for transcription to complete..."
                            )}
                        </Text>
                    </Paper>
                </Grid.Col>

                <Grid.Col span={{ base: 12, md: 6 }}>
                    <Paper withBorder p="md" h="70vh" style={{ overflowY: 'auto' }}>
                        <Title order={5} mb="md">SOAP Notes</Title>
                        <Text c="dimmed">
                            {status === 'COMPLETED' ? (
                                // In a real app, we would fetch the SOAP note here.
                                "[Mock SOAP Note Data]"
                            ) : (
                                "Waiting for AI analysis..."
                            )}
                        </Text>
                    </Paper>
                </Grid.Col>
            </Grid>
        </MainLayout>
    );
};
