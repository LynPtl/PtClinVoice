import React, { useState } from 'react';
import { MainLayout } from '../layouts/MainLayout';
import { UploadDropzone } from '../components/UploadDropzone';
import { TaskList } from '../components/TaskList';
import { Stack, Title, Text } from '@mantine/core';

export const Dashboard: React.FC = () => {
    const [refreshTasks, setRefreshTasks] = useState(0);

    const handleUploadSuccess = () => {
        // Trigger task list refresh
        setRefreshTasks((prev) => prev + 1);
    };

    return (
        <MainLayout>
            <Stack gap="lg" align="stretch" justify="center" p="md">
                <div>
                    <Title order={2}>New Transcription</Title>
                    <Text c="dimmed" size="sm" mb="md">Upload a medical audio file to generate SOAP notes securely.</Text>
                    <UploadDropzone onUploadSuccess={handleUploadSuccess} />
                </div>

                <TaskList refreshTrigger={refreshTasks} />
            </Stack>
        </MainLayout>
    );
};
