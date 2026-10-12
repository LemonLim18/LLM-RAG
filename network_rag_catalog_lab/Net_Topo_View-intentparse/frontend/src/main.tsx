import './monacoLocal'
import { LabProvider } from './LabContext'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { TaskProgressProvider } from '../contexts/TaskProgressContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <TaskProgressProvider>
      <LabProvider><App /></LabProvider>
    </TaskProgressProvider>
  </StrictMode>,
)
