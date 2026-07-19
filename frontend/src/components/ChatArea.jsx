import { useState, useRef, useEffect } from 'react';
import hrImg from '../assets/hr.jpg';

export default function ChatArea({ interview, messages, onSend, onSetup, loading, error }) {
  const [input, setInput] = useState('');
  const [setupData, setSetupData] = useState({ jobDescription: '', resumeFile: null });
  const messagesEnd = useRef(null);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  function handleSubmit(e) {
    e.preventDefault();
    if (!input.trim()) return;
    onSend(input.trim());
    setInput('');
  }

  function handleSetupSubmit(e) {
    e.preventDefault();
    if (!setupData.resumeFile || !setupData.jobDescription.trim()) return;
    onSetup(setupData.resumeFile, setupData.jobDescription.trim());
  }

  if (!interview) {
    return (
      <main className="flex flex-col h-screen bg-[#0f0f23] text-[#e0e0e0]">
        <div className="max-w-[560px] mx-auto my-auto py-10 px-6 text-center">
          <h1 className="text-3xl text-white font-bold mb-2">Mock Interview</h1>
          <p className="text-[#888] mb-8">Upload your resume and paste the job description to begin.</p>
          <form className="text-left flex flex-col gap-4" onSubmit={handleSetupSubmit}>
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-semibold text-[#ccc]">Resume (PDF or DOCX)</span>
              <input
                type="file"
                accept=".pdf,.docx"
                className="p-2.5 bg-[#1a1a2e] border border-dashed border-[#444] rounded-lg text-[#ccc] cursor-pointer text-sm"
                onChange={(e) => setSetupData({ ...setupData, resumeFile: e.target.files[0] })}
              />
              {setupData.resumeFile && (
                <span className="text-xs text-indigo-500">{setupData.resumeFile.name}</span>
              )}
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-semibold text-[#ccc]">Job Description</span>
              <textarea
                rows={6}
                placeholder="Paste the job description here..."
                className="p-3 bg-[#1a1a2e] border border-[#333] rounded-lg text-[#e0e0e0] text-sm resize-y font-sans placeholder:text-[#666]"
                value={setupData.jobDescription}
                onChange={(e) => setSetupData({ ...setupData, jobDescription: e.target.value })}
              />
            </label>
            <button
              type="submit"
              disabled={loading || !setupData.resumeFile || !setupData.jobDescription.trim()}
              className="py-3 px-6 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-base font-semibold cursor-pointer transition-colors disabled:bg-[#333] disabled:text-[#666] disabled:cursor-not-allowed"
            >
              {loading ? 'Starting...' : 'Start Interview'}
            </button>
            {error && <p className="text-red-500 text-sm p-2 bg-[#2d1111] rounded-md">{error}</p>}
          </form>
        </div>
      </main>
    );
  }

  return (
    <main className="flex flex-col h-screen bg-[#0f0f23] text-[#e0e0e0]">
      <div className="flex items-center gap-3 px-6 py-4 border-b border-[#1e1e3a] bg-[#12122a]">
        <h2 className="text-[1.05rem] text-white font-semibold m-0">Interview #{interview.id}</h2>
        <span className={`text-[11px] px-2 py-0.5 rounded-xl uppercase font-semibold tracking-wide ${statusColor(interview.status)}`}>
          {interview.status}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-4">
        {messages.length === 0 && !loading && (
          <div className="m-auto text-center text-[#888] flex flex-col items-center gap-4">
            <p>Click "Next Question" to start the interview.</p>
            <button
              className="py-3 px-6 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-base font-semibold cursor-pointer transition-colors"
              onClick={() => onSend('')}
            >
              Next Question
            </button>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-3 max-w-[75%] ${msg.role === 'user' ? 'self-end flex-row-reverse' : 'self-start'}`}
          >
            {msg.role === 'hr' && (
              <div
                className="w-9 h-9 min-w-9 rounded-full border-2 border-indigo-600 bg-cover bg-center"
                style={{ backgroundImage: `url(${hrImg})` }}
              />
            )}
            <div
              className={`px-4 py-3 rounded-xl text-sm leading-relaxed ${
                msg.role === 'hr'
                  ? 'bg-[#1e1e3a] text-[#e0e0e0] rounded-bl-sm'
                  : 'bg-indigo-600 text-white rounded-br-sm'
              }`}
            >
              <p className="m-0 whitespace-pre-wrap">{msg.text}</p>
              {msg.evaluation && (
                <div className="mt-2.5 p-2.5 bg-[#222240] rounded-lg flex flex-wrap gap-3 text-xs text-[#a5b4fc]">
                  <span>Technical: {msg.evaluation.technical_score}/10</span>
                  <span>Communication: {msg.evaluation.communication_score}/10</span>
                  {msg.evaluation.feedback && (
                    <p className="w-full m-0 text-[#ccc] italic">{msg.evaluation.feedback}</p>
                  )}
                </div>
              )}
              {msg.results && (
                <div className="mt-2.5 p-3.5 bg-[#0d2b1a] border border-green-500 rounded-xl text-xs">
                  <h4 className="text-green-500 font-semibold m-0 mb-2.5">Interview Complete!</h4>
                  <div className="grid grid-cols-3 gap-2 mb-2.5 font-semibold">
                    <span>Overall: {msg.results.overall_score}%</span>
                    <span>Technical: {msg.results.technical_score}%</span>
                    <span>Communication: {msg.results.communication_score}%</span>
                  </div>
                  {msg.results.strengths?.length > 0 && (
                    <div>
                      <strong className="block mt-2 text-[#ccc]">Strengths:</strong>
                      <ul className="mt-1 ml-4">{msg.results.strengths.map((s, j) => <li key={j} className="text-[#aaa] text-xs mb-0.5">{s}</li>)}</ul>
                    </div>
                  )}
                  {msg.results.recommendations?.length > 0 && (
                    <div>
                      <strong className="block mt-2 text-[#ccc]">Recommendations:</strong>
                      <ul className="mt-1 ml-4">{msg.results.recommendations.map((r, j) => <li key={j} className="text-[#aaa] text-xs mb-0.5">{r}</li>)}</ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-3 max-w-[75%] self-start">
            <div
              className="w-9 h-9 min-w-9 rounded-full border-2 border-indigo-600 bg-cover bg-center"
              style={{ backgroundImage: `url(${hrImg})` }}
            />
            <div className="px-4 py-3 rounded-xl bg-[#1e1e3a] rounded-bl-sm text-[#888] italic text-sm">Thinking...</div>
          </div>
        )}

        {error && <p className="text-red-500 text-sm p-2 bg-[#2d1111] rounded-md m-0">{error}</p>}
        <div ref={messagesEnd} />
      </div>

      <form className="flex gap-2 px-5 py-3 border-t border-[#1e1e3a] bg-[#12122a]" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Type your answer..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading || interview.status === 'completed'}
          className="flex-1 py-2.5 px-4 bg-[#1a1a2e] border border-[#333] rounded-lg text-[#e0e0e0] text-sm placeholder:text-[#555] disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || !input.trim() || interview.status === 'completed'}
          className="py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-semibold cursor-pointer text-sm transition-colors whitespace-nowrap disabled:bg-[#2a2a3a] disabled:text-[#555] disabled:cursor-not-allowed"
        >
          Send
        </button>
        <button
          type="button"
          disabled={loading || interview.status === 'completed'}
          onClick={() => onSend('')}
          className="py-2.5 px-4 bg-[#222240] hover:bg-[#2e2e52] text-white rounded-lg font-semibold cursor-pointer text-sm transition-colors whitespace-nowrap disabled:bg-[#2a2a3a] disabled:text-[#555] disabled:cursor-not-allowed"
        >
          Next Question
        </button>
      </form>
    </main>
  );
}

function statusColor(status) {
  switch (status) {
    case 'pending': return 'bg-amber-500 text-black';
    case 'in_progress': return 'bg-blue-500 text-white';
    case 'completed': return 'bg-green-500 text-black';
    case 'archived': return 'bg-gray-500 text-white';
    default: return 'bg-gray-600 text-white';
  }
}
