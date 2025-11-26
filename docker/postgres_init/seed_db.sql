
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT FROM pg_tables
    WHERE schemaname = current_schema() AND tablename = 'user'
  ) THEN
    RAISE NOTICE 'Skipping seed: schema not present (table "user" not found).';
    RETURN;
  END IF;
END$$;

BEGIN;

INSERT INTO "user" (username, email, password_hash, bio, image_url, name, role, failed_login_attempts, created_at)
VALUES (
  'admin',
  'admin@senda.ai',
  '$2b$12$qajUcnFkTYTDX0i0uE1dQujOlBPqUi4ZQBfjYbfMbNc.nfHa1eexO', -- password: admin123
  NULL,
  'https://api.realworld.io/images/smiley-cyrus.jpeg',
  'Administrator',
  'ADMIN',
  0,
  now()
)
ON CONFLICT (username) DO UPDATE
SET email = EXCLUDED.email,
    password_hash = EXCLUDED.password_hash,
    role = 'ADMIN',
    updated_at = now();

INSERT INTO "user" (username, email, password_hash, bio, image_url, name, role, failed_login_attempts, created_at)
VALUES
  ('user1', 'user1@test.com', '$2b$12$aaQcjqZwBdLQHAprQbe3mukbWRPN2l0Va3Ry2yHNGwqZ2zkb9JJge', NULL, 'https://api.realworld.io/images/smiley-cyrus.jpeg', 'user1', 'USER', 0, now())
ON CONFLICT (username) DO NOTHING;

INSERT INTO "user" (username, email, password_hash, bio, image_url, name, role, failed_login_attempts, created_at)
VALUES
  ('user2', 'user2@test.com', '$2b$12$IAZxVCf0zo5Rf.pvsBF1HOn2cw7sjW5RXc2QUu88U/RgtQFmFEb5i', NULL, 'https://api.realworld.io/images/smiley-cyrus.jpeg', 'user2', 'USER', 0, now())
ON CONFLICT (username) DO NOTHING;

WITH admin AS (
  SELECT id AS author_id FROM "user" WHERE username = 'admin' LIMIT 1
)
INSERT INTO course (author_id, slug, title, description, difficulty_level, active, image_placeholder_url, created_at, updated_at)
SELECT admin.author_id, 'senda-seed-course', 'Senda Seed Course', 'This is a seeded course for development', 'BEGINNER', true, NULL, now(), now()
FROM admin
ON CONFLICT (slug) DO NOTHING;

INSERT INTO tag (tag, created_at)
VALUES ('seeded', now()), ('generated', now())
ON CONFLICT (tag) DO NOTHING;

WITH c AS (SELECT id AS course_id FROM course WHERE slug = 'senda-seed-course'),
     t_seeded AS (SELECT id AS tag_id FROM tag WHERE tag = 'seeded'),
     t_generated AS (SELECT id AS tag_id FROM tag WHERE tag = 'generated')
INSERT INTO course_tag (course_id, tag_id, created_at)
SELECT c.course_id, t.tag_id, now() FROM c
CROSS JOIN (SELECT tag_id FROM t_seeded UNION SELECT tag_id FROM t_generated) AS t
ON CONFLICT (course_id, tag_id) DO NOTHING;

WITH c AS (SELECT id AS course_id FROM course WHERE slug = 'senda-seed-course')
INSERT INTO lesson (course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, created_at, updated_at)
SELECT c.course_id, 1, 'Seed Intro', 'Guided practice', 'Notice your breath', 'CALM', 5, 'SCRIPT_COMPLETED', '[{"type":"speak","content":"Welcome to the Senda seed course."}]', now(), now()
FROM c
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = c.course_id AND lesson_number = 1);

WITH c AS (SELECT id AS course_id FROM course WHERE slug = 'senda-seed-course')
INSERT INTO lesson (course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, created_at, updated_at)
SELECT c.course_id, 2, 'Seed Breath Practice', 'Guided practice', 'Anchor attention to breath', 'CALM', 6, 'PENDING', '[{"type":"speak","content":"Now pay attention to your breath."}]', now(), now()
FROM c
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = c.course_id AND lesson_number = 2);

WITH c AS (SELECT id AS course_id FROM course WHERE slug = 'senda-seed-course')
INSERT INTO lesson (course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, created_at, updated_at)
SELECT c.course_id, 3, 'Seed Closing', 'Guided practice', 'Soft open awareness', 'CALM', 4, 'PENDING', '[{"type":"speak","content":"Thank you for practicing with Senda."}]', now(), now()
FROM c
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = c.course_id AND lesson_number = 3);

COMMIT;

--
--
