import { useEffect, useRef } from 'react';
import { LEVELS } from './hrStorage';

function InterviewerReport({ feedback, skills, reportRef }) {
  return <section ref={reportRef} className="hr-report" aria-label="Interviewer feedback">
    <p className="hr-eyebrow">YOUR INTERVIEWER FEEDBACK</p><h2>A moment to reflect.</h2><p>{feedback.summary}</p>
    <div className="hr-scores"><div><strong>{feedback.question_quality}<small>/10</small></strong><span>Question quality</span></div><div><strong>{feedback.follow_up_quality}<small>/10</small></strong><span>Follow-up quality</span></div><div><strong>{feedback.covered_skills.length}<small>/{skills.length}</small></strong><span>Skills explored</span></div></div>
    <div className="hr-feedback-grid"><div><h3>What worked well</h3><ul>{feedback.strengths.map((text, index) => <li key={index}>{text}</li>)}</ul></div><div><h3>Try next time</h3><ul>{feedback.improvements.map((text, index) => <li key={index}>{text}</li>)}</ul></div></div>
    <h3>Skill coverage</h3><ul className="hr-coverage">{skills.map((skill) => <li key={skill}><span>{skill}</span><span>{feedback.covered_skills.includes(skill) ? 'Explored' : 'Not explored'}</span></li>)}</ul>
    <h3>Questions to take into your next interview</h3><ul>{feedback.suggested_questions.map((question, index) => <li key={index}>{question}</li>)}</ul>
    <p className="hr-hint">AI feedback on your interviewing technique, based on this practice conversation.</p>
  </section>;
}

export default function HrSession({ session, draft, onDraft, onAsk, onFinish, onReload, busy, error }) {
  const transcriptEnd = useRef(null);
  const reportStart = useRef(null);
  const input = useRef(null);
  const complete = session.status === 'completed';
  const atLimit = session.turns.length >= session.max_turns;
  const { profile } = session;
  const suggestions = session.turns.length === 0
    ? [`Tell me about yourself and your experience as a ${profile.role}.`, ...profile.skills.slice(0, 2).map((skill) => `Tell me about a project where you used ${skill}. What was your contribution?`)]
    : ['What was your specific contribution, and how did you measure the outcome?', 'What would you do differently if you faced that situation again?', `How have you applied ${profile.skills[session.turns.length % profile.skills.length]} in your work?`];

  useEffect(() => {
    if (complete) reportStart.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    else transcriptEnd.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [session.turns.length, complete, busy]);

  return <>
    <header className="hr-session-header"><div><p className="hr-eyebrow">YOU ARE THE HR INTERVIEWER</p><h1>Interview with {profile.name}</h1><p>{profile.role} · {LEVELS[profile.level]} · Fictional AI candidate</p></div><span className={`hr-status ${complete ? 'is-complete' : ''}`}>{complete ? 'Completed' : 'In progress'}</span></header>
    <div className="hr-session-grid">
      <section className="hr-conversation hr-card" aria-label="Interview conversation">
        <div className="hr-conversation-heading"><span><span className="hr-live-dot" />{profile.name} · AI candidate</span><span>{session.turns.length}/{session.max_turns} questions</span></div>
        <div className="hr-transcript" role="log" tabIndex={0} aria-label="Conversation transcript" aria-live="polite" aria-relevant="additions">
          {session.turns.length === 0 && <div className="hr-conversation-empty"><div className="hr-avatar" aria-hidden="true">{profile.name.slice(0, 1).toUpperCase()}</div><h2>Your candidate is ready.</h2><p>Introduce yourself or ask an opening question. You set the pace.</p></div>}
          {session.turns.map((turn, index) => <div className="hr-turn" key={turn.request_id}><article className="hr-message hr-question"><span>You · HR interviewer <small>Question {index + 1}</small></span><p>{turn.question}</p></article><article className="hr-message hr-answer"><span>{profile.name} · AI candidate</span><p>{turn.answer}</p></article></div>)}
          {busy === 'asking' && <div className="hr-turn"><article className="hr-message hr-question"><span>You · HR interviewer</span><p>{draft.text}</p></article><p className="hr-thinking" role="status">{profile.name} is thinking…</p></div>}
          {complete && session.feedback && <InterviewerReport feedback={session.feedback} skills={profile.skills} reportRef={reportStart} />}
          <div ref={transcriptEnd} />
        </div>
        {error && <div className="hr-error" role="alert"><p>{error.message}</p>{error.status === 409 && <button type="button" className="hr-secondary" disabled={Boolean(busy)} onClick={onReload}>Reload session</button>}</div>}
        {!complete && <div className="hr-compose">
          {!atLimit && <><div className="hr-suggestions" aria-label="Suggested questions"><span>Need a starting point?</span>{suggestions.map((question) => <button key={question} type="button" disabled={Boolean(busy)} onClick={() => { onDraft(question); input.current?.focus(); }}>{question}</button>)}</div>
            <form onSubmit={(event) => { event.preventDefault(); onAsk(); }}><label className="hr-field">Your interview question<textarea ref={input} rows={3} maxLength={2000} value={draft.text} disabled={Boolean(busy)} placeholder="Ask the candidate a question…" onChange={(event) => onDraft(event.target.value)} /></label><div className="hr-compose-actions"><span className="hr-hint">{draft.text.length}/2000 · Ask one question at a time</span><button type="submit" className="hr-primary" disabled={Boolean(busy) || !draft.text.trim()}>{busy === 'asking' ? 'Waiting for candidate…' : draft.requestId ? 'Retry question' : 'Ask candidate'}<span aria-hidden="true">↑</span></button></div></form></>}
          {atLimit && <p className="hr-hint">You’ve reached the 30-question limit. Finish your interview to see your feedback.</p>}
          <div className="hr-finish"><span>{busy === 'finishing' ? 'Reviewing your interviewing technique…' : 'Ready to reflect on the conversation?'}</span><button type="button" className="hr-secondary" disabled={Boolean(busy) || session.turns.length === 0} onClick={onFinish}>{busy === 'finishing' ? 'Preparing feedback…' : 'Finish & get feedback'}</button></div>
        </div>}
        {complete && <div className="hr-finish"><span>Keep practicing with a different candidate.</span><a className="hr-primary" href="#/hr">New HR interview →</a></div>}
      </section>
      <aside className="hr-session-aside"><section className="hr-card"><p className="hr-eyebrow">CANDIDATE PROFILE</p><h2>{profile.name}</h2><p>{profile.role}</p><span className="hr-pill">{LEVELS[profile.level]}</span><h3>Skills to explore</h3><div className="hr-tags">{profile.skills.map((skill) => <span className="hr-tag" key={skill}>{skill}</span>)}</div>{profile.background && <><h3>Background</h3><p className="hr-background">{profile.background}</p></>}</section><section className="hr-coach-note"><p className="hr-eyebrow">A SMALL INTERVIEWING TIP</p><p>Listen for a specific example. Then explore the situation, their own actions, and what changed as a result.</p></section><p className="hr-hint">Your conversation is saved after each response. Reopen this session from Recent HR interviews.</p></aside>
    </div>
  </>;
}
