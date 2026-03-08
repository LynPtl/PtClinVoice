import React, { useState, useRef } from 'react';
import { Button, Group, Stack, Text, Select, Paper, TextInput } from '@mantine/core';
import { IconMicrophone, IconPlayerStop, IconUpload } from '@tabler/icons-react';
import { uploadAudio } from '../api/tasks';

export const AudioRecorder: React.FC<{ onUploadSuccess: () => void }> = ({ onUploadSuccess }) => {
    const [isRecording, setIsRecording] = useState(false);
    const [recordingTime, setRecordingTime] = useState(0);
    const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
    const [language, setLanguage] = useState<string>('auto');
    const [patientName, setPatientName] = useState('');
    const [isUploading, setIsUploading] = useState(false);

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const timerRef = useRef<number | null>(null);
    const chunksRef = useRef<Blob[]>([]);

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    noiseSuppression: true,
                    echoCancellation: true,
                    autoGainControl: true
                }
            });
            streamRef.current = stream;

            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;
            chunksRef.current = [];

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    chunksRef.current.push(e.data);
                }
            };

            mediaRecorder.onstop = () => {
                const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
                setAudioBlob(blob);
            };

            mediaRecorder.start();
            setIsRecording(true);
            setRecordingTime(0);

            timerRef.current = window.setInterval(() => {
                setRecordingTime((prev) => prev + 1);
            }, 1000);

        } catch (err) {
            console.error('Error accessing microphone', err);
            alert('Could not access microphone. Please check your browser permissions.');
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
        }
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
        }
        if (timerRef.current) {
            clearInterval(timerRef.current);
            timerRef.current = null;
        }
    };

    const handleUpload = async () => {
        if (!audioBlob) return;
        setIsUploading(true);
        try {
            // Convert Blob to File, standardizing as .webm
            const file = new File([audioBlob], `recording-${Date.now()}.webm`, { type: 'audio/webm' });
            await uploadAudio(file, language, patientName);
            setAudioBlob(null);
            setRecordingTime(0);
            setPatientName('');
            onUploadSuccess();
        } catch (err) {
            console.error('Upload failed', err);
            alert('Upload failed. Please check console.');
        } finally {
            setIsUploading(false);
        }
    };

    const formatTime = (seconds: number) => {
        const m = Math.floor(seconds / 60).toString().padStart(2, '0');
        const s = (seconds % 60).toString().padStart(2, '0');
        return `${m}:${s}`;
    };

    return (
        <Paper withBorder p="md" radius="md">
            <Stack gap="md">
                <Group justify="space-between" align="flex-start">
                    <Group align="center">
                        {!isRecording ? (
                            <Button
                                leftSection={<IconMicrophone size={16} />}
                                color="red"
                                variant="light"
                                onClick={startRecording}
                                disabled={isUploading || audioBlob !== null}
                            >
                                Record Audio
                            </Button>
                        ) : (
                            <Button
                                leftSection={<IconPlayerStop size={16} />}
                                color="gray"
                                onClick={stopRecording}
                            >
                                Stop ({formatTime(recordingTime)})
                            </Button>
                        )}
                        {audioBlob && !isRecording && (
                            <Text size="sm" fw={500} c="green">Recording Ready ({formatTime(recordingTime)})</Text>
                        )}
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
                    {audioBlob && (
                        <Button
                            variant="light"
                            color="gray"
                            onClick={() => { setAudioBlob(null); setRecordingTime(0); }}
                            disabled={isUploading}
                        >
                            Discard
                        </Button>
                    )}
                    <Button
                        loading={isUploading}
                        onClick={handleUpload}
                        disabled={!audioBlob}
                        color="blue"
                        leftSection={<IconUpload size={16} />}
                    >
                        Upload & Transcribe
                    </Button>
                </Group>
            </Stack>
        </Paper>
    );
};
