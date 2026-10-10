// Imported only by vite.review.config.ts test instrumentation; never by src/main.
import { useEffect } from 'react';
import * as monaco from 'monaco-editor/editor/editor.api';
import { useWorkbench } from '../src/app/workbenchContext';
import type { ChangeProposal } from '../src/features/workspace/changeReview';

export function ReviewHarness() {
  const { working } = useWorkbench();
  useEffect(() => {
    const bridge = {
      base: (id = working.activeId) => working.proposalBase(id),
      stage: (proposal: ChangeProposal) => working.stageProposal(proposal),
      accept: (id: string, proposalId: string) => working.acceptProposal(id, proposalId),
      snapshot: () => ({ activeId: working.activeId, tabs: working.tabs }),
      editors: () => monaco.editor.getEditors().map((item) => ({ id: item.getId(), uri: item.getModel()?.uri.toString(), text: item.getModel()?.getValue(undefined, true), position: item.getPosition(), readOnly: item.getOption(monaco.editor.EditorOption.readOnly) })),
      models: () => monaco.editor.getModels().map((model) => model.uri.toString()),
      diffs: () => monaco.editor.getDiffEditors().map((diff) => ({ changes: diff.getLineChanges(), base: diff.getModel()?.original.getValue(undefined, true), proposed: diff.getModel()?.modified.getValue(undefined, true), originalLayout: diff.getOriginalEditor().getLayoutInfo() })),
      // Adversarial external edits use the real working model and its content events.
      modelEdit: (text: string) => {
        const item = monaco.editor.getEditors().find((editor) => editor.getModel()?.uri.toString().startsWith(`inmemory://v9-working/${working.activeId}/`));
        const model = item?.getModel();
        if (!item || !model) throw new Error('No working model');
        model.pushStackElement(); model.pushEditOperations(null, [{ range: model.getFullModelRange(), text }], () => null); model.pushStackElement();
      },
    };
    Object.assign(window, { __reviewTest: bridge });
    return () => { Reflect.deleteProperty(window, '__reviewTest'); };
  }, [working]);
  return <span className="sr-only" role="note">Test-only proposal producer · no AI service</span>;
}

export type ReviewTestBridge = {
  base: (id?: string) => ReturnType<ReturnType<typeof useWorkbench>['working']['proposalBase']>;
  stage: (proposal: ChangeProposal) => ReturnType<ReturnType<typeof useWorkbench>['working']['stageProposal']>;
  accept: (id: string, proposalId: string) => ReturnType<ReturnType<typeof useWorkbench>['working']['acceptProposal']>;
  snapshot: () => { activeId: string; tabs: ReturnType<typeof useWorkbench>['working']['tabs'] };
  editors: () => { id: string; uri?: string; text?: string; position: monaco.Position | null; readOnly: boolean }[];
  models: () => string[];
  diffs: () => { changes: monaco.editor.ILineChange[] | null; base?: string; proposed?: string; originalLayout: monaco.editor.EditorLayoutInfo }[];
  modelEdit: (text: string) => void;
};
declare global { interface Window { __reviewTest: ReviewTestBridge } }
