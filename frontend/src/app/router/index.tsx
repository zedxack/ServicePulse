import React from 'react';
import { Navigate, createBrowserRouter } from 'react-router-dom';
import { AppLayout } from '../layouts/AppLayout';
import { ProtectedRoute } from '../../features/auth/ProtectedRoute';
import { LoginPage } from '../../features/auth/LoginPage';
import { PlatformDashboardPage } from '../../features/dashboard/PlatformDashboardPage';
import { CompanyDashboardPage } from '../../features/dashboard/CompanyDashboardPage';
import { SysAdminDashboardPage } from '../../features/dashboard/SysAdminDashboardPage';
import { ExecutiveDashboardPage } from '../../features/dashboard/ExecutiveDashboardPage';
import { EmployeeDashboardPage } from '../../features/dashboard/EmployeeDashboardPage';
import { InventoryExplorerPage } from '../../features/inventory/InventoryExplorerPage';
import { IncidentsPage } from '../../features/incidents/IncidentsPage';
import { IncidentDetailPage } from '../../features/incidents/IncidentDetailPage';
import { HelpdeskPage } from '../../features/tickets/HelpdeskPage';
import { TicketDetailPage } from '../../features/tickets/TicketDetailPage';
import { SoftwarePage } from '../../features/software/SoftwarePage';
import { UnauthorizedPage } from '../pages/UnauthorizedPage';
import { NotFoundPage } from '../pages/NotFoundPage';
import { useAuth } from '../../features/auth/AuthContext';

const DashboardRedirect: React.FC = () => {
  const { user } = useAuth();
  const target = user?.primary_dashboard ? `/dashboard/${user.primary_dashboard}` : '/login';
  return <Navigate to={target} replace />;
};

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/unauthorized',
    element: <UnauthorizedPage />,
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <DashboardRedirect />,
      },
      {
        path: 'dashboard/platform',
        element: (
          <ProtectedRoute allowedRoles={['platform_super_admin']}>
            <PlatformDashboardPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'dashboard/company',
        element: (
          <ProtectedRoute allowedRoles={['company_admin', 'admin', 'platform_super_admin']}>
            <CompanyDashboardPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'dashboard/sysadmin',
        element: (
          <ProtectedRoute allowedRoles={['it_admin', 'support', 'admin', 'company_admin', 'platform_super_admin']}>
            <SysAdminDashboardPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'dashboard/executive',
        element: (
          <ProtectedRoute allowedRoles={['executive', 'admin', 'company_admin', 'platform_super_admin']}>
            <ExecutiveDashboardPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'dashboard/employee',
        element: <EmployeeDashboardPage />,
      },
      {
        path: 'inventory',
        element: <InventoryExplorerPage />,
      },
      {
        path: 'incidents',
        element: <IncidentsPage />,
      },
      {
        path: 'incidents/:incidentId',
        element: <IncidentDetailPage />,
      },
      {
        path: 'tickets',
        element: <HelpdeskPage />,
      },
      {
        path: 'tickets/:ticketId',
        element: <TicketDetailPage />,
      },
      {
        path: 'software',
        element: <SoftwarePage />,
      },
    ],
  },
  {
    path: '*',
    element: <NotFoundPage />,
  },
]);
