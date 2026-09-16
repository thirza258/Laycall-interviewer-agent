// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import * as api from './api';

vi.mock('./api');

const evaluation = { technical_score: 8, communication_score: 9, feedback: 'Clear explanation.' };
const partial = { status: 'in_progress', overall_score: null };
const complete = {
  status: 'completed', overall_score: 84, technical_score: 80, communication_score: 90,
  strengths: ['Clear reasoning'], weaknesses: ['Limited database examples'], recommendations: ['Practice system design'],
};

beforeEach(() => {
  vi.resetAllMocks();
  window.history.replaceState({}, '', '/app/');
  window.localStorage.clear();
  Element.prototype.scrollIntoView = vi.fn();
  let nextId = 1;
  api.createInterview.mockImplementation(async () => ({ id: nextId++, status: 'pending', created_at: '2026-09-16T12:00:00Z' }));
  api.uploadResume.mockResolvedValue({ questions_generated: 2 });
  api.getNextQuestion.mockImplementation(async (_id, lastId) => lastId
    ? { question_id: 12, question: 'Describe a difficult bug.' }
    : { question_id: 11, question: 'Explain async/await.' });
  api.submitAnswer.mockResolvedValue({ id: 21 });
  api.evaluateAnswer.mockResolvedValue({ evaluation });
  api.getInterviewResults.mockResolvedValue(partial);
});

afterEach(cleanup);

async function setupInterview() {
  fireEvent.change(screen.getByLabelText(/Resume \(PDF or DOCX\)/), {
    target: { files: [new File(['resume'], 'resume.pdf', { type: 'application/pdf' })] },
  });
  fireEvent.change(screen.getByLabelText('Job Description'), {
    target: { value: 'Experienced Python backend developer.' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Start Interview' }));
  await screen.findByText(/Welcome!/);
}

async function firstQuestion() {
  fireEvent.click(screen.getByRole('button', { name: 'Next Question' }));
  await screen.findByText('Explain async/await.');
}

async function answerQuestion(text = 'It suspends execution while waiting for I/O.') {
  fireEvent.change(screen.getByPlaceholderText('Type your answer...'), { target: { value: text } });
  fireEvent.click(screen.getByRole('button', { name: 'Send' }));
  await waitFor(() => expect(screen.queryByText('Thinking...')).toBeNull());
}

describe('interview flow', () => {
  it('keeps interview progress and the unsent answer when visiting courses', async () => {
    render(<App />);
    await setupInterview();
    await firstQuestion();
    fireEvent.change(screen.getByPlaceholderText('Type your answer...'), { target: { value: 'My draft answer' } });
    act(() => {
      window.history.pushState({}, '', '#/courses/tell-me-about-yourself');
      window.dispatchEvent(new HashChangeEvent('hashchange'));
    });
    await screen.findByRole('heading', { name: 'Answer “Tell me about yourself”' });
    expect(screen.queryByRole('button', { name: 'Send' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Interview 1, in_progress' }));
    await screen.findByRole('button', { name: 'Send' });
    expect(screen.getByPlaceholderText('Type your answer...').value).toBe('My draft answer');
    expect(screen.getByText('Explain async/await.')).toBeTruthy();
    await answerQuestion('My draft answer');
    expect(api.submitAnswer).toHaveBeenCalledWith(1, 11, 'My draft answer');
  });

  it('advances through questions and displays the final report', async () => {
    render(<App />);
    await setupInterview();
    await firstQuestion();
    await answerQuestion();
    expect(screen.getByText('Technical: 8/10')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: 'Next Question' }));
    await screen.findByText('Describe a difficult bug.');
    expect(api.getNextQuestion).toHaveBeenLastCalledWith(1, 11);
    api.getInterviewResults.mockResolvedValue(complete);
    await answerQuestion('I fixed a race condition in a worker queue.');
    expect(api.submitAnswer).toHaveBeenLastCalledWith(1, 12, 'I fixed a race condition in a worker queue.');
    expect(screen.getByText('Overall: 84%')).toBeTruthy();
    expect(screen.getByText('Limited database examples')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Next Question' }).disabled).toBe(true);
  });

  it('preserves messages and progress when switching interviews', async () => {
    render(<App />);
    await setupInterview();
    await firstQuestion();
    await answerQuestion();
    fireEvent.click(screen.getByRole('button', { name: '+ New' }));
    await setupInterview();
    fireEvent.click(screen.getByRole('button', { name: 'Interview 1, in_progress' }));
    expect(screen.getByText('Explain async/await.')).toBeTruthy();
    expect(screen.getByText('Technical: 8/10')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Next Question' }));
    await screen.findByText('Describe a difficult bug.');
    expect(api.getNextQuestion).toHaveBeenLastCalledWith(1, 11);
  });

  it('does not skip an unanswered question or resubmit an evaluated answer', async () => {
    render(<App />);
    await setupInterview();
    await firstQuestion();
    expect(screen.getByRole('button', { name: 'Next Question' }).disabled).toBe(true);
    await answerQuestion();
    expect(screen.getByPlaceholderText('Type your answer...').disabled).toBe(true);
    expect(screen.getByRole('button', { name: 'Next Question' }).disabled).toBe(false);
  });

  it('retries evaluation of the saved answer without posting another answer', async () => {
    api.evaluateAnswer.mockRejectedValueOnce(new Error('Model unavailable'));
    render(<App />);
    await setupInterview();
    await firstQuestion();
    await answerQuestion();
    expect(screen.getByText('Model unavailable')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Next Question' }).disabled).toBe(true);
    fireEvent.click(screen.getByRole('button', { name: 'Retry Evaluation' }));
    await screen.findByText('Technical: 8/10');
    expect(api.submitAnswer).toHaveBeenCalledTimes(1);
    expect(api.evaluateAnswer).toHaveBeenCalledTimes(2);
    expect(api.evaluateAnswer).toHaveBeenLastCalledWith(1, 21);
  });

  it('keeps the draft when saving the answer fails', async () => {
    api.submitAnswer.mockRejectedValueOnce(new Error('Connection lost'));
    render(<App />);
    await setupInterview();
    await firstQuestion();
    await answerQuestion('My unsaved answer');
    expect(screen.getByPlaceholderText('Type your answer...').value).toBe('My unsaved answer');
    expect(screen.queryByText('My unsaved answer')).toBeNull();
    expect(api.evaluateAnswer).not.toHaveBeenCalled();
  });

  it('retries the final report without resubmitting the last answer', async () => {
    api.uploadResume.mockResolvedValue({ questions_generated: 1 });
    render(<App />);
    await setupInterview();
    await firstQuestion();
    await answerQuestion();
    api.getInterviewResults.mockResolvedValue(complete);
    fireEvent.click(screen.getByRole('button', { name: 'Retry Results' }));
    await screen.findByText('Overall: 84%');
    expect(api.submitAnswer).toHaveBeenCalledTimes(1);
    expect(api.evaluateAnswer).toHaveBeenCalledTimes(1);
  });

  it('recovers the report when the question count was unavailable during setup', async () => {
    api.uploadResume.mockResolvedValue({ questions_generated: 0 });
    render(<App />);
    fireEvent.change(screen.getByLabelText(/Resume \(PDF or DOCX\)/), {
      target: { files: [new File(['resume'], 'resume.pdf')] },
    });
    fireEvent.change(screen.getByLabelText('Job Description'), {
      target: { value: 'Experienced Python backend developer.' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Start Interview' }));
    await screen.findByText(/preparing the questions did not finish/);
    await firstQuestion();
    await answerQuestion();
    api.getNextQuestion.mockRejectedValueOnce(Object.assign(
      new Error('No more questions available for this interview'), { status: 404 }
    ));
    fireEvent.click(screen.getByRole('button', { name: 'Next Question' }));
    const retry = await screen.findByRole('button', { name: 'Retry Results' });
    expect(screen.getByRole('button', { name: 'Next Question' }).disabled).toBe(true);
    api.getInterviewResults.mockResolvedValue(complete);
    fireEvent.click(retry);
    await screen.findByText('Overall: 84%');
    expect(api.submitAnswer).toHaveBeenCalledTimes(1);
  });

  it('keeps other question errors available for retry', async () => {
    api.getNextQuestion.mockRejectedValueOnce(Object.assign(new Error('Interview not found'), { status: 404 }));
    render(<App />);
    await setupInterview();
    fireEvent.click(screen.getByRole('button', { name: 'Next Question' }));
    await screen.findByText('Interview not found');
    expect(screen.getByRole('button', { name: 'Next Question' }).disabled).toBe(false);
    expect(api.getInterviewResults).not.toHaveBeenCalled();
    await firstQuestion();
  });
});
