import React, { useState } from 'react';

export default function LegalView({ initialTab = 'privacy' }) {
  const [activeTab, setActiveTab] = useState(initialTab === 'terms' ? 'terms' : 'privacy');

  return (
    <main className="flex-1 h-dvh overflow-y-auto bg-[#101022] text-[#e0e0e0] p-6 md:p-10">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Navigation & Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-[#2a2a4a]">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <a href="#/interviews" className="text-xs uppercase tracking-wider font-semibold text-indigo-400 hover:text-indigo-300">
                &larr; Back to Interviews
              </a>
              <span className="text-[#555]">&bull;</span>
              <a href="#/courses" className="text-xs uppercase tracking-wider font-semibold text-indigo-400 hover:text-indigo-300">
                Courses
              </a>
            </div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">Legal &amp; Privacy Information</h1>
            <p className="text-sm text-[#aaa4bc] mt-1">
              Transparency regarding our self-hosted architecture, data handling, and AI services.
            </p>
          </div>

          <div className="flex items-center gap-2 bg-[#1a1a2e] p-1.5 rounded-xl border border-[#2a2a4a] self-start md:self-auto">
            <button
              onClick={() => setActiveTab('privacy')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'privacy'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-[#aaa4bc] hover:text-white hover:bg-[#242039]'
              }`}
            >
              Privacy Policy
            </button>
            <button
              onClick={() => setActiveTab('terms')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'terms'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-[#aaa4bc] hover:text-white hover:bg-[#242039]'
              }`}
            >
              Terms of Service
            </button>
          </div>
        </div>

        {activeTab === 'privacy' ? (
          <div className="space-y-6 bg-[#1a1a2e]/60 border border-[#2a2a4a] rounded-2xl p-6 md:p-8 leading-relaxed">
            <div>
              <h2 className="text-2xl font-bold text-white mb-2">Privacy Policy</h2>
              <p className="text-xs text-[#818cf8]">Last updated: November 2026</p>
            </div>

            <section className="space-y-3">
              <h3 className="text-lg font-semibold text-white">1. Self-Hosted Infrastructure &amp; Zero Data Monetization</h3>
              <p className="text-sm text-[#ccc]">
                Mock Interview is operated as a <strong>fully self-hosted platform</strong>. All user sessions, uploaded resumes,
                job descriptions, practice interview transcripts, audio or text responses, and evaluation scores reside entirely
                on the hosting administrator&apos;s private server infrastructure.
              </p>
              <p className="text-sm text-[#ccc]">
                We do not sell, rent, monetize, or transmit your personal data, resumes, or interview records to third-party data brokers,
                advertisers, or profiling companies.
              </p>
            </section>

            <section className="space-y-3">
              <h3 className="text-lg font-semibold text-white">2. AI Inference via OpenRouter</h3>
              <p className="text-sm text-[#ccc]">
                To provide tailored mock interview questions, simulated HR conversational turns, and detailed candidate performance evaluations,
                the backend connects to generative AI models via <strong>OpenRouter</strong>.
              </p>
              <p className="text-sm text-[#ccc]">
                When an interview is generated or an answer is evaluated, relevant textual prompts (such as job requirements or candidate answers)
                are dispatched securely to OpenRouter for real-time inference. For information on OpenRouter&apos;s data retention, processing standards,
                and privacy guarantees, please review:
              </p>
              <ul className="list-disc pl-5 text-sm text-[#ccc] space-y-1">
                <li>
                  <a
                    href="https://openrouter.ai/privacy"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2"
                  >
                    OpenRouter Privacy Policy
                  </a>
                </li>
                <li>
                  <a
                    href="https://openrouter.ai/terms"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2"
                  >
                    OpenRouter Terms of Service
                  </a>
                </li>
              </ul>
            </section>

            <section className="space-y-3">
              <h3 className="text-lg font-semibold text-white">3. Information Processed</h3>
              <ul className="list-disc pl-5 text-sm text-[#ccc] space-y-1">
                <li><strong>Resume &amp; CV Data:</strong> Text extracted from uploaded resumes is used solely to generate contextual interview questions.</li>
                <li><strong>Interview Transcripts &amp; Audio:</strong> Candidate responses are stored locally in the application database to display feedback history.</li>
                <li><strong>Course &amp; Progress Records:</strong> Learning academy progress and completed lessons are saved in your local session/storage.</li>
              </ul>
            </section>

            <section className="space-y-3">
              <h3 className="text-lg font-semibold text-white">4. User Control &amp; Data Deletion</h3>
              <p className="text-sm text-[#ccc]">
                Since Mock Interview runs on self-hosted instances, users and administrators have full autonomy over their data.
                Interviews and uploaded documents can be removed directly through the application interface or server database management.
              </p>
            </section>

            <section className="space-y-3">
              <h3 className="text-lg font-semibold text-white">5. Privacy Contact</h3>
              <p className="text-sm text-[#ccc]">
                For any privacy questions, inquiries, or data requests, please contact:{" "}
                <a href="mailto:nevatalapp@gmail.com" className="text-indigo-400 hover:text-indigo-300 underline font-medium">
                  nevatalapp@gmail.com
                </a>
              </p>
            </section>
          </div>
        ) : (
          <div className="space-y-6 bg-[#1a1a2e]/60 border border-[#2a2a4a] rounded-2xl p-6 md:p-8 leading-relaxed">
            <div>
              <h2 className="text-2xl font-bold text-white mb-2">Terms of Service</h2>
              <p className="text-xs text-[#818cf8]">Last updated: November 2026</p>
            </div>

            <section className="space-y-3">
              <h3 className="text-lg font-semibold text-white">1. Acceptance of Terms</h3>
              <p className="text-sm text-[#ccc]">
                By accessing or using Mock Interview, you agree to these Terms of Service. If you do not agree, you should refrain from using the application.
              </p>
            </section>

            <section className="space-y-3">
              <h3 className="text-lg font-semibold text-white">2. Educational &amp; Practice Purpose</h3>
              <p className="text-sm text-[#ccc]">
                Mock Interview is an automated practice and educational tool designed to help candidates prepare for job interviews.
                Evaluations, interview scores, and suggestions provided by the AI are simulated approximations and do not guarantee actual job offers or real-world hiring outcomes.
              </p>
            </section>

            <section className="space-y-3">
              <h3 className="text-lg font-semibold text-white">3. Third-Party AI Services (OpenRouter)</h3>
              <p className="text-sm text-[#ccc]">
                By utilizing the interview question generation and response scoring features, you acknowledge that inference requests are routed through OpenRouter.
                Your use of these AI capabilities is subject to:
              </p>
              <ul className="list-disc pl-5 text-sm text-[#ccc] space-y-1">
                <li>
                  <a
                    href="https://openrouter.ai/terms"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2"
                  >
                    OpenRouter Terms of Service
                  </a>
                </li>
                <li>
                  <a
                    href="https://openrouter.ai/privacy"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2"
                  >
                    OpenRouter Privacy Policy
                  </a>
                </li>
              </ul>
            </section>

            <section className="space-y-3">
              <h3 className="text-lg font-semibold text-white">4. Acceptable Use</h3>
              <p className="text-sm text-[#ccc]">
                You agree not to submit malicious payloads, unlawful materials, harmful or abusive content, or intentionally attempt to compromise the self-hosted server or downstream AI APIs.
              </p>
            </section>

            <section className="space-y-3">
              <h3 className="text-lg font-semibold text-white">5. Disclaimer &amp; Limitation of Liability</h3>
              <p className="text-sm text-[#ccc]">
                The software is provided &ldquo;as is&rdquo;, without warranty of any kind, express or implied. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability arising from the use of this software.
              </p>
            </section>

            <section className="space-y-3">
              <h3 className="text-lg font-semibold text-white">6. Inquiries &amp; Contact</h3>
              <p className="text-sm text-[#ccc]">
                For questions regarding these terms, please contact:{" "}
                <a href="mailto:nevatalapp@gmail.com" className="text-indigo-400 hover:text-indigo-300 underline font-medium">
                  nevatalapp@gmail.com
                </a>
              </p>
            </section>
          </div>
        )}

        <footer className="mt-8 pt-6 border-t border-[#2a2a4a] text-center text-xs text-[#888] space-y-1">
          <p>Mock Interview · Self-Hosted Technical &amp; Behavioral Platform</p>
          <p>This project is under nevatal.id for educational purposes.</p>
        </footer>
      </div>
    </main>
  );
}
