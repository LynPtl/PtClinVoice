import React, { useState } from 'react';
import { IconUpload } from '@tabler/icons-react';
import { Text, Group, Button, Paper, Select, Stack, TextInput } from '@mantine/core';

export const UploadDropzone: React.FC<{ onUploadSuccess: () => void }> = ({ onUploadSuccess }) => {
    const [file, setFile] = useState<File | null>(null);
    const [language, setLanguage] = useState<string>('auto');
    const [patientName, setPatientName] = useState('');
    const [loading, setLoading] = useState(false);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            setFile(e.target.files[0]);
        }
    };

    const handleUpload = async () => {
        if (!file) return;
        setLoading(true);
        try {
            const { uploadAudio } = await import('../api/tasks');
            await uploadAudio(file, language, patientName);
            setFile(null);
            setPatientName('');
            onUploadSuccess();
        } catch (error) {
            console.error('Upload failed', error);
            alert('Upload failed. Please check console.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Paper withBorder p="md" radius="md">
            <Stack gap="md">
                <Group justify="space-between" align="flex-start">
                    <Group align="center">
                        <input
                            type="file"
                            accept="audio/*"
                            onChange={handleFileChange}
                            style={{ display: 'none' }}
                            id="audio-upload-input"
                        />
                        <Button
                            component="label"
                            htmlFor="audio-upload-input"
                            variant="light"
                            leftSection={<IconUpload size={16} />}
                        >
                            Select Audio File
                        </Button>
                        {file && <Text size="sm" fw={500}>{file.name}</Text>}
                    </Group>
                    <Select
                        label="Source Language"
                        placeholder="Select language"
                        value={language}
                        onChange={(value) => setLanguage(value || 'auto')}
                        data={[
                            { value: 'auto', label: 'Auto-Detect (Default)' },
                            { value: 'en', label: 'English' },
                            { value: 'ar', label: 'Arabic' },
                        ]}
                        w={200}
                    />
                </Group>

                <TextInput
                    label="Patient Name (Optional)"
                    placeholder="e.g. John Doe or MRN-12345"
                    value={patientName}
                    onChange={(e) => setPatientName(e.currentTarget.value)}
                />

                <Group justify="flex-end">
                    <Button loading={loading} onClick={handleUpload} disabled={!file} color="blue">
                        Start Transcription
                    </Button>
                </Group>
            </Stack>
        </Paper>
    );
};
