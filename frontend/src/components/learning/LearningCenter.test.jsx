// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import LearningCenter from './LearningCenter';
import { courses, questions } from '../../data/courses';
import { LEARNING_STORAGE_KEY } from '../../hooks/useLearningProgress';

const firstCourse = courses[0];
const firstLesson = firstCourse.lessons[0];
const libraryRoute = { section: 'courses' };
const lessonRoute = { section: 'courses', courseId: firstCourse.id, lessonId: firstLesson.id };
const bankRoute = { section: 'questions' };
const stored = () => JSON.parse(window.localStorage.getItem(LEARNING_STORAGE_KEY));

beforeEach(() => {
  window.localStorage.clear();
  Element.prototype.scrollIntoView = vi.fn();
  Element.prototype.scrollTo = vi.fn();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('course library', () => {
  it('combines topic and text filters and recovers from empty results', () => {
    render(<LearningCenter route={libraryRoute} />);
    expect(screen.getByRole('status').textContent).toBe('30 courses to explore');
    fireEvent.change(screen.getByLabelText('Course topic'), { target: { value: 'Technical' } });
    expect(screen.getByRole('status').textContent).toBe('5 courses to explore');
    fireEvent.change(screen.getByLabelText('Search courses'), { target: { value: 'database transaction' } });
    expect(screen.getByRole('status').textContent).toBe('1 course to explore');
    expect(screen.getByRole('link', { name: 'Backend APIs, databases and concurrency' })).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Search courses'), { target: { value: 'no-matching-course' } });
    expect(screen.getByText('No courses match your search')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Show all courses' }));
    expect(screen.getByRole('status').textContent).toBe('30 courses to explore');
  });

  it('persists saved courses and filters the library by them', () => {
    const view = render(<LearningCenter route={libraryRoute} />);
    fireEvent.click(screen.getByRole('button', { name: `Save ${firstCourse.title}` }));
    expect(stored().saved).toEqual([firstCourse.id]);
    view.unmount();
    render(<LearningCenter route={libraryRoute} />);
    fireEvent.click(screen.getByRole('button', { name: /Saved courses/ }));
    expect(screen.getByRole('status').textContent).toBe('1 course saved');
    fireEvent.click(screen.getByRole('button', { name: `Unsave ${firstCourse.title}` }));
    expect(screen.getByText('No saved courses match yet')).toBeTruthy();
    expect(stored().saved).toEqual([]);
  });

  it('restores lesson completion and notes and offers the next unfinished lesson', () => {
    const view = render(<LearningCenter route={lessonRoute} />);
    expect(screen.getByRole('heading', { name: firstLesson.title })).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Your notes'), { target: { value: 'My real project example' } });
    fireEvent.click(screen.getByRole('button', { name: 'Mark lesson complete' }));
    expect(stored().completed).toEqual([firstLesson.key]);
    expect(stored().notes[firstLesson.key]).toBe('My real project example');
    view.unmount();

    const restored = render(<LearningCenter route={lessonRoute} />);
    expect(screen.getByLabelText('Your notes').value).toBe('My real project example');
    expect(screen.getByRole('button', { name: /Lesson completed/ }).getAttribute('aria-pressed')).toBe('true');
    restored.rerender(<LearningCenter route={libraryRoute} />);
    expect(screen.getByRole('link', { name: /Continue learning/ }).getAttribute('href'))
      .toBe(`#/courses/${firstCourse.id}/${firstCourse.lessons[1].id}`);
    expect(screen.getByRole('progressbar', { name: `${firstCourse.title} progress` }).value).toBe(1);
    restored.rerender(<LearningCenter route={lessonRoute} />);
    fireEvent.click(screen.getByRole('button', { name: /Lesson completed/ }));
    expect(stored().completed).toEqual([]);
  });

  it('provides syllabus, next and previous links for direct lesson navigation', () => {
    const view = render(<LearningCenter route={{ ...lessonRoute, lessonId: firstCourse.lessons[1].id }} />);
    const syllabus = screen.getByRole('navigation', { name: 'Course lessons' });
    expect(within(syllabus).getByRole('link', { current: 'step' }).getAttribute('href'))
      .toBe(`#/courses/${firstCourse.id}/${firstCourse.lessons[1].id}`);
    expect(screen.getByRole('link', { name: /Previous lesson/ }).getAttribute('href'))
      .toBe(`#/courses/${firstCourse.id}/${firstLesson.id}`);
    expect(screen.getByRole('link', { name: /Next lesson/ }).getAttribute('href'))
      .toBe(`#/courses/${firstCourse.id}/${firstCourse.lessons[2].id}`);
    view.rerender(<LearningCenter route={{ ...lessonRoute, lessonId: firstCourse.lessons[2].id }} />);
    expect(screen.getByRole('link', { name: /Try a mock interview/ }).getAttribute('href')).toBe('#/interviews');
  });

  it.each([
    { section: 'courses', courseId: 'missing' },
    { ...lessonRoute, lessonId: 'missing' },
    { section: 'questions', courseId: 'missing' },
    { ...bankRoute, lessonId: 'unexpected' },
    { ...lessonRoute, extra: true },
  ])('handles invalid course routes without crashing: %j', (route) => {
    render(<LearningCenter route={route} />);
    expect(screen.getByRole('heading', { name: /could not be found/ })).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Browse courses' }).getAttribute('href')).toBe('#/courses');
  });
});

describe('question practice', () => {
  it('paginates the full bank and resets the page when filters change', () => {
    const { container } = render(<LearningCenter route={bankRoute} />);
    expect(container.querySelectorAll('details')).toHaveLength(18);
    expect(screen.getByText('Page 1 of 10')).toBeTruthy();
    expect(screen.getByRole('button', { name: /Previous page/ }).disabled).toBe(true);
    fireEvent.click(screen.getByRole('button', { name: /Next page/ }));
    expect(screen.getByText('Page 2 of 10')).toBeTruthy();
    expect(screen.queryByText(questions[0].text)).toBeNull();
    expect(screen.getByText(questions[18].text)).toBeTruthy();
    expect(document.activeElement).toBe(screen.getByRole('status'));
    fireEvent.change(screen.getByLabelText('Question topic'), { target: { value: 'Technical' } });
    expect(screen.getByRole('status').textContent).toBe('30 questions found');
    expect(screen.getByText('Page 1 of 2')).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Search questions'), { target: { value: 'database transaction' } });
    expect(screen.getByRole('status').textContent).toBe('1 question found');
    expect(screen.getByText('What is a database transaction useful for?')).toBeTruthy();
  });

  it('shares answers and practiced status between a lesson and its question bank', () => {
    const question = firstLesson.questions[0];
    const view = render(<LearningCenter route={lessonRoute} />);
    const card = screen.getByText(question.text).closest('details');
    fireEvent.click(card.querySelector('summary'));
    fireEvent.change(within(card).getByLabelText('Your practice answer'), { target: { value: 'A specific example from my experience.' } });
    fireEvent.click(within(card).getByLabelText('I practiced this question'));
    view.unmount();

    render(<LearningCenter route={{ ...bankRoute, courseId: firstCourse.id }} />);
    expect(screen.getByRole('status').textContent).toBe('6 questions found');
    fireEvent.change(screen.getByLabelText('Practice status'), { target: { value: 'Practiced' } });
    expect(screen.getByRole('status').textContent).toBe('1 question found');
    const restored = screen.getByText(question.text).closest('details');
    fireEvent.click(restored.querySelector('summary'));
    expect(within(restored).getByLabelText('Your practice answer').value).toBe('A specific example from my experience.');
    expect(within(restored).getByLabelText('I practiced this question').checked).toBe(true);
    expect(within(restored).getByRole('link').getAttribute('href')).toBe(`#/courses/${firstCourse.id}/${firstLesson.id}`);
    fireEvent.change(screen.getByLabelText('Practice status'), { target: { value: 'To practice' } });
    expect(screen.getByRole('status').textContent).toBe('5 questions found');
    expect(screen.queryByText(question.text)).toBeNull();
  });

  it('can clear an empty search and keeps a scoped course’s counts independent', () => {
    window.localStorage.setItem(LEARNING_STORAGE_KEY, JSON.stringify({ practiced: [questions[questions.length - 1].id] }));
    render(<LearningCenter route={{ ...bankRoute, courseId: firstCourse.id }} />);
    expect(screen.getByText(/0 questions practiced/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Search questions'), { target: { value: 'no-matching-question' } });
    expect(screen.getByText('No questions match these filters')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }));
    expect(screen.getByRole('status').textContent).toBe('6 questions found');
  });
});

describe('learning storage', () => {
  it('ignores unknown progress keys and limits restored note lengths', () => {
    window.localStorage.setItem(LEARNING_STORAGE_KEY, JSON.stringify({
      completed: [firstLesson.key, firstLesson.key, 'unknown/lesson'],
      saved: ['unknown-course'], practiced: 'invalid',
      notes: { [firstLesson.key]: 'a'.repeat(4000), unknown: 'not a lesson', [questions[0].id]: 42 },
    }));
    render(<LearningCenter route={lessonRoute} />);
    expect(screen.getByText(/1 of 3 lessons complete/)).toBeTruthy();
    expect(screen.getByLabelText('Your notes').value).toHaveLength(3000);
    fireEvent.change(screen.getByLabelText('Your notes'), { target: { value: '' } });
    expect(stored()).toEqual({ completed: [firstLesson.key], saved: [], practiced: [], notes: {} });
  });

  it('recovers from malformed saved data without making the lessons unusable', () => {
    window.localStorage.setItem(LEARNING_STORAGE_KEY, '{bad JSON');
    render(<LearningCenter route={lessonRoute} />);
    expect(screen.getByText(/Saved progress could not be read or written/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Mark lesson complete' }));
    expect(stored().completed).toEqual([firstLesson.key]);
    expect(screen.queryByText(/Saved progress could not be read or written/)).toBeNull();
  });

  it('keeps learning usable when the browser blocks reading or saving progress', () => {
    vi.spyOn(window.Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('Blocked'); });
    vi.spyOn(window.Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Quota exceeded'); });
    render(<LearningCenter route={lessonRoute} />);
    expect(screen.getByText(/Saved progress could not be read or written/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Your notes'), { target: { value: 'Temporary notes' } });
    fireEvent.click(screen.getByRole('button', { name: 'Mark lesson complete' }));
    expect(screen.getByRole('button', { name: /Lesson completed/ })).toBeTruthy();
    expect(screen.getByLabelText('Your notes').value).toBe('Temporary notes');
  });
});
