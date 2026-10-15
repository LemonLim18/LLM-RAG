import React, { useEffect, useState } from 'react';
import { 
  Home,
  Network,
  BotMessageSquare, 
  Activity,
  ShieldCheck,
  LogOut,
  Server,
  Workflow,
  PackagePlus,
  ListChecks,
  ChevronLeft,
  ChevronRight,
  FileCode2,
  HardDrive,
  RadioTower,
  LayoutDashboard,
  Library,
  User as UserIcon,
} from 'lucide-react';
import type { ViewId, User } from '../types';
import { normalizeUserRole } from '../types';
import { Confirm } from '../src/utils/swal';
import { useLocalLab } from '../src/localLab';

interface SidebarProps {
  currentView: ViewId;
  setView: (view: ViewId) => void;
  user: User | null;
  onLogout: () => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  onEditProfile?: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ currentView, setView, user, onLogout, collapsed: userCollapsed, onToggleCollapse, onEditProfile }) => {
  const [compact, setCompact] = useState(() => window.matchMedia('(max-width: 640px)').matches);
  useEffect(() => {
    const media = window.matchMedia('(max-width: 640px)');
    const update = () => setCompact(media.matches);
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);
  const collapsed = userCollapsed || (currentView.startsWith('knowledge_') && compact);
  const [networkOpen, setNetworkOpen] = useState(true);
  const [automationOpen, setAutomationOpen] = useState(true);
  const localLab = useLocalLab();
  const [knowledgeOpen, setKnowledgeOpen] = useState(true);

  if (!user) return null;
  const normalizedRole = normalizeUserRole(user.role);

  // ── Menu Item ──
  const MenuItem = ({
    id,
    label,
    icon: Icon,
    iconColor,
    textColor,
    labelClassName,
    matchViews,
  }: {
    id: ViewId;
    label: string;
    icon: any;
    iconColor?: string;
    textColor?: string;
    labelClassName?: string;
    /** Treat these views as active for this row (e.g. legacy drift / policy routes → hub). */
    matchViews?: ViewId[];
  }) => {
    const isActive = matchViews?.length
      ? matchViews.includes(currentView)
      : currentView === id;
    return (
      <li>
        <a
          className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors cursor-pointer 
            ${isActive
              ? (id.startsWith('knowledge_') ? 'bg-authoring/20 text-authoring font-semibold border-l-2 border-authoring' : 'bg-primary/20 text-primary font-semibold border-l-2 border-primary')
              : 'hover:bg-base-200'
            }
            ${collapsed ? 'justify-center px-2' : ''}
          `}
          onClick={() => setView(id)}
          title={label}
        >
          <Icon className={`h-4 w-4 shrink-0 ${isActive ? (id.startsWith('knowledge_') ? 'text-authoring' : 'text-primary') : (id.startsWith('knowledge_') ? 'text-authoring' : (iconColor || ''))}`} />
          {!collapsed && <span className={`whitespace-nowrap overflow-hidden ${isActive ? '' : (textColor || '')} ${labelClassName || ''}`}>{label}</span>}
        </a>
      </li>
    );
  };

  // ── Section Header (collapsible group) ──
  const SectionHeader = ({
    label,
    icon: Icon,
    iconColor,
    open,
    onToggle,
    children,
  }: {
    label: string;
    icon: any;
    iconColor: string;
    open: boolean;
    onToggle: () => void;
    children: React.ReactNode;
  }) => {
    if (collapsed) {
      // In collapsed mode, just render items directly (no group header)
      return <>{children}</>;
    }
    return (
      <li>
        <details open={open}>
          <summary
            className="cursor-pointer"
            onClick={(e) => { e.preventDefault(); onToggle(); }}
          >
            <Icon className={`h-4 w-4 ${iconColor}`} />
            <div className={`font-medium ${iconColor}`}>{label}</div>
          </summary>
          <ul>{children}</ul>
        </details>
      </li>
    );
  };

  return (
    <aside
      className={`bg-base-100 shrink-0 shadow-lg z-10 flex flex-col h-full transition-all duration-300 ease-in-out
        ${collapsed ? 'w-16' : 'w-64'}
      `}
    >
      {/* User Avatar Section */}
      <div 
        className={`border-b border-base-200 cursor-pointer hover:bg-base-200/50 transition-colors ${collapsed ? 'p-2 flex justify-center' : 'p-4'}`}
        onClick={onEditProfile}
        title="Edit Profile Settings"
      >
        {collapsed ? (
          <div className="avatar tooltip tooltip-right" data-tip="Edit Profile Settings">
            {(() => {
              if (!user.avatar) {
                return (
                  <div className="bg-neutral text-neutral-content rounded-full w-10 h-10 flex items-center justify-center font-bold border border-base-content/10">
                    <span className="text-lg">{user.username.charAt(0).toUpperCase()}</span>
                  </div>
                );
              }
              if (user.avatar.startsWith('avatar-')) {
                return (
                  <div className="bg-primary/20 text-primary flex items-center justify-center border border-primary/30 shadow-inner rounded-full w-10 h-10">
                    <UserIcon className="w-5 h-5" />
                  </div>
                );
              }
              return (
                <img
                  src={user.avatar}
                  alt="Profile"
                  className="rounded-full object-cover border border-base-content/20 shadow-sm w-10 h-10"
                />
              );
            })()}
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <div className="avatar">
              {(() => {
                if (!user.avatar) {
                  return (
                    <div className="bg-neutral text-neutral-content rounded-full w-10 h-10 flex items-center justify-center font-bold border border-base-content/10">
                      <span className="text-lg">{user.username.charAt(0).toUpperCase()}</span>
                    </div>
                  );
                }
                if (user.avatar.startsWith('avatar-')) {
                  return (
                    <div className="bg-primary/20 text-primary flex items-center justify-center border border-primary/30 shadow-inner rounded-full w-10 h-10">
                      <UserIcon className="w-5 h-5" />
                    </div>
                  );
                }
                return (
                  <img
                    src={user.avatar}
                    alt="Profile"
                    className="rounded-full object-cover border border-base-content/20 shadow-sm w-10 h-10"
                  />
                );
              })()}
            </div>
            <div className="min-w-0 flex-1 text-left">
              <div className="font-bold text-sm truncate" title={user.fullName || user.username}>{user.fullName || user.username}</div>
              <div className="text-xs opacity-60 capitalize truncate">{normalizedRole}</div>
            </div>
          </div>
        )}
      </div>

      {/* Navigation Menu */}
      <ul className={`menu ${collapsed ? 'p-1' : 'p-2'} w-full grow overflow-y-auto min-h-0 flex-col flex-nowrap`}>
        <MenuItem id="overview" label="Dashboard" icon={Home} iconColor="text-warning" textColor="text-warning" labelClassName="font-medium" />

        <SectionHeader
          label="Network Onboarding"
          icon={Activity}
          iconColor="text-primary"
          open={networkOpen}
          onToggle={() => setNetworkOpen(!networkOpen)}
        >
          
          <MenuItem id="common_services" label="Global Service Profiles" icon={RadioTower} iconColor="text-primary"/>
          <MenuItem id="netbox_devices" label="Device Inventory" icon={Server} iconColor="text-primary"/>
          <MenuItem id="template_studio" label="Template Studio" icon={FileCode2} iconColor="text-primary"/>
          <MenuItem id="onboarding" label="Onboard Device" icon={PackagePlus} iconColor="text-primary"/>
        </SectionHeader>

        <SectionHeader
          label="Safety/Monitoring/Policy"
          icon={ShieldCheck}
          iconColor="text-secondary"
          open={automationOpen}
          onToggle={() => setAutomationOpen(!automationOpen)}
        >
          <MenuItem id="topology" label="Topology Map" icon={Network} iconColor="text-secondary"/>
          <MenuItem id="net_perf" label="Performance" icon={Activity} iconColor="text-secondary"/>
          <MenuItem id="config_backup" label="Config Backup" icon={HardDrive} iconColor="text-secondary"/>          
        </SectionHeader>

        <SectionHeader
          label="Automation & AI"
          icon={BotMessageSquare}
          iconColor="text-accent"
          open={automationOpen}
          onToggle={() => setAutomationOpen(!automationOpen)}
        >
          <MenuItem id="ansible_studio" label="Ansible Studio" icon={Workflow} iconColor="text-accent"/>
          {normalizedRole === 'admin' && (
            <MenuItem id="approval_queue" label="Approval Queue" icon={ListChecks} iconColor="text-accent"/>
          )}
        </SectionHeader>
        {localLab && <SectionHeader label="Knowledge Engineering" icon={FileCode2} iconColor="text-authoring" open={knowledgeOpen} onToggle={() => setKnowledgeOpen(!knowledgeOpen)}>
          <MenuItem id="knowledge_overview" label="Overview" icon={LayoutDashboard}/>
          <MenuItem id="knowledge_categories" label="Category Management" icon={PackagePlus}/>
          <MenuItem id="knowledge_engineering" label="Operation Management" icon={Workflow}/>
          <MenuItem id="knowledge_parameters" label="Global Parameters" icon={ListChecks}/>
          <MenuItem id="knowledge_templates" label="Template Management" icon={Library}/>
          <MenuItem id="knowledge_publication" label="Validation & Publication" icon={ShieldCheck}/>
        </SectionHeader>}
      </ul>

      {/* Bottom Section: Collapse Toggle + Logout */}
      <div className="border-t border-base-200 p-2 flex flex-col gap-1">
        <button
          onClick={onToggleCollapse}
          className="btn btn-ghost btn-sm w-full gap-2"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <><ChevronLeft className="h-4 w-4" /><span className="text-xs">Collapse</span></>}
        </button>

        {/* Logout */}
        {collapsed ? (
          <button
            onClick={async () => { if (await Confirm.ask('Log Out?', 'You will need to sign in again.')) onLogout(); }}
            className="btn btn-ghost btn-sm w-full tooltip tooltip-right"
            data-tip="Logout"
          >
            <LogOut className="h-4 w-4 text-error" />
          </button>
        ) : (
          <button
            onClick={async () => { if (await Confirm.ask('Log Out?', 'You will need to sign in again.')) onLogout(); }}
            className="btn btn-outline btn-error btn-sm w-full gap-2"
          >
            <LogOut className="h-4 w-4" />
            Logout
          </button>
        )}
      </div>
    </aside>
  );
};

export default Sidebar;
