import { useState } from 'react';
import { courses, questions } from '../data/courses';

export const LEARNING_STORAGE_KEY = 'laycall.learning.v1';
const courseIds = new Set(courses.map((course) => course.id));
const lessonIds = new Set(courses.flatMap((course) => course.lessons.map((lesson) => lesson.key)));
const questionIds = new Set(questions.map((question) => question.id));
const noteIds = new Set([...lessonIds, ...questionIds]);
const emptyProgress = () => ({ completed: [], saved: [], practiced: [], notes: {} });

function validList(value, allowed) {
  return Array.isArray(value) ? [...new Set(value.filter((id) => allowed.has(id)))] : [];
}

function readProgress() {
  try {
    const raw = JSON.parse(window.localStorage.getItem(LEARNING_STORAGE_KEY) || '{}');
    const data = raw && typeof raw === 'object' ? raw : {};
    const notes = Object.fromEntries(Object.entries(data.notes || {}).filter(([id, text]) => (
      noteIds.has(id) && typeof text === 'string'
    )).map(([id, text]) => [id, text.slice(0, 3000)]));
    return { progress: {
      completed: validList(data.completed, lessonIds), saved: validList(data.saved, courseIds),
      practiced: validList(data.practiced, questionIds), notes,
    }, persistenceError: false };
  } catch {
    return { progress: emptyProgress(), persistenceError: true };
  }
}

export default function useLearningProgress() {
  const [state, setState] = useState(readProgress);

  function save(progress) {
    let persistenceError = false;
    try {
      window.localStorage.setItem(LEARNING_STORAGE_KEY, JSON.stringify(progress));
    } catch {
      persistenceError = true;
    }
    setState({ progress, persistenceError });
  }

  function toggle(field, id) {
    const previous = state.progress[field];
    save({ ...state.progress, [field]: previous.includes(id) ? previous.filter((item) => item !== id) : [...previous, id] });
  }

  function setNote(id, text) {
    const notes = { ...state.progress.notes };
    if (text) notes[id] = text.slice(0, 3000);
    else delete notes[id];
    save({ ...state.progress, notes });
  }

  return { ...state, toggle, setNote };
}
