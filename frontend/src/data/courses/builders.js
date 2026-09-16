// Authoring helpers keep each lesson's teaching, example, exercise and questions together.
export const course = (id, title, description, level, lessons) => ({ id, title, description, level, lessons });
export const lesson = (id, title, summary, steps, example, exercise, questions, minutes = 7) => ({
  id, title, summary, steps, example, exercise, questions, minutes,
});
export const question = (text, focus, guide) => ({ text, focus, guide });
