import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Badge, Paper, Title, ActionIcon, Group, Modal, Button, Text } from '@mantine/core';
import { IconRefresh, IconEye, IconTrash } from '@tabler/icons-react';
import { getTasks, deleteTask, type TranscriptionTask } from '../api/tasks';
import { useAuthStore } from '../store/useAuthStore';

export const TaskList: React.FC<{ refreshTrigger: number }> = ({ refreshTrigger }) => {
    const navigate = useNavigate();
    const token = useAuthStore((state: any) => state.token);
    const [tasks, setTasks] = useState<TranscriptionTask[]>([]);
    const [loading, setLoading] = useState(true);
    const [deleteModalOpen, setDeleteModalOpen] = useState(false);
    const [taskToDelete, setTaskToDelete] = useState<TranscriptionTask | null>(null);
    const [deleting, setDeleting] = useState(false);
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
            case 'TRANSCRIBING': return <Badge color="blue" variant="light">Transcribing</Badge>;
            case 'ANALYZING': return <Badge color="violet" variant="light">Analyzing</Badge>;
            case 'COMPLETED': return <Badge color="green">Completed</Badge>;
            case 'FAILED': return <Badge color="red">Failed</Badge>;
            default: return <Badge color="gray">{status}</Badge>;
        }
    };

    const formatDate = (dateStr: string) => {
        try {
            const d = new Date(dateStr);
            return d.toLocaleString('en-AU', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
        } catch {
            return dateStr;
        }
    };

    const getDisplayName = (task: TranscriptionTask) => {
        if (task.patient_name) return task.patient_name;
        if (task.filename) return task.filename;
        return 'Untitled';
    };

    const handleDeleteClick = (task: TranscriptionTask) => {
        setTaskToDelete(task);
        setDeleteModalOpen(true);
    };

    const confirmDelete = async () => {
        if (!taskToDelete) return;
        setDeleting(true);
        try {
            await deleteTask(taskToDelete.id);
            setTasks((prev) => prev.filter((t) => t.id !== taskToDelete.id));
            setDeleteModalOpen(false);
            setTaskToDelete(null);
        } catch (err) {
            console.error('Delete failed', err);
            alert('Failed to delete task.');
        } finally {
            setDeleting(false);
        }
    };

    return (
        <>
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
                            <Table.Th>Patient</Table.Th>
                            <Table.Th>Created</Table.Th>
                            <Table.Th>Status</Table.Th>
                            <Table.Th>Actions</Table.Th>
                        </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                        {tasks.map((task: TranscriptionTask) => (
                            <Table.Tr key={task.id}>
                                <Table.Td fw={500}>{getDisplayName(task)}</Table.Td>
                                <Table.Td c="dimmed">{formatDate(task.created_at)}</Table.Td>
                                <Table.Td>{getStatusBadge(task.status)}</Table.Td>
                                <Table.Td>
                                    <Group gap="xs">
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
                                        <ActionIcon
                                            variant="light"
                                            color="red"
                                            onClick={() => handleDeleteClick(task)}
                                            title="Delete Task"
                                        >
                                            <IconTrash size={16} />
                                        </ActionIcon>
                                    </Group>
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

            <Modal opened={deleteModalOpen} onClose={() => setDeleteModalOpen(false)} title="Confirm Deletion" centered>
                <Text size="sm" mb="lg">
                    Are you sure you want to permanently delete the record for <b>{taskToDelete ? getDisplayName(taskToDelete) : ''}</b>? This action cannot be undone.
                </Text>
                <Group justify="flex-end">
                    <Button variant="default" onClick={() => setDeleteModalOpen(false)}>Cancel</Button>
                    <Button color="red" loading={deleting} onClick={confirmDelete}>Delete</Button>
                </Group>
            </Modal>
        </>
    );
};
