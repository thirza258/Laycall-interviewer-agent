import { useEffect, useRef, useState } from 'react';
import { categories, courses, courseById, courseMatches, lessonCount, questions } from '../../data/courses';
import useLearningProgress from '../../hooks/useLearningProgress';
import QuestionCard from './QuestionCard';
import './learning.css';

const courseHref = (course) => `#/courses/${course.id}`;
const completedLessons = (course, progress) => course.lessons.filter((lesson) => progress.completed.includes(lesson.key)).length;

function CourseCard({ course, index, learning }) {
  const completed = completedLessons(course, learning.progress);
  const nextLesson = course.lessons.find((lesson) => !learning.progress.completed.includes(lesson.key)) || course.lessons[0];
  const saved = learning.progress.saved.includes(course.id);
  return (
    <article className="academy-course-card">
      <div className="academy-card-top"><span className="academy-category">{course.category}</span><span className="academy-course-number">{String(index + 1).padStart(2, '0')}</span></div>
      <h3><a href={courseHref(course)}>{course.title}</a></h3>
      <p>{course.description}</p>
      <div className="academy-course-meta"><span>{course.lessons.length} lessons</span><span>~{course.minutes} min</span><span>{course.level}</span></div>
      <progress value={completed} max={course.lessons.length} aria-label={`${course.title} progress`} />
      <div className="academy-card-bottom">
        <a className="academy-text-link" href={`${courseHref(course)}/${nextLesson.id}`}>{completed === course.lessons.length ? 'Review course' : completed ? 'Continue course' : 'Start course'} <span aria-hidden="true">→</span></a>
        <button className="academy-save" aria-label={`${saved ? 'Unsave' : 'Save'} ${course.title}`} aria-pressed={saved} onClick={() => learning.toggle('saved', course.id)}>{saved ? '★ Saved' : '☆ Save'}</button>
      </div>
      {completed > 0 && <span className="academy-progress-caption">{completed} of {course.lessons.length} lessons complete</span>}
    </article>
  );
}

function CourseLibrary({ learning }) {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('All topics');
  const [savedOnly, setSavedOnly] = useState(false);
  const filtered = courses.filter((course) => (category === 'All topics' || course.category === category)
    && (!savedOnly || learning.progress.saved.includes(course.id)) && courseMatches(course, search));
  const inProgress = courses.find((course) => {
    const done = completedLessons(course, learning.progress);
    return done > 0 && done < course.lessons.length;
  });

  return <>
    <section className="academy-hero">
      <div>
        <p className="academy-eyebrow">THE INTERVIEW ACADEMY</p>
        <h1>A little preparation.<br /><span>A lot more confidence.</span></h1>
        <p className="academy-intro">Learn how to explain your experience, handle common questions and show your thinking. Then put it into practice.</p>
        <div className="academy-actions"><a className="academy-primary" href={courseHref(courses[0])}>Start with the basics <span aria-hidden="true">→</span></a><a className="academy-secondary" href="#/questions">Explore the question bank</a></div>
      </div>
      <aside className="academy-learning-plan">
        <span className="academy-plan-label">YOUR NEXT GOOD ANSWER STARTS HERE</span>
        <ol><li><b>01</b><div><strong>Learn the approach</strong><span>Short lessons with concrete examples.</span></div></li><li><b>02</b><div><strong>Make it your own</strong><span>Practice with your real experience.</span></div></li><li><b>03</b><div><strong>Try a mock interview</strong><span>Get feedback tailored to your resume.</span></div></li></ol>
        <a className="academy-text-link" href="#/interviews">Open interview practice →</a>
      </aside>
    </section>
    <div className="academy-stats"><span><strong>{courses.length}</strong> courses</span><span><strong>{lessonCount}</strong> lessons</span><span><strong>{questions.length}</strong> practice questions</span><span><strong>{learning.progress.completed.length}</strong> lessons completed</span></div>
    {inProgress && <div className="academy-resume"><div><span className="academy-eyebrow">PICK UP WHERE YOU LEFT OFF</span><strong>{inProgress.title}</strong></div><a className="academy-text-link" href={`${courseHref(inProgress)}/${inProgress.lessons.find((lesson) => !learning.progress.completed.includes(lesson.key)).id}`}>Continue learning →</a></div>}
    <div className="academy-section-heading"><div><h2>Find your next course</h2><p>Start anywhere. Every course includes examples and guided practice.</p></div></div>
    <div className="academy-filters">
      <label className="academy-search"><span className="sr-only">Search courses</span><input type="search" placeholder="Search skills, topics or questions…" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
      <label className="academy-select"><span className="sr-only">Course topic</span><select value={category} onChange={(event) => setCategory(event.target.value)}><option>All topics</option>{categories.map((item) => <option key={item}>{item}</option>)}</select></label>
      <button className={`academy-filter-button ${savedOnly ? 'is-active' : ''}`} aria-pressed={savedOnly} onClick={() => setSavedOnly(!savedOnly)}>☆ Saved courses</button>
    </div>
    <p className="academy-count" role="status">{filtered.length} {filtered.length === 1 ? 'course' : 'courses'}{savedOnly ? ' saved' : ' to explore'}</p>
    <div className="academy-course-grid">{filtered.map((course) => <CourseCard key={course.id} course={course} index={courses.indexOf(course)} learning={learning} />)}</div>
    {filtered.length === 0 && <div className="academy-empty"><h3>{savedOnly ? 'No saved courses match yet' : 'No courses match your search'}</h3><p>Try another topic or a shorter search.</p><button className="academy-secondary" onClick={() => { setSearch(''); setCategory('All topics'); setSavedOnly(false); }}>Show all courses</button></div>}
  </>;
}

function CourseReader({ course, lessonId, learning }) {
  const lesson = lessonId ? course.lessons.find((item) => item.id === lessonId) : course.lessons[0];
  if (!lesson) return <NotFound />;
  const index = course.lessons.indexOf(lesson);
  const completed = learning.progress.completed.includes(lesson.key);
  const next = course.lessons[index + 1];
  const previous = course.lessons[index - 1];
  return <>
    <a className="academy-text-link" href="#/courses">← All courses</a>
    <header className="academy-course-header"><p className="academy-eyebrow">{course.category} · {course.level}</p><h1>{course.title}</h1><p>{course.description}</p><span className="academy-course-meta">{completedLessons(course, learning.progress)} of {course.lessons.length} lessons complete · About {course.minutes} minutes including exercises</span></header>
    <div className="academy-reader-grid">
      <aside className="academy-syllabus"><h2>In this course</h2><nav aria-label="Course lessons">{course.lessons.map((item, itemIndex) => <a key={item.id} aria-current={item.id === lesson.id ? 'step' : undefined} href={`${courseHref(course)}/${item.id}`}><span className="academy-lesson-number">{learning.progress.completed.includes(item.key) ? '✓' : String(itemIndex + 1).padStart(2, '0')}</span><span>{item.title}<small>{item.minutes} min</small></span></a>)}</nav><a className="academy-text-link" href={`#/questions/${course.id}`}>Practice this course’s questions →</a></aside>
      <article className="academy-lesson">
        <p className="academy-eyebrow">LESSON {index + 1} OF {course.lessons.length}</p><h2>{lesson.title}</h2><p className="academy-lesson-summary">{lesson.summary}</p>
        <h3>Put it into practice</h3><ol className="academy-steps">{lesson.steps.map((step) => <li key={step}>{step}</li>)}</ol>
        <div className="academy-example"><h3>An example</h3><p>{lesson.example}</p><small>Illustrative example. Adapt the structure to your own experience and use only results you can support.</small></div>
        <section className="academy-exercise"><p className="academy-eyebrow">YOUR TURN</p><h3>A small exercise</h3><p>{lesson.exercise}</p><label className="academy-field"><span>Your notes</span><textarea maxLength={3000} rows={4} placeholder="Capture a real example or a few points to practice…" value={learning.progress.notes[lesson.key] || ''} onChange={(event) => learning.setNote(lesson.key, event.target.value)} /></label></section>
        <section className="academy-lesson-questions"><h3>Questions to rehearse</h3><p>Try answering aloud before opening each guide. These are practice prompts, not a prediction of any employer’s questions.</p>{lesson.questions.map((question) => <QuestionCard key={question.id} question={question} learning={learning} showCourse={false} />)}</section>
        <div className="academy-lesson-actions"><button className={completed ? 'academy-secondary is-complete' : 'academy-primary'} aria-pressed={completed} onClick={() => learning.toggle('completed', lesson.key)}>{completed ? '✓ Lesson completed' : 'Mark lesson complete'}</button>{next ? <a className="academy-text-link" href={`${courseHref(course)}/${next.id}`}>Next lesson →</a> : <a className="academy-text-link" href="#/interviews">Try a mock interview →</a>}</div>
        {previous && <a className="academy-previous" href={`${courseHref(course)}/${previous.id}`}>← Previous lesson</a>}
        <div className="academy-resources"><h3>Further reading</h3>{course.resources.map((resource) => <a key={resource.url} href={resource.url} target="_blank" rel="noreferrer">{resource.title} ↗</a>)}</div>
      </article>
    </div>
  </>;
}

function QuestionBank({ courseId, learning }) {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('All topics');
  const [practiceFilter, setPracticeFilter] = useState('All questions');
  const [page, setPage] = useState(0);
  const resultHeading = useRef(null);
  const course = courseById.get(courseId);
  if (courseId && !course) return <NotFound />;
  const words = search.toLowerCase().trim().split(/\s+/);
  const filtered = questions.filter((question) => (!courseId || question.courseId === courseId)
    && (category === 'All topics' || question.category === category)
    && (practiceFilter === 'All questions' || learning.progress.practiced.includes(question.id) === (practiceFilter === 'Practiced'))
    && words.every((word) => `${question.text} ${question.focus} ${question.guide} ${question.courseTitle}`.toLowerCase().includes(word)));
  const pageSize = 18;
  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  const currentPage = Math.min(page, pageCount - 1);
  const practicedCount = questions.filter((question) => (!courseId || question.courseId === courseId)
    && learning.progress.practiced.includes(question.id)).length;

  function changePage(nextPage) {
    setPage(nextPage);
    resultHeading.current?.scrollIntoView({ block: 'start' });
    resultHeading.current?.focus({ preventScroll: true });
  }

  return <>
    <a className="academy-text-link" href={course ? courseHref(course) : '#/courses'}>← {course ? 'Back to course' : 'All courses'}</a>
    <header className="academy-course-header"><p className="academy-eyebrow">THINK IT THROUGH. SAY IT OUT LOUD.</p><h1>{course ? 'Practice this course' : 'The question bank'}</h1><p>{course ? course.title : `${questions.length} questions with answer guides, space to practice and a link to the lesson behind each one.`}</p><span className="academy-course-meta">{practicedCount} questions practiced · Self-guided practice, without AI scoring</span></header>
    <div className="academy-filters">
      <label className="academy-search"><span className="sr-only">Search questions</span><input type="search" value={search} placeholder="Search a question or skill…" onChange={(event) => { setSearch(event.target.value); setPage(0); }} /></label>
      {!course && <label className="academy-select"><span className="sr-only">Question topic</span><select value={category} onChange={(event) => { setCategory(event.target.value); setPage(0); }}><option>All topics</option>{categories.map((item) => <option key={item}>{item}</option>)}</select></label>}
      <label className="academy-select"><span className="sr-only">Practice status</span><select value={practiceFilter} onChange={(event) => { setPracticeFilter(event.target.value); setPage(0); }}><option>All questions</option><option>To practice</option><option>Practiced</option></select></label>
    </div>
    <p className="academy-count" role="status" tabIndex={-1} ref={resultHeading}>{filtered.length} {filtered.length === 1 ? 'question' : 'questions'} found</p>
    <div className="academy-question-list">{filtered.slice(currentPage * pageSize, (currentPage + 1) * pageSize).map((question) => <QuestionCard key={question.id} question={question} learning={learning} />)}</div>
    {filtered.length === 0 && <div className="academy-empty"><h2>No questions match these filters</h2><button className="academy-secondary" onClick={() => { setSearch(''); setCategory('All topics'); setPracticeFilter('All questions'); setPage(0); }}>Clear filters</button></div>}
    {pageCount > 1 && <nav className="academy-pagination" aria-label="Question pages"><button className="academy-secondary" disabled={currentPage === 0} onClick={() => changePage(currentPage - 1)}>← Previous page</button><span>Page {currentPage + 1} of {pageCount}</span><button className="academy-secondary" disabled={currentPage + 1 === pageCount} onClick={() => changePage(currentPage + 1)}>Next page →</button></nav>}
  </>;
}

function NotFound() {
  return <div className="academy-empty"><h1>This lesson could not be found</h1><p>Choose another lesson from the course library.</p><a className="academy-primary" href="#/courses">Browse courses</a></div>;
}

export default function LearningCenter({ route }) {
  const learning = useLearningProgress();
  const main = useRef(null);
  const course = courseById.get(route.courseId);
  useEffect(() => {
    document.title = `${route.section === 'questions' ? 'Question bank' : course?.title || 'Interview courses'} | My Mock Interview`;
    main.current?.scrollTo?.({ top: 0 });
  }, [route.section, route.courseId, route.lessonId, course]);
  return (
    <main className="learning-page" ref={main} id="learning-content">
      <div className="academy-topbar"><a href="/">My Mock Interview <span>/ Learn</span></a><nav aria-label="Learning navigation"><a aria-current={route.section === 'courses' ? 'page' : undefined} href="#/courses">Courses</a><a aria-current={route.section === 'questions' ? 'page' : undefined} href="#/questions">Question bank</a><a href="#/interviews">Mock interview ↗</a></nav></div>
      <div className="academy-content">
        {learning.persistenceError && <p className="academy-storage-warning" role="status">Saved progress could not be read or written. You can keep learning, but this session’s changes may not survive a reload.</p>}
        {route.extra || (route.section === 'questions' && route.lessonId) ? <NotFound /> : route.section === 'questions'
          ? <QuestionBank key={route.courseId || 'all'} courseId={route.courseId} learning={learning} />
          : route.courseId ? (course ? <CourseReader course={course} lessonId={route.lessonId} learning={learning} /> : <NotFound />)
            : <CourseLibrary learning={learning} />}
        <footer className="academy-footer"><span>Learn at your own pace. Use your own stories.</span><span>Progress, saved courses and notes stay in this browser.</span></footer>
      </div>
    </main>
  );
}
