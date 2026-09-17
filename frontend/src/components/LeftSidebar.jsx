export default function LeftSidebar({ interviews, activeInterviewId, onSelect, onNew, disabled, section = 'interviews' }) {
  return (
    <aside className="flex flex-col bg-[#1a1a2e] text-[#e0e0e0] h-screen overflow-y-auto">
      <nav aria-label="Main navigation" className="flex flex-col gap-1 px-3 py-4 border-b border-[#2a2a4a]">
        {[
          ['interviews', 'Mock interviews'], ['hr', 'HR interview mode'], ['courses', 'Courses & guides'], ['questions', 'Question bank'],
        ].map(([id, label]) => <a key={id} href={`#/${id}`} aria-current={section === id ? 'page' : undefined}
          aria-disabled={disabled} onClick={(event) => { if (disabled) event.preventDefault(); }}
          className={`px-3 py-2.5 rounded-lg text-sm transition-colors ${section === id ? 'bg-[#30274a] text-[#e4dbff]' : 'text-[#b7b1ca] hover:bg-[#242039]'} ${disabled ? 'opacity-50' : ''}`}>
          {label}
        </a>)}
      </nav>
      {section === 'hr' ? (
        <div className="px-4 py-5">
          <h2 className="text-lg font-semibold text-white mb-4">HR practice</h2>
          <a href="#/hr" className="block rounded-lg bg-indigo-600 hover:bg-indigo-500 px-3.5 py-2.5 text-sm text-white">+ New candidate</a>
          <p className="text-sm text-[#aaa4bc] mt-5 leading-relaxed">You ask the questions. Your AI candidate responds with the skills and experience you choose.</p>
          <p className="text-xs text-[#aaa4bc] mt-4 leading-relaxed">Reopen a saved conversation from Recent HR interviews.</p>
        </div>
      ) : <>
      <div className="flex justify-between items-center px-4 py-5 border-b border-[#2a2a4a]">
        <h2 className="text-lg font-semibold text-white m-0">Interviews</h2>
        <button
          className="bg-indigo-600 hover:bg-indigo-500 text-white px-3.5 py-1.5 rounded-lg text-sm cursor-pointer transition-colors"
          onClick={onNew}
          disabled={disabled}
        >
          + New
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {interviews.length === 0 ? (
          <p className="text-center text-[#888] text-sm py-6 px-3 leading-relaxed">
            No interviews yet.<br />Upload a resume to start.
          </p>
        ) : (
          interviews.map((iv) => (
            <button
              key={iv.id}
              aria-label={`Interview ${iv.id}, ${iv.status}`}
              className={`flex items-center gap-2 w-full p-3 border-none rounded-lg bg-transparent text-[#ccc] cursor-pointer text-left text-sm mb-1 transition-colors hover:bg-[#2a2a4a] ${
                iv.id === activeInterviewId ? 'bg-indigo-600 text-white' : ''
              }`}
              onClick={() => onSelect(iv.id)}
              disabled={disabled}
            >
              <span className="font-semibold text-sm">#{iv.id}</span>
              <span className={`text-[11px] px-2 py-0.5 rounded-xl uppercase font-semibold tracking-wide ${statusColor(iv.status)}`}>
                {iv.status}
              </span>
              <span className={`ml-auto text-xs ${iv.id === activeInterviewId ? 'text-indigo-200' : 'text-[#888]'}`}>
                {new Date(iv.created_at).toLocaleDateString()}
              </span>
            </button>
          ))
        )}
      </div>
      </>}
    </aside>
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
