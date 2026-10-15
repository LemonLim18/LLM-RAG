import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Network, Bell, Sun } from 'lucide-react';
import './index.css';
import './monacoLocal';
import { LabContext } from './localLab';
import { daisyUIThemes } from './themes';
import Sidebar from '../components/Sidebar';
import KnowledgeEngineeringView from '../views/KnowledgeEngineeringView';
import type { ViewId } from '../types';

// This separate visual preview cannot switch to live mode or invoke authoring APIs.
const pages = {knowledge_overview:'Overview',knowledge_categories:'Categories',knowledge_parameters:'Parameters',knowledge_engineering:'Operations',knowledge_templates:'Templates',knowledge_publication:'Publication'} as const;
function ReferencePreview() {
  const [view,setView]=useState<keyof typeof pages>('knowledge_overview');
  const [theme,setTheme]=useState('night');
  useEffect(()=>{document.documentElement.setAttribute('data-theme',theme)},[theme]);
  const [collapsed,setCollapsed]=useState(false);
  const user={username:'admin',fullName:'Reference Preview',role:'admin' as const,lastLogin:''};
  const navigate=(next:ViewId)=>{if(next in pages)setView(next as keyof typeof pages)};
  return <LabContext.Provider value={true}><div data-theme={theme} className="w-screen h-screen flex flex-col overflow-hidden bg-base-200">
    <header className="flex items-center gap-3 px-5 h-14 shrink-0 border-b border-base-300 bg-base-100"><Network className="text-primary"/><strong className="text-xl">CogniShield</strong><span className="hidden lg:block text-xs opacity-60">LLM-Assisted Network Automation Controller</span><span className="ml-auto hidden md:block text-xs text-warning">Reference-data preview · no database writes</span><Bell size={18}/><Sun size={18}/><select aria-label="Theme" className="select select-sm w-28 bg-base-100" value={theme} onChange={e=>setTheme(e.target.value)}>{daisyUIThemes.map(t=><option key={t} value={t}>{t}</option>)}</select></header>
    <div className="flex flex-1 min-h-0 overflow-hidden"><Sidebar currentView={view} setView={navigate} user={user} onLogout={()=>{window.location.href='/'}} collapsed={collapsed} onToggleCollapse={()=>setCollapsed(!collapsed)}/><main className="relative flex-1 min-w-0 overflow-hidden"><KnowledgeEngineeringView previewOnly user={user} initialPage={pages[view]} setView={navigate}/></main></div>
  </div></LabContext.Provider>;
}
createRoot(document.getElementById('root')!).render(<ReferencePreview/>);
