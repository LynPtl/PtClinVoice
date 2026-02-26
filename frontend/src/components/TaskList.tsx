import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Badge, Paper, Title, ActionIcon, Group } from '@mantine/core';
import { IconRefresh, IconEye } from '@tabler/icons-react';
import { getTasks, type TranscriptionTask } from '../api/tasks';
import { useAuthStore } from '../store/useAuthStore';

export const TaskList: React.FC<{ refreshTrigger: number }> = ({ refreshTrigger }) => {
    const navigate = useNavigate();
    const token = useAuthStore((state: any) => state.token);
    const [tasks, setTasks] = useState<TranscriptionTask[]>([]);
    const [loading, setLoading] = useState(true);
    const eventSourcesRef = useRef<{ [key: string]: EventSource }>({});

    const fetchTasks = async () => {
        setLoading(true);
        try {
            const data = await getTasks();
            setTasks(data);
        } catch (error) {
            console.error('Failed to fetch tasks', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTasks();
    }, [refreshTrigger]);

    useEffect(() => {
        // Cleanup all SSE connections on component unmount
        return () => {
            Object.values(eventSourcesRef.current).forEach((source: any) => source.close());
            eventSourcesRef.current = {};
        };
    }, []);

    useEffect(() => {
        if (!token) return;

        tasks.forEach(task => {
            if ((task.status === 'PENDING' || task.status === 'TRANSCRIBING' || task.status === 'ANALYZING') && !eventSourcesRef.current[task.id]) {
                const source = new EventSource(`/api/stream/${task.id}?token=${token}`);
                eventSourcesRef.current[task.id] = source;

                source.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        setTasks((prevTasks) =>
                            prevTasks.map((t) => (t.id === data.task_id ? { ...t, status: data.status } : t))
                        );

                        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
                            source.close();
                            delete eventSourcesRef.current[task.id];
                        }
                    } catch (e) {
                        console.error('SSE parsing error', e);
                    }
                };

                source.onerror = () => {
                    source.close();
                    delete eventSourcesRef.current[task.id];
                };
            }
        });
    }, [tasks, token]);

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'PENDING': return <Badge color="gray">Pending</Badge>;
            case 'PROCESSING': return <Badge color="blue" variant="light">Processing</Badge>;
            case 'COMPLETED': return <Badge color="green">Completed</Badge>;
            case 'FAILED': return <Badge color="red">Failed</Badge>;
            default: return <Badge color="gray">{status}</Badge>;
        }
    };

    return (
        <Paper withBorder p="md" radius="md">
            <Group justify="space-between" mb="md">
                <Title order={4}>Transcription History</Title>
                <ActionIcon variant="light" onClick={fetchTasks} loading={loading}>
                    <IconRefresh size={16} />
                </ActionIcon>
            </Group>

            <Table highlightOnHover>
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th>Task ID</Table.Th>
                        <Table.Th>Filename</Table.Th>
                        <Table.Th>Status</Table.Th>
                        <Table.Th>Actions</Table.Th>
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                    {tasks.map((task: TranscriptionTask) => (
                        <Table.Tr key={task.id}>
                            <Table.Td>{task.id.slice(0, 8)}...</Table.Td>
                            <Table.Td>{task.filename || 'Unknown'}</Table.Td>
                            <Table.Td>{getStatusBadge(task.status)}</Table.Td>
                            <Table.Td>
                                {task.status === 'COMPLETED' && (
                                    <ActionIcon
                                        variant="light"
                                        color="blue"
                                        onClick={() => navigate(`/task/${task.id}`)}
                                        title="View Workspace"
                                    >
                                        <IconEye size={16} />
                                    </ActionIcon>
                                )}
                            </Table.Td>
                        </Table.Tr>
                    ))}
                    {tasks.length === 0 && !loading && (
                        <Table.Tr>
                            <Table.Td colSpan={4} style={{ textAlign: 'center' }}>No tasks found.</Table.Td>
                        </Table.Tr>
                    )}
                </Table.Tbody>
            </Table>
        </Paper>
    );
};
