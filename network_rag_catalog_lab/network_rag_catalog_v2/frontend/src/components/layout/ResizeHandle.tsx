import { useCallback, useEffect, useRef } from 'react';

interface ResizeHandleProps {
  orientation: 'vertical' | 'horizontal';
  label: string;
  value: number;
  min: number;
  max: number;
  direction?: 1 | -1;
  onChange: (value: number) => void;
}

export function ResizeHandle({ orientation, label, value, min, max, direction = 1, onChange }: ResizeHandleProps) {
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => () => cleanupRef.current?.(), []);

  const beginDrag = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    event.preventDefault();
    const origin = orientation === 'vertical' ? event.clientX : event.clientY;
    const startValue = value;

    const move = (moveEvent: PointerEvent) => {
      const position = orientation === 'vertical' ? moveEvent.clientX : moveEvent.clientY;
      onChange(startValue + (position - origin) * direction);
    };
    const stop = () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', stop);
      document.body.classList.remove('is-resizing');
      cleanupRef.current = null;
    };

    document.body.classList.add('is-resizing');
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', stop, { once: true });
    cleanupRef.current = stop;
  }, [direction, onChange, orientation, value]);

  const onKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    const decrement = orientation === 'vertical' ? 'ArrowLeft' : 'ArrowUp';
    const increment = orientation === 'vertical' ? 'ArrowRight' : 'ArrowDown';
    if (event.key !== decrement && event.key !== increment && event.key !== 'Home' && event.key !== 'End') return;
    event.preventDefault();
    if (event.key === 'Home') onChange(min);
    else if (event.key === 'End') onChange(max);
    else onChange(value + (event.key === increment ? 12 : -12) * direction);
  };

  return (
    <div
      className={`resize-handle resize-handle--${orientation}`}
      role="separator"
      tabIndex={0}
      aria-label={label}
      aria-orientation={orientation}
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={Math.round(value)}
      onPointerDown={beginDrag}
      onKeyDown={onKeyDown}
    />
  );
}
