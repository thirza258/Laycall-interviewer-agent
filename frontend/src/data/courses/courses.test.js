import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { categories, courses, courseById, courseMatches, lessonCount, questions } from './index';

describe('interview curriculum', () => {
  it('provides complete lessons across all six topics', () => {
    expect(courses.length).toBeGreaterThanOrEqual(30);
    expect(lessonCount).toBeGreaterThanOrEqual(90);
    expect(questions.length).toBeGreaterThanOrEqual(180);
    for (const category of categories) {
      expect(courses.filter((course) => course.category === category).length).toBeGreaterThanOrEqual(5);
    }
    for (const course of courses) {
      expect(course.id).toMatch(/^[a-z0-9-]+$/);
      expect(course.title).toBeTruthy();
      expect(course.description).toBeTruthy();
      expect(course.resources.length).toBeGreaterThan(0);
      for (const lesson of course.lessons) {
        expect(lesson.id).toMatch(/^[a-z0-9-]+$/);
        expect(lesson.summary.length).toBeGreaterThan(100);
        expect(lesson.steps.length).toBeGreaterThanOrEqual(3);
        expect(lesson.steps.every((step) => step.trim().length > 0)).toBe(true);
        expect(lesson.example.length).toBeGreaterThan(50);
        expect(lesson.exercise.length).toBeGreaterThan(20);
        expect(lesson.questions.length).toBeGreaterThanOrEqual(2);
        expect(lesson.minutes).toBeGreaterThan(0);
      }
    }
  });

  it('uses unique keys and valid parent links for bookmarks, notes and deep links', () => {
    expect(new Set(courses.map((course) => course.id)).size).toBe(courses.length);
    expect(new Set(courses.flatMap((course) => course.lessons.map((lesson) => lesson.key))).size).toBe(lessonCount);
    expect(new Set(questions.map((question) => question.id)).size).toBe(questions.length);
    expect(new Set(questions.map((question) => question.text.toLowerCase())).size).toBe(questions.length);
    for (const question of questions) {
      const lesson = courseById.get(question.courseId)?.lessons.find((lesson) => lesson.id === question.lessonId);
      expect(lesson?.questions).toContain(question);
      expect(question.focus.trim()).toBeTruthy();
      expect(question.guide.length).toBeGreaterThan(30);
    }
  });

  it('keeps landing-page counts and course links consistent with the catalog', () => {
    const landing = readFileSync(new URL('../../../index.html', import.meta.url), 'utf8');
    expect(landing).toContain(`${courses.length} courses &middot; ${lessonCount} lessons &middot; ${questions.length} practice questions`);
    const links = [...landing.matchAll(/href="\/app\/#\/courses\/([^"/]+)"/g)];
    expect(links.length).toBeGreaterThanOrEqual(6);
    for (const [, id] of links) expect(courseById.has(id)).toBe(true);
  });

  it('finds lessons and common questions as well as course titles', () => {
    expect(courseMatches(courseById.get('first-job-internships'), ' GREATEST strengths ')).toBe(true);
    expect(courseMatches(courseById.get('backend-api-databases'), 'transaction')).toBe(true);
    expect(courseMatches(courseById.get('star-stories'), 'unrelated-query')).toBe(false);
  });
});
