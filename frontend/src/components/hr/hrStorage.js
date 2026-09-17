const HISTORY_KEY = 'laycall.hr.sessions.v1';
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function validSessionId(id) {
  return typeof id === 'string' && UUID_PATTERN.test(id);
}

export function readRecentSessions() {
  try {
    const stored = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
    return Array.isArray(stored) ? stored.filter((item) => item && validSessionId(item.id)
      && typeof item.name === 'string' && typeof item.role === 'string'
      && ['in_progress', 'completed'].includes(item.status)).slice(0, 20) : [];
  } catch { return []; }
}

export function rememberSession(session) {
  const item = {
    id: session.id, name: session.profile.name, role: session.profile.role,
    status: session.status, created_at: session.created_at,
  };
  const recent = [item, ...readRecentSessions().filter((previous) => previous.id !== item.id)].slice(0, 20);
  try { localStorage.setItem(HISTORY_KEY, JSON.stringify(recent)); } catch { /* Session URLs still work. */ }
  return recent;
}

export function readDraft(key, fallback) {
  try { return JSON.parse(sessionStorage.getItem(`laycall.hr.draft.v1.${key}`)) || fallback; }
  catch { return fallback; }
}

export function saveDraft(key, value) {
  try {
    if (value === null) sessionStorage.removeItem(`laycall.hr.draft.v1.${key}`);
    else sessionStorage.setItem(`laycall.hr.draft.v1.${key}`, JSON.stringify(value));
  } catch { /* Drafts remain available in React state. */ }
}

export function normalizeSkills(skills) {
  const seen = new Set();
  return skills.map((skill) => skill.trim()).filter((skill) => {
    if (!skill || seen.has(skill.toLowerCase())) return false;
    seen.add(skill.toLowerCase());
    return true;
  });
}

export const LEVELS = { junior: 'Junior', mid: 'Mid-level', senior: 'Senior' };
