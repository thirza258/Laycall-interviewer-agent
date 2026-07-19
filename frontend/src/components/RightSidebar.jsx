import hrImg from '../assets/hr.jpg';

export default function RightSidebar({ interview }) {
  return (
    <aside className="flex flex-col bg-[#1a1a2e] text-[#e0e0e0] h-screen overflow-y-auto p-5 gap-4">
      <div className="text-center pb-4 border-b border-[#2a2a4a]">
        <img
          src={hrImg}
          alt="HR Interviewer"
          className="w-36 h-36 rounded-full object-cover border-[3px] border-indigo-600 mx-auto mb-3"
        />
        <h3 className="text-[1.05rem] text-white font-semibold m-0 mb-1">HR Interviewer</h3>
        <p className="text-xs text-[#888] m-0">AI-Powered Mock Interview</p>
      </div>
      {interview && (
        <div className="flex flex-col gap-2">
          <div className="bg-[#222240] px-3 py-2.5 rounded-lg flex justify-between items-center">
            <span className="text-xs text-[#888]">Interview</span>
            <span className="text-sm font-semibold text-white">#{interview.id}</span>
          </div>
          <div className="bg-[#222240] px-3 py-2.5 rounded-lg flex justify-between items-center">
            <span className="text-xs text-[#888]">Status</span>
            <span className={`text-[11px] px-2 py-0.5 rounded-xl uppercase font-semibold tracking-wide ${statusColor(interview.status)}`}>
              {interview.status}
            </span>
          </div>
          {interview.results && (
            <>
              <div className="bg-[#222240] px-3 py-2.5 rounded-lg flex justify-between items-center">
                <span className="text-xs text-[#888]">Overall Score</span>
                <span className="text-lg font-bold text-green-500">{interview.results.overall_score ?? '-'}%</span>
              </div>
              <div className="bg-[#222240] px-3 py-2.5 rounded-lg flex justify-between items-center">
                <span className="text-xs text-[#888]">Technical</span>
                <span className="text-sm font-semibold text-white">{interview.results.technical_score ?? '-'}%</span>
              </div>
              <div className="bg-[#222240] px-3 py-2.5 rounded-lg flex justify-between items-center">
                <span className="text-xs text-[#888]">Communication</span>
                <span className="text-sm font-semibold text-white">{interview.results.communication_score ?? '-'}%</span>
              </div>
            </>
          )}
        </div>
      )}
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
