import { useState } from 'react';
import { LEVELS, normalizeSkills, readDraft, saveDraft } from './hrStorage';

const EMPTY_PROFILE = { name: 'Alex Morgan', role: '', level: 'mid', skills: [], background: '' };
const PRESETS = [
  { role: 'Software engineer', skills: ['JavaScript', 'React', 'Problem solving'] },
  { role: 'Product manager', skills: ['Product strategy', 'Prioritization', 'Stakeholder communication'] },
  { role: 'Data analyst', skills: ['SQL', 'Data visualization', 'Analytical thinking'] },
  { role: 'Customer success manager', skills: ['Customer communication', 'Conflict resolution', 'Account management'] },
];

function initialProfile() {
  const saved = readDraft('setup', EMPTY_PROFILE);
  return saved && typeof saved.name === 'string' && typeof saved.role === 'string'
    && LEVELS[saved.level] && typeof saved.background === 'string'
    && Array.isArray(saved.skills) && saved.skills.every((skill) => typeof skill === 'string')
    ? saved : EMPTY_PROFILE;
}

export default function HrSetup({ onStart, busy, error }) {
  const [profile, setProfile] = useState(initialProfile);
  const [skillInput, setSkillInput] = useState('');
  const [skillError, setSkillError] = useState('');
  const allSkills = normalizeSkills([...profile.skills, ...skillInput.split(/[,\n]/)]);
  const skillsValid = allSkills.length > 0 && allSkills.length <= 12 && allSkills.every((skill) => skill.length <= 60);

  function update(changes) {
    const next = { ...profile, ...changes };
    setProfile(next);
    saveDraft('setup', next);
  }

  function addSkills() {
    if (allSkills.length > 12 || allSkills.some((skill) => skill.length > 60)) {
      setSkillError('Use up to 12 skills, with at most 60 characters each.');
      return;
    }
    update({ skills: allSkills });
    setSkillInput('');
    setSkillError('');
  }

  function submit(event) {
    event.preventDefault();
    if (busy || !skillsValid || !profile.name.trim() || profile.role.trim().length < 2) return;
    onStart({ ...profile, name: profile.name.trim(), role: profile.role.trim(), skills: allSkills, background: profile.background.trim() });
  }

  return <>
    <header className="hr-hero">
      <p className="hr-eyebrow">HR INTERVIEW MODE</p>
      <h1>Take the interviewer’s seat.</h1>
      <p>Build a candidate profile, ask your own questions, and practice following the conversation wherever it leads.</p>
      <div className="hr-role-switch"><span>You are the HR interviewer</span><span aria-hidden="true">↔</span><span>AI plays the candidate</span></div>
    </header>
    <div className="hr-setup-grid">
      <section className="hr-card">
        <div className="hr-section-title"><span className="hr-step">01</span><div><h2>Meet your next candidate</h2><p>Choose what they know. You lead the interview.</p></div></div>
        <form onSubmit={submit} className="hr-form">
          <fieldset disabled={busy}>
            <legend className="hr-label">Start with a role, or create your own</legend>
            <div className="hr-presets">{PRESETS.map((preset) => <button type="button" key={preset.role}
              aria-pressed={profile.role === preset.role} onClick={() => { update(preset); setSkillInput(''); setSkillError(''); }}>
              {preset.role}
            </button>)}</div>
            <div className="hr-field-row">
              <label className="hr-field">Candidate name<input required maxLength={80} value={profile.name} onChange={(event) => update({ name: event.target.value })} /></label>
              <label className="hr-field">Experience level<select value={profile.level} onChange={(event) => update({ level: event.target.value })}>
                {Object.entries(LEVELS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
              </select></label>
            </div>
            <label className="hr-field">Target role<input required minLength={2} maxLength={120} placeholder="e.g. Frontend engineer" value={profile.role} onChange={(event) => update({ role: event.target.value })} /></label>
            <div className="hr-field">
              <label htmlFor="hr-skills">Candidate skills <span className="hr-optional">1–12 skills</span></label>
              <div className="hr-skill-input"><input id="hr-skills" value={skillInput} aria-describedby="hr-skills-help" placeholder="e.g. React, TypeScript, communication"
                onChange={(event) => { setSkillInput(event.target.value); setSkillError(''); }}
                onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ',') { event.preventDefault(); addSkills(); } }} />
                <button type="button" className="hr-secondary" onClick={addSkills} disabled={!skillInput.trim()}>Add</button></div>
              <p id="hr-skills-help" className="hr-hint">Separate skills with commas or press Enter. Technical and people skills both work.</p>
              <div className="hr-tags">{profile.skills.map((skill) => <span key={skill} className="hr-tag">{skill}<button type="button" aria-label={`Remove ${skill}`} onClick={() => update({ skills: profile.skills.filter((item) => item !== skill) })}>×</button></span>)}</div>
              {(skillError || allSkills.length > 12 || allSkills.some((skill) => skill.length > 60)) && <p className="hr-error" role="alert">{skillError || 'Use up to 12 skills, with at most 60 characters each.'}</p>}
            </div>
            <label className="hr-field">Candidate background <span className="hr-optional">Optional</span>
              <textarea rows={3} maxLength={2000} value={profile.background} placeholder="e.g. Built dashboards at a small startup and is moving into a larger team."
                onChange={(event) => update({ background: event.target.value })} />
            </label>
          </fieldset>
          {error && <p className="hr-error" role="alert">{error.message}</p>}
          <button className="hr-primary" type="submit" disabled={busy || !skillsValid || !profile.name.trim() || profile.role.trim().length < 2}>{busy ? 'Preparing your session…' : 'Start HR interview'}<span aria-hidden="true">→</span></button>
        </form>
      </section>
      <aside className="hr-setup-guide">
        <div className="hr-card hr-preview"><p className="hr-eyebrow">YOUR PRACTICE CANDIDATE</p><div className="hr-avatar" aria-hidden="true">{(profile.name.trim() || 'A').slice(0, 1).toUpperCase()}</div><h2>{profile.name.trim() || 'Your candidate'}</h2><p>{profile.role || 'Choose a target role'}</p><span className="hr-pill">{LEVELS[profile.level]} · AI candidate</span><div className="hr-tags">{allSkills.slice(0, 12).map((skill) => <span className="hr-tag" key={skill}>{skill}</span>)}</div></div>
        <div className="hr-guide"><h2>A better conversation starts here.</h2><ol><li><strong>Set the scene</strong><span>Pick the role, skills and experience you want to explore.</span></li><li><strong>Ask, listen, follow up</strong><span>The candidate responds in character. Ask for examples and dig into their decisions.</span></li><li><strong>Reflect on your technique</strong><span>Finish to get feedback on your questions, follow-ups and skill coverage.</span></li></ol><p className="hr-hint">Fictional candidates for practice. No resume needed.</p></div>
      </aside>
    </div>
  </>;
}
