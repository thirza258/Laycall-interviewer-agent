import foundations from './foundations';
import behavioral from './behavioral';
import formats from './formats';
import technical from './technical';
import roles from './roles';
import careers from './careers';

export const categories = ['Foundations', 'Behavioral', 'Interview formats', 'Technical', 'Role paths', 'Career moves'];

export const resources = {
  general: { title: 'MIT: Interview preparation', url: 'https://capd.mit.edu/resources/interview-primer/' },
  technical: { title: 'Microsoft: Technical interview preparation', url: 'https://careers.microsoft.com/v2/global/en/hiring-tips/technical-interviewing' },
  web: { title: 'MDN: Client-server fundamentals', url: 'https://developer.mozilla.org/en-US/docs/Learn_web_development/Extensions/Server-side/First_steps/Client-Server_overview' },
  database: { title: 'PostgreSQL: Transactions', url: 'https://www.postgresql.org/docs/current/tutorial-transactions.html' },
};

const groups = [
  { category: 'Foundations', items: foundations },
  { category: 'Behavioral', items: behavioral },
  { category: 'Interview formats', items: formats },
  { category: 'Technical', items: technical },
  { category: 'Role paths', items: roles },
  { category: 'Career moves', items: careers },
];

// Keep course/lesson slugs stable: URLs and saved progress refer to these keys.
export const courses = groups.flatMap(({ category, items }) => items.map((course) => ({
  ...course,
  category,
  minutes: course.lessons.reduce((sum, lesson) => sum + lesson.minutes, 0),
  resources: [
    resources.general,
    ...(category === 'Technical' || ['frontend-engineering', 'data-analytics'].includes(course.id) ? [resources.technical] : []),
    ...(['frontend-engineering', 'backend-api-databases'].includes(course.id) ? [resources.web] : []),
    ...(course.id === 'backend-api-databases' ? [resources.database] : []),
  ],
  lessons: course.lessons.map((lesson) => ({
    ...lesson,
    key: `${course.id}/${lesson.id}`,
    questions: lesson.questions.map((question, index) => ({
      ...question,
      id: `${course.id}/${lesson.id}/${index + 1}`,
      courseId: course.id,
      courseTitle: course.title,
      lessonId: lesson.id,
      category,
    })),
  })),
})));

export const questions = courses.flatMap((course) => course.lessons.flatMap((lesson) => lesson.questions));
export const lessonCount = courses.reduce((total, course) => total + course.lessons.length, 0);
export const courseById = new Map(courses.map((course) => [course.id, course]));

export function courseMatches(course, search) {
  const haystack = [course.title, course.description, course.category, ...course.lessons.flatMap((lesson) => [
    lesson.title, lesson.summary, ...lesson.questions.map((question) => question.text),
  ])].join(' ').toLowerCase();
  return search.toLowerCase().trim().split(/\s+/).every((word) => haystack.includes(word));
}
