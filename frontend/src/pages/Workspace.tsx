import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { MainLayout } from '../layouts/MainLayout';
import { Grid, Paper, Title, Text, Button, Badge, Stack, Divider, Loader, Center, Group } from '@mantine/core';
import { getTask, type TranscriptionTask } from '../api/tasks';
import { useAuthStore } from '../store/useAuthStore';

export const Workspace: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { token } = useAuthStore();
    const [task, setTask] = useState<TranscriptionTask | null>(null);
    const [status, setStatus] = useState<string>('LOADING');
    const [error, setError] = useState<string | null>(null);

    const refreshData = useCallback(async () => {
        if (!id) return;
        try {
            const t = await getTask(id);
            setTask(t);
            setStatus(t.status);
        } catch (e: any) {
            setError(e.response?.data?.detail || 'Failed to load task');
            setStatus('FAILED');
        }
    }, [id]);

    useEffect(() => {
        refreshData();

        if (!id || !token) return;

        // Open SSE connection to listen for state changes
        const eventSource = new EventSource(`/api/stream/${id}?token=${token}`);

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                setStatus(data.status);

                // If the state moved to a final state, trigger a full data re-fetch to get transcript/soap
                if (data.status === 'COMPLETED' || data.status === 'FAILED') {
                    refreshData();
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
    }, [id, token, refreshData]);

    const renderSoapNote = () => {
        if (!task?.soap_note) return <Text c="dimmed">No analysis available yet.</Text>;

        try {
            const parsed = JSON.parse(task.soap_note);
            const soap = parsed.soap || {};

            return (
                <Stack gap="md">
                    <div>
                        <Text fw={700} size="sm" c="blue">SUBJECTIVE</Text>
                        <Text size="sm">{soap.subjective || 'N/A'}</Text>
                    </div>
                    <Divider />
                    <div>
                        <Text fw={700} size="sm" c="blue">OBJECTIVE</Text>
                        <Text size="sm">{soap.objective || 'N/A'}</Text>
                    </div>
                    <Divider />
                    <div>
                        <Text fw={700} size="sm" c="blue">ASSESSMENT</Text>
                        <Text size="sm">{soap.assessment || 'N/A'}</Text>
                    </div>
                    <Divider />
                    <div>
                        <Text fw={700} size="sm" c="blue">PLAN</Text>
                        <Text size="sm">{soap.plan || 'N/A'}</Text>
                    </div>
                </Stack>
            );
        } catch (e) {
            return <Text c="red">Failed to parse SOAP note data.</Text>;
        }
    };

    if (error) {
        return (
            <MainLayout>
                <Center h="50vh">
                    <Stack align="center">
                        <Text c="red" fw={500}>{error}</Text>
                        <Button onClick={() => navigate('/')}>Back to Dashboard</Button>
                    </Stack>
                </Center>
            </MainLayout>
        );
    }

    return (
        <MainLayout>
            <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <Title order={3}>Clinical Workspace</Title>
                    <Text size="xs" c="dimmed">Task ID: {id}</Text>
                </div>
                <Button variant="default" onClick={() => navigate('/')}>Back to Dashboard</Button>
            </div>

            <Paper withBorder p="xs" mb="lg" radius="md" style={{ backgroundColor: '#f8f9fa' }}>
                <Group>
                    <Text fw={500} size="sm">Current Pipeline Status:</Text>
                    <Badge
                        variant="filled"
                        color={status === 'COMPLETED' ? 'green' : status === 'FAILED' ? 'red' : 'blue'}
                    >
                        {status}
                    </Badge>
                    {(status !== 'COMPLETED' && status !== 'FAILED') && <Loader size="xs" />}
                </Group>
            </Paper>

            <Grid gutter="md">
                <Grid.Col span={{ base: 12, md: 6 }}>
                    <Paper withBorder p="md" radius="md" h="70vh" style={{ display: 'flex', flexDirection: 'column' }}>
                        <Title order={5} mb="md">
                            {status === 'COMPLETED' ? 'AI-Diarized Dialogue' : 'Original Transcript (Raw)'}
                        </Title>
                        <Divider mb="sm" />
                        <div style={{ flex: 1, overflowY: 'auto' }}>
                            {task?.transcript ? (
                                <Text size="sm" style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                                    {status === 'COMPLETED' && task.soap_note ? (
                                        (() => {
                                            try {
                                                const parsed = JSON.parse(task.soap_note);
                                                return parsed.dialogue || task.transcript;
                                            } catch (e) {
                                                return task.transcript;
                                            }
                                        })()
                                    ) : (
                                        task.transcript
                                    )}
                                </Text>
                            ) : (
                                <Center h="100%">
                                    <Stack align="center" gap="xs">
                                        <Text c="dimmed" size="sm">
                                            {status === 'FAILED' ? 'Transcription failed.' : 'Waiting for transcription...'}
                                        </Text>
                                        {status !== 'FAILED' && <Loader size="sm" variant="dots" />}
                                    </Stack>
                                </Center>
                            )}
                        </div>
                    </Paper>
                </Grid.Col>

                <Grid.Col span={{ base: 12, md: 6 }}>
                    <Paper withBorder p="md" radius="md" h="70vh" style={{ display: 'flex', flexDirection: 'column' }}>
                        <Title order={5} mb="md">AI-Generated SOAP Analysis</Title>
                        <Divider mb="sm" />
                        <div style={{ flex: 1, overflowY: 'auto' }}>
                            {status === 'COMPLETED' ? renderSoapNote() : (
                                <Center h="100%">
                                    <Stack align="center" gap="xs">
                                        <Text c="dimmed" size="sm">
                                            {status === 'FAILED' ? 'Analysis failed.' : 'Waiting for AI processing...'}
                                        </Text>
                                        {status !== 'FAILED' && <Loader size="sm" variant="bars" />}
                                    </Stack>
                                </Center>
                            )}
                        </div>
                    </Paper>
                </Grid.Col>
            </Grid>
        </MainLayout>
    );
};
