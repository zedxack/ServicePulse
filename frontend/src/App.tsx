import React from 'react';
import { RouterProvider } from 'react-router-dom';
import { QueryProvider } from './app/providers/QueryProvider';
import { AuthProvider } from './features/auth/AuthContext';
import { ThemeProvider } from './shared/theme/ThemeContext';
import { router } from './app/router';

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <QueryProvider>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </QueryProvider>
    </ThemeProvider>
  );
};

export default App;
