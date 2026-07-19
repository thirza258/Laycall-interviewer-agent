import { useState, useCallback } from 'react';
import LeftSidebar from './components/LeftSidebar';
import ChatArea from './components/ChatArea';
import RightSidebar from './components/RightSidebar';
import * as api from './api';

export default function App() {
  const [interviews, setInterviews] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const activeInterview = interviews.find((iv) => iv.id === activeId);

  function addMessage(role, text, extra = {}) {
    setMessages((prev) => [...prev, { role, text, ...extra }]);
  }

  const handleSetup = useCallback(async (file, jobDescription) => {
    setLoading(true);
    setError(null);
    try {
      const iv = await api.createInterview(jobDescription);
      const interviewId = iv.id;

      await api.uploadResume(file, interviewId);

      const newInterview = {
        id: interviewId,
        status: 'pending',
        created_at: new Date().toISOString(),
      };

      setInterviews((prev) => [newInterview, ...prev]);
      setActiveId(interviewId);
      setMessages([]);
      addMessage('hr', 'Welcome! Your resume has been uploaded and the interview is ready. Click "Next Question" to begin.');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSend = useCallback(async (text) => {
    if (!activeId) return;
    setLoading(true);
    setError(null);

    try {
      if (!text) {
        const q = await api.getNextQuestion(activeId);
        addMessage('hr', q.question, { questionId: q.question_id });
        setLoading(false);
        return;
      }

      const lastQuestion = [...messages].reverse().find((m) => m.role === 'hr' && m.questionId);
      if (!lastQuestion) {
        setError('No question to answer. Click "Next Question" first.');
        setLoading(false);
        return;
      }

      addMessage('user', text);

      const answer = await api.submitAnswer(activeId, lastQuestion.questionId, text);

      try {
        const evalResult = await api.evaluateAnswer(activeId, answer.id);
        addMessage('hr', 'Here is your evaluation:', { evaluation: evalResult.evaluation });

        try {
          const results = await api.getInterviewResults(activeId);
          if (results.overall_score !== null) {
            addMessage('hr', 'Interview complete! Here are your results:', { results });
            setInterviews((prev) =>
              prev.map((iv) => (iv.id === activeId ? { ...iv, status: 'completed', results } : iv))
            );
          }
        } catch {
          addMessage('hr', 'Click "Next Question" to continue.');
        }
      } catch (evalErr) {
        addMessage('hr', `Evaluation note: ${evalErr.message}`);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [activeId, messages]);

  function handleSelect(id) {
    setActiveId(id);
    setMessages([]);
    setError(null);
    const iv = interviews.find((i) => i.id === id);
    if (iv?.results) {
      addMessage('hr', 'Interview complete! Here are your results:', { results: iv.results });
    }
  }

  function handleNew() {
    setActiveId(null);
    setMessages([]);
    setError(null);
  }

  return (
    <div className="grid grid-cols-[260px_1fr_280px] h-screen overflow-hidden">
      <LeftSidebar
        interviews={interviews}
        activeInterviewId={activeId}
        onSelect={handleSelect}
        onNew={handleNew}
      />
      <ChatArea
        interview={activeInterview}
        messages={messages}
        onSend={handleSend}
        onSetup={handleSetup}
        loading={loading}
        error={error}
      />
      <RightSidebar interview={activeInterview} />
    </div>
  );
}
