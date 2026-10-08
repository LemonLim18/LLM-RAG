import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './app/App';
import { WorkbenchProvider } from './app/WorkbenchProvider';
import './styles/workbench.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <WorkbenchProvider>
      <App />
    </WorkbenchProvider>
  </StrictMode>,
);
