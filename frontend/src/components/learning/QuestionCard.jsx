export default function QuestionCard({ question, learning, showCourse = true }) {
  const practiced = learning.progress.practiced.includes(question.id);
  return (
    <details className="academy-question">
      <summary>
        <span className="academy-question-text">{question.text}</span>
        <span className="academy-question-label">{practiced ? 'Practiced ✓' : 'Answer guide + practice'}</span>
      </summary>
      <div className="academy-question-body">
        {showCourse && <a className="academy-text-link" href={`#/courses/${question.courseId}/${question.lessonId}`}>{question.courseTitle} ↗</a>}
        <h4>What this question explores</h4>
        <p>{question.focus}</p>
        <h4>Build your answer</h4>
        <p>{question.guide}</p>
        <label className="academy-field">
          <span>Your practice answer</span>
          <textarea rows={4} maxLength={3000} placeholder="Use your own experience. Write a few points, then try saying your answer aloud."
            value={learning.progress.notes[question.id] || ''} onChange={(event) => learning.setNote(question.id, event.target.value)} />
        </label>
        <label className="academy-checkbox">
          <input type="checkbox" checked={practiced} onChange={() => learning.toggle('practiced', question.id)} />
          I practiced this question
        </label>
      </div>
    </details>
  );
}
