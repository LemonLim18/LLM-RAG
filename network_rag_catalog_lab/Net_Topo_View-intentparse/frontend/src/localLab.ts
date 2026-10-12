import { createContext, useContext } from 'react';
export const LabContext = createContext(false);
export const useLocalLab = () => useContext(LabContext);

export type DataSource = 'stored' | 'simulated' | 'real';
export type Capability =
  | 'inventory.write' | 'profiles.write' | 'templates.write' | 'studio.authoring'
  | 'observations.read' | 'template_git.status' | 'template_git.remote'
  | 'onboarding.register_ui' | 'onboarding.ztp_simulation'
  | 'approval.workflow_ui' | 'backup.restore_simulation_ui' | 'policy.evaluate_stored_ui'
  | 'execution.ssh' | 'execution.deploy' | 'ai.generate' | 'ai.local_chat';
export interface PlatformCapabilities {
  mode: 'local_lab' | 'normal';
  providers?: Record<string, string>;
  features?: Partial<Record<Capability, boolean>>;
}
export interface ObservationMetadata {
  source: DataSource;
  provider: string;
  fixture_revision?: string;
  live: boolean;
}
export const CapabilityContext = createContext<PlatformCapabilities>({ mode: 'local_lab', features: {} });
export const useCapability = (name: Capability) => {
  const capabilities = useContext(CapabilityContext);
  return capabilities.features?.[name] ?? capabilities.mode === 'normal';
};
