import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import * as api from './api';

function jsonResponse(body, { ok = true, status = 200 } = {}) {
  return { ok, status, json: async () => body };
}

let fetchMock;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('createInterview', () => {
  it('posts the job description to the versioned path', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ id: 7, status: 'pending' }));

    const result = await api.createInterview('A long job description.');

    expect(result).toEqual({ id: 7, status: 'pending' });
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/v1/interviews');
    expect(options.method).toBe('POST');
    expect(JSON.parse(options.body)).toEqual({ job_description: 'A long job description.' });
    expect(options.headers['Content-Type']).toBe('application/json');
  });

  it('includes the resume id only when given', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ id: 1 }));

    await api.createInterview('desc', 42);

    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      job_description: 'desc',
      resume_id: 42,
    });
  });
});

describe('uploadResume', () => {
  it('sends the file as multipart form data without a JSON content type', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ questions_generated: 12 }));
    const file = new File(['cv'], 'cv.pdf', { type: 'application/pdf' });

    const result = await api.uploadResume(file, 3);

    expect(result.questions_generated).toBe(12);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/v1/resumes');
    expect(options.body).toBeInstanceOf(FormData);
    expect(options.body.get('interview_id')).toBe('3');
    expect(options.headers).toBeUndefined();
  });
});

describe('getNextQuestion', () => {
  it('asks for the first question without a cursor', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ question_id: 1, question: 'Q?' }));

    await api.getNextQuestion(5);

    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/interviews/5/question');
  });

  it('passes the last question id when continuing', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ question_id: 2, question: 'Q2?' }));

    await api.getNextQuestion(5, 1);

    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/interviews/5/question?last_question_id=1');
  });
});

describe('submitAnswer and evaluateAnswer', () => {
  it('posts the answer under the interview', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ id: 9 }));

    await api.submitAnswer(5, 2, 'My answer.');

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/v1/interviews/5/answers');
    expect(JSON.parse(options.body)).toEqual({ question_id: 2, answer: 'My answer.' });
  });

  it('triggers evaluation for a saved answer', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ status: 'success' }));

    await api.evaluateAnswer(5, 9);

    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/interviews/5/answers/9/evaluate');
    expect(fetchMock.mock.calls[0][1].method).toBe('POST');
  });
});

describe('error handling', () => {
  it('surfaces the API detail string', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ detail: 'Interview not found' }, { ok: false, status: 404 })
    );

    await expect(api.getInterviewResults(1)).rejects.toThrow('Interview not found');
  });

  it('flattens FastAPI validation errors instead of rendering [object Object]', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        {
          detail: [
            { loc: ['body', 'answer'], msg: 'String should have at most 5000 characters' },
          ],
        },
        { ok: false, status: 422 }
      )
    );

    await expect(api.submitAnswer(1, 2, 'x')).rejects.toThrow(
      'String should have at most 5000 characters'
    );
  });

  it('falls back to the status code when the body is not JSON', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 502,
      json: async () => {
        throw new Error('not json');
      },
    });

    await expect(api.getNextQuestion(1)).rejects.toThrow('Request failed: 502');
  });

  it('reports upload failures with the API detail', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ detail: 'Invalid file type' }, { ok: false, status: 400 })
    );
    const file = new File(['x'], 'cv.exe');

    await expect(api.uploadResume(file, 1)).rejects.toThrow('Invalid file type');
  });
});

describe('healthCheck', () => {
  it('calls the unversioned health endpoint', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ status: 'healthy', env: 'production' }));

    const result = await api.healthCheck();

    expect(fetchMock.mock.calls[0][0]).toBe('/health');
    expect(result.status).toBe('healthy');
  });
});
