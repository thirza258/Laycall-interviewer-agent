import { useEffect, useRef, useState } from 'react';
import * as api from '../../api';
import HrSetup from './HrSetup';
import HrSession from './HrSession';
import { readDraft, readRecentSessions, rememberSession, saveDraft, validSessionId } from './hrStorage';
import './hr.css';

function questionDraft(id) {
  const draft = readDraft(id, {});
  return { text: typeof draft.text === 'string' ? draft.text : '', requestId: validSessionId(draft.requestId) ? draft.requestId : null };
}

export default function HrWorkspace({ sessionId, invalidRoute }) {
  const invalid = invalidRoute || (sessionId && !validSessionId(sessionId));
  const [session, setSession] = useState(null);
  const [recent, setRecent] = useState(readRecentSessions);
  const [draft, setDraft] = useState(() => questionDraft(sessionId));
  const [busy, setBusy] = useState(sessionId && !invalid ? 'loading' : '');
  const [error, setError] = useState(null);
  const action = useRef(false);
  const creation = useRef(null);

  function acceptSession(next) {
    setSession(next);
    setRecent(rememberSession(next));
  }

  useEffect(() => {
    if (!sessionId || invalid) return;
    const controller = new AbortController();
    api.getHrInterview(sessionId, controller.signal).then((next) => {
      if (controller.signal.aborted) return;
      setSession(next);
      setRecent(rememberSession(next));
      // A response may have been saved before the browser lost connection.
      setDraft((current) => {
        if (!next.turns.some((turn) => turn.request_id === current.requestId)) return current;
        saveDraft(sessionId, null);
        return { text: '', requestId: null };
      });
    }).catch((err) => { if (!controller.signal.aborted) setError(err); })
      .finally(() => { if (!controller.signal.aborted) setBusy(''); });
    return () => controller.abort();
  }, [sessionId, invalid]);

  function begin(kind) {
    if (action.current || busy) return false;
    action.current = true;
    setBusy(kind);
    setError(null);
    return true;
  }

  function end() { action.current = false; setBusy(''); }

  async function start(profile) {
    if (!begin('creating')) return;
    try {
      const fingerprint = JSON.stringify(profile);
      if (creation.current?.fingerprint !== fingerprint) creation.current = { id: crypto.randomUUID(), fingerprint };
      const next = await api.createHrInterview(creation.current.id, profile);
      setRecent(rememberSession(next));
      saveDraft('setup', null);
      window.location.hash = `#/hr/${next.id}`;
    } catch (err) { setError(err); }
    finally { end(); }
  }

  function changeDraft(text) {
    const next = { text, requestId: null };
    setDraft(next);
    saveDraft(sessionId, next);
  }

  async function ask() {
    if (!session || session.status === 'completed' || session.turns.length >= session.max_turns || !draft.text.trim() || !begin('asking')) return;
    const pending = { text: draft.text.trim(), requestId: draft.requestId || crypto.randomUUID() };
    setDraft(pending);
    saveDraft(sessionId, pending);
    try {
      acceptSession(await api.askHrCandidate(sessionId, pending.text, pending.requestId, session.turns.length));
      changeDraft('');
    } catch (err) { setError(err); }
    finally { end(); }
  }

  async function finish() {
    if (!session?.turns.length || session.status === 'completed' || !begin('finishing')) return;
    try {
      acceptSession(await api.finishHrInterview(sessionId));
      changeDraft('');
    } catch (err) { setError(err); }
    finally { end(); }
  }

  async function reload() {
    if (!begin('loading')) return;
    try {
      const next = await api.getHrInterview(sessionId);
      acceptSession(next);
      if (next.status === 'completed' || next.turns.some((turn) => turn.request_id === draft.requestId)) changeDraft('');
    } catch (err) { setError(err); }
    finally { end(); }
  }

  return <main className="hr-workspace">
    <div className="hr-topbar"><a href="#/interviews">← Candidate practice</a><nav aria-label="HR navigation"><a href="#/courses">Courses & guides</a>{sessionId && <a href="#/hr">+ New HR interview</a>}</nav></div>
    <div className="hr-content">
      {invalid ? <section className="hr-card"><h1>This session link is invalid.</h1><a className="hr-text-link" href="#/hr">Start a new HR interview →</a></section>
        : sessionId ? session ? <HrSession session={session} draft={draft} onDraft={changeDraft} onAsk={ask} onFinish={finish} onReload={reload} busy={busy} error={error} />
          : <section className="hr-card">{busy ? <p role="status">Loading your HR interview…</p> : <><h1>Couldn’t open this interview</h1><p className="hr-error" role="alert">{error?.message}</p><button className="hr-secondary" onClick={reload}>Retry loading</button> <a className="hr-text-link" href="#/hr">Start a new session</a></>}</section>
          : <HrSetup onStart={start} busy={Boolean(busy)} error={error} />}
      {recent.length > 0 && <section className="hr-recent"><h2>Recent HR interviews</h2><p className="hr-hint">Session shortcuts are saved in this browser. Keep a session URL to reopen it elsewhere.</p><div>{recent.map((item) => <a key={item.id} href={`#/hr/${item.id}`} aria-current={item.id === sessionId ? 'page' : undefined}><span><strong>{item.name}</strong><small>{item.role}</small></span><span className={`hr-status ${item.status === 'completed' ? 'is-complete' : ''}`}>{item.status === 'completed' ? 'Completed' : 'Resume'} →</span></a>)}</div></section>}
    </div>
  </main>;
}
