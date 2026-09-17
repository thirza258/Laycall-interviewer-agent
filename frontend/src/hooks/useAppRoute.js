import { useSyncExternalStore } from 'react';

function subscribe(onChange) {
  window.addEventListener('hashchange', onChange);
  return () => window.removeEventListener('hashchange', onChange);
}

export default function useAppRoute() {
  const hash = useSyncExternalStore(subscribe, () => window.location.hash, () => '');
  const parts = hash.replace(/^#\/?/, '').split('/').filter(Boolean);
  return { section: parts[0] || 'interviews', courseId: parts[1], sessionId: parts[0] === 'hr' ? parts[1] : undefined, lessonId: parts[2], extra: parts.length > 3 };
}
