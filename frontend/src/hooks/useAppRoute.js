import { useSyncExternalStore } from 'react';

function getRouteString() {
  if (typeof window === 'undefined') return '';
  return window.location.hash || window.location.pathname;
}

function subscribe(onChange) {
  window.addEventListener('hashchange', onChange);
  window.addEventListener('popstate', onChange);
  return () => {
    window.removeEventListener('hashchange', onChange);
    window.removeEventListener('popstate', onChange);
  };
}

export default function useAppRoute() {
  const routeString = useSyncExternalStore(subscribe, getRouteString, () => '');
  const raw = routeString.replace(/^#\/?/, '').replace(/^\/(?:app\/)?/, '');
  const parts = raw.split('/').filter(Boolean);
  return {
    section: parts[0] || 'interviews',
    courseId: parts[1],
    sessionId: parts[0] === 'hr' ? parts[1] : undefined,
    lessonId: parts[2],
    extra: parts.length > 3,
  };
}
