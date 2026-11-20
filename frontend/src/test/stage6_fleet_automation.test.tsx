/**
 * ServicePulse - Stage 6 RMM Fleet Automation Vitest Suite
 * Tests Subnet Auto-Discovery Scanner, 1-Click Agent Bootstrap Deployer,
 * and Remote Task & Service Manager in DeviceDetailModal.
 *
 * Author: Muhammadyusuf Usmonov
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SubnetDiscoveryModal } from '../features/inventory/SubnetDiscoveryModal';
import { AgentBootstrapModal } from '../features/inventory/AgentBootstrapModal';
import { DeviceDetailModal } from '../features/inventory/DeviceDetailModal';
import { inventoryApi } from '../shared/api/inventory';
import { DeviceRead } from '../shared/types/inventory';
import '../i18n/config';

vi.mock('../shared/api/inventory', () => ({
  inventoryApi: {
    discoverSubnet: vi.fn(),
    importDiscovered: vi.fn(),
    executeRemoteAction: vi.fn(),
    getDeviceProcessSnapshot: vi.fn(),
    getAgentBootstrapConfig: vi.fn(),
    getDeviceNetworkChecks: vi.fn(),
    listAgents: vi.fn(),
    getAgentTelemetry: vi.fn(),
  },
}));

describe('Stage 6 Fleet Automation & Remote Node Management', () => {
  let queryClient: QueryClient;

  const mockDevice: DeviceRead = {
    id: 101,
    organization_id: 1,
    name: 'Core Border Router',
    hostname: 'rtr-border-01.noc',
    ip_address: '10.0.0.1',
    mac_address: '00:50:56:AB:CD:01',
    device_type: 'router',
    operating_system: 'Cisco IOS-XE',
    is_monitored: true,
    is_sample_data: false,
    room_id: 1,
    status: 'online',
    consecutive_failures: 0,
    created_at: '2026-11-14T00:00:00Z',
  };

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  describe('Subnet Auto-Discovery Scanner Modal', () => {
    it('scans subnet CIDR and displays discovered candidates', async () => {
      vi.mocked(inventoryApi.discoverSubnet).mockResolvedValueOnce({
        subnet_cidr: '192.168.10.0/24',
        total_probed: 15,
        discovered_count: 2,
        scan_duration_ms: 180,
        candidates: [
          {
            ip_address: '192.168.10.15',
            hostname: 'srv-dc01.corp',
            mac_address: '00:1A:2B:3C:4D:15',
            detected_device_type: 'server',
            open_ports: [80, 443, 3389],
            response_time_ms: 1.2,
            already_registered: false,
          },
          {
            ip_address: '192.168.10.20',
            hostname: 'sw-core01.corp',
            mac_address: '00:1A:2B:3C:4D:20',
            detected_device_type: 'switch',
            open_ports: [22, 161],
            response_time_ms: 0.9,
            already_registered: true,
          },
        ],
      });

      render(
        <QueryClientProvider client={queryClient}>
          <SubnetDiscoveryModal isOpen={true} onClose={vi.fn()} onImportSuccess={vi.fn()} />
        </QueryClientProvider>
      );

      // Verify modal title
      expect(screen.getByText(/Subnet Auto-Discovery Scanner/i)).toBeInTheDocument();

      // Click Start Subnet Scan
      const scanBtn = screen.getByTestId('start-scan-btn');
      fireEvent.click(scanBtn);

      await waitFor(() => {
        expect(inventoryApi.discoverSubnet).toHaveBeenCalledWith({
          subnet_cidr: '192.168.10.0/24',
          scan_mode: 'fast',
        });
      });

      // Verify candidate hosts rendered
      await waitFor(() => {
        expect(screen.getByText('192.168.10.15')).toBeInTheDocument();
        expect(screen.getByText('srv-dc01.corp')).toBeInTheDocument();
        expect(screen.getByText('192.168.10.20')).toBeInTheDocument();
        expect(screen.getByText(/Registered/i)).toBeInTheDocument();
      });
    });

    it('performs bulk import of selected candidates', async () => {
      const onImportSuccess = vi.fn();
      vi.mocked(inventoryApi.discoverSubnet).mockResolvedValueOnce({
        subnet_cidr: '192.168.10.0/24',
        total_probed: 10,
        discovered_count: 1,
        scan_duration_ms: 120,
        candidates: [
          {
            ip_address: '192.168.10.50',
            hostname: 'wks-eng01.corp',
            mac_address: '00:1A:2B:3C:4D:50',
            detected_device_type: 'workstation',
            open_ports: [445],
            response_time_ms: 2.1,
            already_registered: false,
          },
        ],
      });

      vi.mocked(inventoryApi.importDiscovered).mockResolvedValueOnce({
        imported_count: 1,
        skipped_count: 0,
        created_device_ids: [205],
        message: 'Successfully imported 1 discovered node(s).',
      });

      render(
        <QueryClientProvider client={queryClient}>
          <SubnetDiscoveryModal isOpen={true} onClose={vi.fn()} onImportSuccess={onImportSuccess} />
        </QueryClientProvider>
      );

      // Run scan
      fireEvent.click(screen.getByTestId('start-scan-btn'));

      await waitFor(() => {
        expect(screen.getByText('192.168.10.50')).toBeInTheDocument();
      });

      // Click import button
      const importBtn = screen.getByTestId('bulk-import-btn');
      fireEvent.click(importBtn);

      await waitFor(() => {
        expect(inventoryApi.importDiscovered).toHaveBeenCalledWith(
          expect.objectContaining({
            devices: expect.arrayContaining([
              expect.objectContaining({
                ip_address: '192.168.10.50',
                hostname: 'wks-eng01.corp',
              }),
            ]),
          })
        );
        expect(screen.getByText(/Successfully imported 1/i)).toBeInTheDocument();
      });
    });
  });

  describe('Agent 1-Click Bootstrap Deployer Modal', () => {
    it('fetches bootstrap config and renders PowerShell and Bash commands with copy functionality', async () => {
      vi.mocked(inventoryApi.getAgentBootstrapConfig).mockResolvedValueOnce({
        server_url: 'http://localhost:8000',
        organization_id: 1,
        organization_name: 'Primary Enterprise NOC',
        enrollment_secret_masked: '●●●●●●●●●●',
        powershell_command: 'powershell -ExecutionPolicy Bypass -Command "iwr http://localhost:8000/install.ps1"',
        linux_bash_command: 'curl -fsSL http://localhost:8000/install.sh | sudo bash',
        manual_steps: ['Open PowerShell as Administrator', 'Execute command'],
        agent_version: '1.2.0',
      });

      // Mock navigator.clipboard
      const writeTextMock = vi.fn().mockResolvedValue(undefined);
      Object.assign(navigator, {
        clipboard: {
          writeText: writeTextMock,
        },
      });

      await act(async () => {
        render(
          <QueryClientProvider client={queryClient}>
            <AgentBootstrapModal isOpen={true} onClose={vi.fn()} />
          </QueryClientProvider>
        );
      });

      // Check loading to content transition
      await waitFor(() => {
        expect(screen.getByText('Primary Enterprise NOC')).toBeInTheDocument();
        expect(screen.getByText(/v1\.2\.0/)).toBeInTheDocument();
      });

      // Verify PowerShell command is displayed
      const commandBlock = screen.getByTestId('bootstrap-command-text');
      expect(commandBlock.textContent).toContain('install.ps1');

      // Click Copy Command
      const copyBtn = screen.getByTestId('copy-bootstrap-btn');
      fireEvent.click(copyBtn);

      expect(writeTextMock).toHaveBeenCalledWith(
        'powershell -ExecutionPolicy Bypass -Command "iwr http://localhost:8000/install.ps1"'
      );

      // Switch to Linux Platform
      const linuxTab = screen.getByRole('button', { name: /Linux \/ macOS/i });
      fireEvent.click(linuxTab);

      // Verify Linux command is updated
      expect(commandBlock.textContent).toContain('install.sh | sudo bash');
    });
  });

  describe('Live Task Manager & Remote Action in DeviceDetailModal', () => {
    it('queries process snapshot and allows killing an active process', async () => {
      vi.mocked(inventoryApi.getDeviceProcessSnapshot).mockResolvedValueOnce({
        device_id: 101,
        device_name: 'Core Border Router',
        os_name: 'Linux / EdgeOS',
        captured_at: '2026-11-16T10:00:00Z',
        top_processes: [
          {
            pid: 1420,
            name: 'unbound',
            cpu_percent: 2.5,
            ram_mb: 48,
          },
          {
            pid: 9999,
            name: 'rogue_miner',
            cpu_percent: 85.0,
            ram_mb: 512,
          },
        ],
        system_services: [],
      });

      vi.mocked(inventoryApi.executeRemoteAction).mockResolvedValueOnce({
        command_id: 401,
        device_id: 101,
        action: 'kill_process',
        status: 'executed',
        verification_status: 'verified',
        execution_result: 'Process rogue_miner (PID 9999) successfully terminated.',
        executed_at: '2026-11-16T10:01:00Z',
      });

      render(
        <QueryClientProvider client={queryClient}>
          <DeviceDetailModal device={mockDevice} onClose={vi.fn()} />
        </QueryClientProvider>
      );

      // Switch to Task Manager tab
      const taskMgrTab = screen.getByTestId('tab-task-manager');
      fireEvent.click(taskMgrTab);

      // Verify processes are displayed
      await waitFor(() => {
        expect(screen.getByText('rogue_miner')).toBeInTheDocument();
        expect(screen.getByText('1420')).toBeInTheDocument();
      });

      // Kill the rogue process
      const killBtn = screen.getByTestId('kill-process-9999');
      fireEvent.click(killBtn);

      await waitFor(() => {
        expect(inventoryApi.executeRemoteAction).toHaveBeenCalledWith(
          101,
          expect.objectContaining({
            action: 'kill_process',
            parameters: { pid: 9999, process_name: 'rogue_miner' },
          })
        );
      });

      // Verify feedback banner
      await waitFor(() => {
        expect(
          screen.getByText(/Process rogue_miner \(PID 9999\) successfully terminated/i)
        ).toBeInTheDocument();
      });
    });

    it('queries system services and restarts a service', async () => {
      vi.mocked(inventoryApi.getDeviceProcessSnapshot).mockResolvedValueOnce({
        device_id: 101,
        device_name: 'Core Border Router',
        os_name: 'Windows Server',
        captured_at: '2026-11-16T10:00:00Z',
        top_processes: [],
        system_services: [
          {
            name: 'Spooler',
            display_name: 'Print Spooler',
            status: 'STOPPED',
            can_restart: true,
          },
          {
            name: 'WinDefend',
            display_name: 'Microsoft Defender Antivirus',
            status: 'RUNNING',
            can_restart: true,
          },
        ],
      });

      vi.mocked(inventoryApi.executeRemoteAction).mockResolvedValueOnce({
        command_id: 402,
        device_id: 101,
        action: 'restart_service',
        status: 'executed',
        verification_status: 'verified',
        execution_result: 'Service Spooler restarted and confirmed RUNNING.',
        executed_at: '2026-11-16T10:02:00Z',
      });

      render(
        <QueryClientProvider client={queryClient}>
          <DeviceDetailModal device={mockDevice} onClose={vi.fn()} />
        </QueryClientProvider>
      );

      // Switch to System Services tab
      const servicesTab = screen.getByTestId('tab-system-services');
      fireEvent.click(servicesTab);

      // Verify services are displayed
      await waitFor(() => {
        expect(screen.getByText('Print Spooler')).toBeInTheDocument();
        expect(screen.getByText('WinDefend')).toBeInTheDocument();
        expect(screen.getByText('STOPPED')).toBeInTheDocument();
      });

      // Restart the Spooler service
      const restartBtn = screen.getByTestId('restart-service-Spooler');
      fireEvent.click(restartBtn);

      await waitFor(() => {
        expect(inventoryApi.executeRemoteAction).toHaveBeenCalledWith(
          101,
          expect.objectContaining({
            action: 'restart_service',
            parameters: { service_name: 'Spooler' },
          })
        );
      });

      // Verify feedback banner
      await waitFor(() => {
        expect(
          screen.getByText(/Service Spooler restarted and confirmed RUNNING/i)
        ).toBeInTheDocument();
      });
    });
  });
});
