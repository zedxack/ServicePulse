import { apiClient } from './client';
import {
  CEODashboardResponse,
  CompanyDashboardResponse,
  EmployeeDashboardResponse,
  PlatformDashboardResponse,
  SysAdminDashboardResponse,
} from '../types/dashboard';

export const dashboardApi = {
  getPlatformDashboard: async (): Promise<PlatformDashboardResponse> => {
    const response = await apiClient.get<PlatformDashboardResponse>('/dashboard/platform');
    return response.data;
  },

  getCompanyDashboard: async (): Promise<CompanyDashboardResponse> => {
    const response = await apiClient.get<CompanyDashboardResponse>('/dashboard/company');
    return response.data;
  },

  getSysAdminDashboard: async (): Promise<SysAdminDashboardResponse> => {
    const response = await apiClient.get<SysAdminDashboardResponse>('/dashboard/sysadmin');
    return response.data;
  },

  getExecutiveDashboard: async (): Promise<CEODashboardResponse> => {
    const response = await apiClient.get<CEODashboardResponse>('/dashboard/executive');
    return response.data;
  },

  getEmployeeDashboard: async (): Promise<EmployeeDashboardResponse> => {
    const response = await apiClient.get<EmployeeDashboardResponse>('/dashboard/employee');
    return response.data;
  },
};
