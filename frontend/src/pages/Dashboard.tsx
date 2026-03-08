import React, { useState } from 'react';
import { MainLayout } from '../layouts/MainLayout';
import { UploadDropzone } from '../components/UploadDropzone';
import { AudioRecorder } from '../components/AudioRecorder';
import { TaskList } from '../components/TaskList';
import { Stack, Title, Text, Tabs } from '@mantine/core';
import { IconUpload, IconMicrophone } from '@tabler/icons-react';

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
                    <Text c="dimmed" size="sm" mb="md">Provide medical audio to securely generate SOAP notes.</Text>

                    <Tabs defaultValue="upload" variant="outline">
                        <Tabs.List mb="md">
                            <Tabs.Tab value="upload" leftSection={<IconUpload size={14} />}>
                                Upload File
                            </Tabs.Tab>
                            <Tabs.Tab value="record" leftSection={<IconMicrophone size={14} />}>
                                Record Audio
                            </Tabs.Tab>
                        </Tabs.List>

                        <Tabs.Panel value="upload">
                            <UploadDropzone onUploadSuccess={handleUploadSuccess} />
                        </Tabs.Panel>

                        <Tabs.Panel value="record">
                            <AudioRecorder onUploadSuccess={handleUploadSuccess} />
                        </Tabs.Panel>
                    </Tabs>
                </div>

                <TaskList refreshTrigger={refreshTasks} />
            </Stack>
        </MainLayout>
    );
};
