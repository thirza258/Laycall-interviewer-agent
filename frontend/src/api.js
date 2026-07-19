const API_BASE = '/api/v1';

async function request(url, options = {}) {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function uploadResume(file, interviewId) {
  const form = new FormData();
  form.append('file', file);
  form.append('interview_id', interviewId);
  const res = await fetch(`${API_BASE}/resumes`, { method: 'POST', body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Upload failed: ${res.status}`);
  }
  return res.json();
}

export async function createInterview(jobDescription, resumeId = null) {
  const body = { job_description: jobDescription };
  if (resumeId) body.resume_id = resumeId;
  return request('/interviews', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function getNextQuestion(interviewId, lastQuestionId) {
  const params = lastQuestionId ? `?last_question_id=${lastQuestionId}` : '';
  return request(`/interviews/${interviewId}/question${params}`);
}

export async function submitAnswer(interviewId, questionId, answer) {
  return request(`/interviews/${interviewId}/answers`, {
    method: 'POST',
    body: JSON.stringify({ question_id: questionId, answer }),
  });
}

export async function evaluateAnswer(interviewId, answerId) {
  return request(`/interviews/${interviewId}/answers/${answerId}/evaluate`, {
    method: 'POST',
  });
}

export async function getInterviewResults(interviewId) {
  return request(`/interviews/${interviewId}/results`);
}

export async function healthCheck() {
  const res = await fetch('/health');
  return res.json();
}
