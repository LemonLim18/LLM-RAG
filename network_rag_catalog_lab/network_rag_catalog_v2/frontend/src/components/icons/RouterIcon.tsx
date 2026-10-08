import type { SVGProps } from 'react';

export function RouterIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
      <rect x="2" y="8" width="20" height="8" rx="2" />
      <path d="M6 12h.01M10 12h.01M14 12h.01M18 12h.01" />
      <path d="M7 5l2-2m8 2-2-2M7 19l2 2m8-2-2 2" />
    </svg>
  );
}
