// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../../App';
import * as api from '../../api';
import { readRecentSessions } from './hrStorage';

vi.mock('../../api');

const ID = 'dea3da4e-f670-465b-aac2-97926d205668';
const PROFILE = { name: 'Alex Morgan', role: 'Backend engineer', level: 'senior', skills: ['Python', 'SQL'], background: 'Built a scheduling service.' };
const FEEDBACK = {
  summary: 'You asked for clear examples. Follow up on the candidate’s personal contribution.',
  question_quality: 8, follow_up_quality: 6, strengths: ['Clear opening question.'],
  improvements: ['Ask about measurable outcomes.'], covered_skills: ['Python'],
  suggested_questions: ['How did you measure the result?'],
};
let stored;

function navigate(path) {
  act(() => {
    window.history.pushState({}, '', `/app/#/${path}`);
    window.dispatchEvent(new HashChangeEvent('hashchange'));
  });
}

beforeEach(() => {
  vi.resetAllMocks();
  localStorage.clear();
  sessionStorage.clear();
  Element.prototype.scrollIntoView = vi.fn();
  window.history.replaceState({}, '', '/app/#/hr');
  stored = { id: ID, profile: PROFILE, status: 'in_progress', turns: [], feedback: null, created_at: '2026-09-17T00:00:00Z', max_turns: 30 };
  api.createHrInterview.mockImplementation(async (id, profile) => { stored = { ...stored, id, profile }; return stored; });
  api.getHrInterview.mockImplementation(async () => stored);
  api.askHrCandidate.mockImplementation(async (_id, question, requestId) => {
    stored = { ...stored, turns: [...stored.turns, { question, request_id: requestId, answer: 'I built a Python scheduling service with a retry queue.', created_at: '2026-09-17T00:00:00Z' }] };
    return stored;
  });
  api.finishHrInterview.mockImplementation(async () => { stored = { ...stored, status: 'completed', feedback: FEEDBACK }; return stored; });
});

afterEach(cleanup);

async function openSession() {
  navigate(`hr/${ID}`);
  render(<App />);
  await screen.findByRole('heading', { name: 'Your candidate is ready.' });
}

async function ask(text = 'Tell me about a Python project.') {
  fireEvent.change(screen.getByLabelText('Your interview question'), { target: { value: text } });
  fireEvent.click(screen.getByRole('button', { name: 'Ask candidate' }));
  await waitFor(() => expect(screen.queryByText('Alex Morgan is thinking…')).toBeNull());
}

describe('HR interviewer practice', () => {
  it('creates a candidate from specified skills without a resume, then interviews and reviews', async () => {
    render(<App />);
    await screen.findByRole('heading', { name: 'Take the interviewer’s seat.' });
    expect(screen.getByRole('button', { name: 'Start HR interview' }).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText('Target role'), { target: { value: 'Backend engineer' } });
    fireEvent.change(screen.getByLabelText('Experience level'), { target: { value: 'senior' } });
    fireEvent.change(screen.getByLabelText(/Candidate skills/), { target: { value: ' Python, SQL, python ' } });
    fireEvent.click(screen.getByRole('button', { name: 'Start HR interview' }));
    await screen.findByRole('heading', { name: 'Your candidate is ready.' });
    expect(api.createHrInterview).toHaveBeenCalledWith(expect.any(String), expect.objectContaining({ role: 'Backend engineer', level: 'senior', skills: ['Python', 'SQL'] }));
    expect(api.uploadResume).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Finish & get feedback' }).disabled).toBe(true);
    await ask();
    expect(screen.getByText('I built a Python scheduling service with a retry queue.')).toBeTruthy();
    await ask('Why did you choose a retry queue?');
    expect(api.askHrCandidate).toHaveBeenLastCalledWith(stored.id, 'Why did you choose a retry queue?', expect.any(String), 1);
    fireEvent.click(screen.getByRole('button', { name: 'Finish & get feedback' }));
    const feedback = await screen.findByRole('region', { name: 'Interviewer feedback' });
    expect(within(feedback).getByText('Ask about measurable outcomes.')).toBeTruthy();
    expect(within(feedback).getByText('Not explored')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Ask candidate' })).toBeNull();
    expect(readRecentSessions()[0].status).toBe('completed');
  });

  it('preserves an unsent draft and conversation when leaving and reopening HR practice', async () => {
    await openSession();
    await ask();
    fireEvent.change(screen.getByLabelText('Your interview question'), { target: { value: 'What was your contribution?' } });
    navigate('interviews');
    expect(screen.getByRole('heading', { name: 'Mock Interview' })).toBeTruthy();
    navigate(`hr/${ID}`);
    await screen.findByLabelText('Your interview question');
    expect(screen.getByLabelText('Your interview question').value).toBe('What was your contribution?');
    expect(screen.getByText('I built a Python scheduling service with a retry queue.')).toBeTruthy();
    expect(readRecentSessions()[0].id).toBe(ID);
  });

  it('retries with the same request ID and retains the draft after a model failure', async () => {
    api.askHrCandidate.mockRejectedValueOnce(new Error('Model unavailable'));
    await openSession();
    await ask();
    expect(screen.getByRole('alert').textContent).toContain('Model unavailable');
    expect(screen.getByLabelText('Your interview question').value).toBe('Tell me about a Python project.');
    const firstRequest = api.askHrCandidate.mock.calls[0];
    fireEvent.click(screen.getByRole('button', { name: 'Retry question' }));
    await screen.findByText('I built a Python scheduling service with a retry queue.');
    expect(api.askHrCandidate.mock.calls[1]).toEqual(firstRequest);
    expect(screen.getByLabelText('Your interview question').value).toBe('');
  });

  it('recovers a committed response after a lost connection without sending it again', async () => {
    await openSession();
    api.askHrCandidate.mockImplementationOnce(async (_id, question, requestId) => {
      stored = { ...stored, turns: [{ request_id: requestId, question, answer: 'Saved before the connection dropped.', created_at: stored.created_at }] };
      throw new Error('Connection lost');
    });
    await ask();
    cleanup();
    render(<App />);
    await screen.findByText('Saved before the connection dropped.');
    expect(screen.getByLabelText('Your interview question').value).toBe('');
    expect(api.askHrCandidate).toHaveBeenCalledTimes(1);
  });

  it('keeps the conversation usable after feedback fails', async () => {
    await openSession();
    await ask();
    api.finishHrInterview.mockRejectedValueOnce(new Error('Feedback unavailable'));
    fireEvent.click(screen.getByRole('button', { name: 'Finish & get feedback' }));
    await screen.findByText('Feedback unavailable');
    expect(screen.getByText('I built a Python scheduling service with a retry queue.')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Finish & get feedback' }));
    await screen.findByRole('region', { name: 'Interviewer feedback' });
    expect(api.askHrCandidate).toHaveBeenCalledTimes(1);
  });

  it('blocks overlapping requests and allows suggestions to be edited before sending', async () => {
    let resolveQuestion;
    api.askHrCandidate.mockImplementationOnce(() => new Promise((resolve) => { resolveQuestion = resolve; }));
    await openSession();
    const suggestion = 'Tell me about yourself and your experience as a Backend engineer.';
    fireEvent.click(screen.getByRole('button', { name: suggestion }));
    expect(screen.getByLabelText('Your interview question').value).toBe(suggestion);
    expect(api.askHrCandidate).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Ask candidate' }));
    expect(screen.getByRole('button', { name: 'Waiting for candidate…' }).disabled).toBe(true);
    fireEvent.submit(screen.getByLabelText('Your interview question').closest('form'));
    expect(api.askHrCandidate).toHaveBeenCalledTimes(1);
    await act(async () => { resolveQuestion(stored); });
  });

  it('reloads a stale session and preserves the question for resubmission', async () => {
    await openSession();
    api.askHrCandidate.mockRejectedValueOnce(Object.assign(new Error('Conversation changed'), { status: 409 }));
    await ask();
    stored = { ...stored, turns: [{ request_id: 'different', question: 'Another tab', answer: 'A saved response', created_at: stored.created_at }] };
    fireEvent.click(screen.getByRole('button', { name: 'Reload session' }));
    await screen.findByText('A saved response');
    expect(screen.getByLabelText('Your interview question').value).toBe('Tell me about a Python project.');
    fireEvent.click(screen.getByRole('button', { name: 'Retry question' }));
    await screen.findByText('I built a Python scheduling service with a retry queue.');
    expect(api.askHrCandidate.mock.calls[1][3]).toBe(1);
  });

  it('offers load retry, validates links and tolerates corrupt browser history', async () => {
    localStorage.setItem('laycall.hr.sessions.v1', '{broken');
    api.getHrInterview.mockRejectedValueOnce(new Error('Connection unavailable'));
    navigate(`hr/${ID}`);
    render(<App />);
    await screen.findByText('Connection unavailable');
    fireEvent.click(screen.getByRole('button', { name: 'Retry loading' }));
    await screen.findByRole('heading', { name: 'Your candidate is ready.' });
    navigate('hr/bad-link');
    await screen.findByRole('heading', { name: 'This session link is invalid.' });
    expect(api.getHrInterview).toHaveBeenCalledTimes(2);
  });

  it('supports editable presets and rejects too many specified skills', async () => {
    render(<App />);
    await screen.findByRole('heading', { name: 'Take the interviewer’s seat.' });
    fireEvent.click(screen.getByRole('button', { name: 'Software engineer' }));
    expect(screen.getByLabelText('Target role').value).toBe('Software engineer');
    fireEvent.click(screen.getByRole('button', { name: 'Remove React' }));
    fireEvent.change(screen.getByLabelText(/Candidate skills/), { target: { value: 'TypeScript' } });
    fireEvent.keyDown(screen.getByLabelText(/Candidate skills/), { key: 'Enter' });
    expect(screen.getByRole('button', { name: 'Remove TypeScript' })).toBeTruthy();
    fireEvent.change(screen.getByLabelText(/Candidate skills/), { target: { value: Array.from({ length: 13 }, (_, i) => `Skill ${i}`).join(',') } });
    expect(screen.getByRole('button', { name: 'Start HR interview' }).disabled).toBe(true);
    expect(screen.getByRole('alert').textContent).toContain('up to 12 skills');
  });
});
