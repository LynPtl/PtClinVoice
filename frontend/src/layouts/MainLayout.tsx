import React from 'react';
import { AppShell, Burger, Group, Title, Button } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { useAuthStore } from '../store/useAuthStore';
import { IconLogout, IconStethoscope } from '@tabler/icons-react';

interface MainLayoutProps {
    children: React.ReactNode;
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
    const [opened, { toggle }] = useDisclosure();
    const { logout, user } = useAuthStore();

    return (
        <AppShell
            header={{ height: 60 }}
            navbar={{
                width: 300,
                breakpoint: 'sm',
                collapsed: { mobile: !opened },
            }}
            padding="md"
        >
            <AppShell.Header>
                <Group h="100%" px="md" justify="space-between">
                    <Group>
                        <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
                        <IconStethoscope size={28} color="#228be6" />
                        <Title order={3} c="blue">PtClinVoice Dashboard</Title>
                    </Group>
                    <Group>
                        <div style={{ fontSize: '14px', fontWeight: 500 }}>Dr. {user?.username}</div>
                        <Button variant="subtle" color="red" leftSection={<IconLogout size={16} />} onClick={logout}>
                            Logout
                        </Button>
                    </Group>
                </Group>
            </AppShell.Header>

            <AppShell.Navbar p="md">
                <div>WIP: Navigation Links</div>
            </AppShell.Navbar>

            <AppShell.Main>{children}</AppShell.Main>
        </AppShell>
    );
};
