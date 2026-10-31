import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';
import './index.css';

import App from './App.tsx';
import ErrorBoundary from './components/ErrorBoundary.tsx';
import { setupMock } from './mocks';

// モック有効時のみ、コンソールに案内を表示（本番では何もしない）
setupMock();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </BrowserRouter>
  </StrictMode>,
);
