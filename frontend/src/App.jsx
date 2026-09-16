import { useRef, useState } from 'react';
import LeftSidebar from './components/LeftSidebar';
import ChatArea from './components/ChatArea';
import RightSidebar from './components/RightSidebar';
import * as api from './api';

export default function App() {
  const [interviews, setInterviews] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const actionPending = useRef(false);

  const activeInterview = interviews.find((iv) => iv.id === activeId);

  function updateInterview(id, update) {
    setInterviews((previous) => previous.map((iv) => iv.id === id ? update(iv) : iv));
  }

  function beginAction() {
    if (actionPending.current) return false;
    actionPending.current = true;
    setLoading(true);
    setError(null);
    return true;
  }

  function finishAction() {
    actionPending.current = false;
    setLoading(false);
  }

  async function handleSetup(file, jobDescription) {
    if (!beginAction()) return;
    try {
      const iv = await api.createInterview(jobDescription);
      const upload = await api.uploadResume(file, iv.id);
      const ready = upload.questions_generated > 0;
      const newInterview = {
        ...iv,
        status: ready ? 'in_progress' : 'pending',
        questionCount: upload.questions_generated,
        answeredCount: 0,
        currentQuestion: null,
        questionAnswered: false,
        pendingAnswer: null,
        resultsPending: false,
        messages: [{
          role: 'hr',
          text: ready
            ? 'Welcome! Your resume has been uploaded and the interview is ready. Click "Next Question" to begin.'
            : 'Your resume was uploaded, but preparing the questions did not finish. Click "Next Question" to try again.',
        }],
      };
      setInterviews((previous) => [newInterview, ...previous]);
      setActiveId(iv.id);
    } catch (err) {
      setError(err.message);
    } finally {
      finishAction();
    }
  }

  async function loadResults(interviewId, expectingComplete) {
    const results = await api.getInterviewResults(interviewId);
    if (results.status === 'completed' && results.overall_score != null) {
      updateInterview(interviewId, (iv) => ({
        ...iv,
        status: 'completed',
        results,
        resultsPending: false,
        messages: iv.results ? iv.messages : [...iv.messages, {
          role: 'hr', text: 'Interview complete! Here are your results:', results,
        }],
      }));
      return;
    }
    updateInterview(interviewId, (iv) => ({ ...iv, resultsPending: expectingComplete }));
    if (expectingComplete) {
      setError('Your final report is not ready yet. Click "Retry Results" to try again.');
    }
  }

  async function handleNext() {
    const iv = activeInterview;
    if (!iv || iv.status === 'completed' || iv.pendingAnswer
      || (iv.currentQuestion && !iv.questionAnswered) || !beginAction()) return;
    try {
      const q = await api.getNextQuestion(iv.id, iv.currentQuestion?.question_id);
      updateInterview(iv.id, (current) => ({
        ...current,
        status: 'in_progress',
        currentQuestion: q,
        questionAnswered: false,
        messages: [...current.messages, { role: 'hr', text: q.question, questionId: q.question_id }],
      }));
    } catch (err) {
      if (err.status === 404 && err.message === 'No more questions available for this interview') {
        updateInterview(iv.id, (current) => ({ ...current, noMoreQuestions: true, resultsPending: true }));
        try {
          await loadResults(iv.id, true);
        } catch (resultsError) {
          setError(resultsError.message);
        }
      } else {
        setError(err.message);
      }
    } finally {
      finishAction();
    }
  }

  async function evaluateSavedAnswer(iv, answer) {
    const response = await api.evaluateAnswer(iv.id, answer.id);
    const answeredCount = iv.answeredCount + 1;
    updateInterview(iv.id, (current) => ({
      ...current,
      pendingAnswer: null,
      questionAnswered: true,
      answeredCount,
      messages: [...current.messages, {
        role: 'hr', text: 'Here is your evaluation:', evaluation: response.evaluation,
      }],
    }));
    try {
      await loadResults(iv.id, iv.questionCount > 0 && answeredCount >= iv.questionCount);
    } catch (err) {
      updateInterview(iv.id, (current) => ({ ...current, resultsPending: true }));
      setError(err.message);
    }
  }

  async function handleSend(text) {
    const iv = activeInterview;
    if (!iv?.currentQuestion || iv.questionAnswered || iv.pendingAnswer
      || iv.status === 'completed' || !text.trim() || !beginAction()) return false;
    let saved = false;
    try {
      const answer = await api.submitAnswer(iv.id, iv.currentQuestion.question_id, text);
      saved = true;
      updateInterview(iv.id, (current) => ({
        ...current,
        pendingAnswer: answer,
        messages: [...current.messages, { role: 'user', text }],
      }));
      await evaluateSavedAnswer(iv, answer);
    } catch (err) {
      setError(err.message);
    } finally {
      finishAction();
    }
    return saved;
  }

  async function handleRetryEvaluation() {
    const iv = activeInterview;
    if (!iv?.pendingAnswer || !beginAction()) return;
    try {
      await evaluateSavedAnswer(iv, iv.pendingAnswer);
    } catch (err) {
      setError(err.message);
    } finally {
      finishAction();
    }
  }

  async function handleRetryResults() {
    const iv = activeInterview;
    if (!iv || !beginAction()) return;
    try {
      await loadResults(iv.id, true);
    } catch (err) {
      setError(err.message);
    } finally {
      finishAction();
    }
  }

  function handleSelect(id) {
    if (actionPending.current) return;
    setActiveId(id);
    setError(null);
  }

  return (
    <div className="grid grid-cols-[260px_1fr_280px] h-screen overflow-hidden">
      <LeftSidebar
        interviews={interviews}
        activeInterviewId={activeId}
        onSelect={handleSelect}
        onNew={() => handleSelect(null)}
        disabled={loading}
      />
      <ChatArea
        key={activeId ?? 'setup'}
        interview={activeInterview}
        messages={activeInterview?.messages ?? []}
        onSend={handleSend}
        onNext={handleNext}
        onSetup={handleSetup}
        onRetryEvaluation={handleRetryEvaluation}
        onRetryResults={handleRetryResults}
        loading={loading}
        error={error}
      />
      <RightSidebar interview={activeInterview} />
    </div>
  );
}
