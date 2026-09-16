const API_BASE = '/api/v1';

// FastAPI answers a 422 with a list of field errors; passing that array
// straight to Error() renders "[object Object]" in the UI.
export function errorMessage(payload, res) {
  const detail = payload?.detail;
  if (typeof detail === 'string' && detail) return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail.map((item) => item.msg || String(item)).join('; ');
  }
  return `Request failed: ${res.status}`;
}

async function readError(res) {
  const payload = await res.json().catch(() => null);
  const error = new Error(errorMessage(payload, res));
  error.status = res.status;
  return error;
}

async function request(url, options = {}) {
  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  if (!res.ok) {
    throw await readError(res);
  }
  return res.json();
}

export async function uploadResume(file, interviewId) {
  const form = new FormData();
  form.append('file', file);
  form.append('interview_id', interviewId);
  const res = await fetch(`${API_BASE}/resumes`, { method: 'POST', body: form });
  if (!res.ok) {
    throw await readError(res);
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
  if (!res.ok) throw await readError(res);
  return res.json();
}
