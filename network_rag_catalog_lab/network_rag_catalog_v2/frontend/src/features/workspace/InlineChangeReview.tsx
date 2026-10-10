import { useState } from 'react';
import { DiffEditor } from '@monaco-editor/react';
import { configureNetworkLanguage } from './monacoSetup';

// Monaco's native inline diff, not a side-by-side workspace or custom diff engine.
export function InlineChangeReview({ documentId, reviewId, base, proposed }: {
  documentId: string; reviewId: string; base: string; proposed: string;
}) {
  const [summary, setSummary] = useState(base === proposed ? 'No changes.' : 'Computing inline changes…');
  const path = `inmemory://v9-review/${documentId}/${encodeURIComponent(reviewId)}`;
  return <section className="inline-change-review" aria-label="Inline change review">
    <p className="inline-change-review__legend" role="status">{summary} <span>− removed</span> <span>+ added</span> · read-only comparison</p>
    <div className="monaco-host"><DiffEditor original={base} modified={proposed} language="network-cli" theme="network-workbench"
      originalModelPath={`${path}/base`} modifiedModelPath={`${path}/proposed`}
      keepCurrentOriginalModel={false} keepCurrentModifiedModel={false} beforeMount={configureNetworkLanguage}
      onMount={(diff) => {
        const subscription = diff.onDidUpdateDiff(() => {
          const changes = diff.getLineChanges();
          setSummary(changes === null ? 'Diff unavailable; no changes accepted.' : changes.length
            ? `${changes.length} changed region${changes.length === 1 ? '' : 's'}.`
            : base === proposed ? 'No changes.' : 'Text differs only in metadata or line endings; no visible line changes.');
        });
        diff.onDidDispose(() => subscription.dispose());
      }}
      options={{ renderSideBySide: false, useInlineViewWhenSpaceIsLimited: true, readOnly: true, domReadOnly: true,
        originalEditable: false, renderMarginRevertIcon: false, renderGutterMenu: false, ignoreTrimWhitespace: false,
        diffAlgorithm: 'advanced', maxComputationTime: 3000, maxFileSize: 2, automaticLayout: true,
        minimap: { enabled: false }, fontSize: 13, lineHeight: 21, renderIndicators: true,
        ariaLabel: 'Read-only inline change comparison', scrollBeyondLastLine: false }} /></div>
  </section>;
}
