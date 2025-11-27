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

-- Users
-- Admin User
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

INSERT INTO "user" (username, email, password_hash, bio, image_url, name, role, failed_login_attempts, account_locked_until, last_login, created_at, updated_at)
VALUES
  ('user1', 'user1@test.com', '$2b$12$aaQcjqZwBdLQHAprQbe3mukbWRPN2l0Va3Ry2yHNGwqZ2zkb9JJge', NULL, 'https://api.realworld.io/images/smiley-cyrus.jpeg', 'user1', 'USER', 0, NULL, NULL, '2025-11-27 20:27:52.593640 +00:00', '2025-11-27 20:27:52.593640 +00:00'),
  ('user2', 'user2@test.com', '$2b$12$IAZxVCf0zo5Rf.pvsBF1HOn2cw7sjW5RXc2QUu88U/RgtQFmFEb5i', NULL, 'https://api.realworld.io/images/smiley-cyrus.jpeg', 'user2', 'USER', 0, NULL, NULL, '2025-11-27 20:27:52.593640 +00:00', '2025-11-27 20:27:52.593640 +00:00')
ON CONFLICT (username) DO NOTHING;

-- Tags
INSERT INTO tag (id, tag, created_at)
VALUES
  (3, 'Mindfulness', '2025-11-27 21:49:44.011504 +00:00'),
  (4, 'Meditation', '2025-11-27 21:49:44.011504 +00:00'),
  (5, 'Beginner', '2025-11-27 21:49:44.011504 +00:00'),
  (6, 'Inner Peace', '2025-11-27 21:49:44.011504 +00:00'),
  (7, 'Stress Relief', '2025-11-27 21:49:44.011504 +00:00')
ON CONFLICT (tag) DO NOTHING;

-- Course
WITH admin_user AS (
  SELECT id FROM "user" WHERE username = 'admin' LIMIT 1
)
INSERT INTO course (id, author_id, active, slug, title, description, difficulty_level, image_placeholder_url, created_at, updated_at)
SELECT 2, admin_user.id, FALSE, 'the-definitive-beginner-s-medita-tbr_gx3j', 'The Definitive Beginner''s Meditation Journey: 30 Days to Inner Peace', 'Embark on a transformative 30-day journey designed to lay an unshakeable foundation for your meditation practice. This comprehensive course, meticulously crafted for absolute beginners, demystifies meditation and makes it accessible for everyone. Over four weeks, you will progressively learn core mindfulness techniques, cultivate present moment awareness, develop self-compassion, and integrate peace into your daily life. From mastering breath awareness to navigating thoughts and emotions, you will build essential skills for stress reduction, enhanced focus, and profound inner calm. This isn''t just a course; it''s an invitation to cultivate a lifelong practice that humanity will benefit from for generations.', 'BEGINNER', NULL, '2025-11-27 21:49:44.002541 +00:00', '2025-11-27 21:51:43.390276 +00:00'
FROM admin_user
ON CONFLICT (slug) DO NOTHING;

-- Course Tags
INSERT INTO course_tag (course_id, tag_id, created_at)
VALUES
  (2, 3, '2025-11-27 21:49:44.024068 +00:00'),
  (2, 4, '2025-11-27 21:49:44.024068 +00:00'),
  (2, 5, '2025-11-27 21:49:44.024068 +00:00'),
  (2, 6, '2025-11-27 21:49:44.024068 +00:00'),
  (2, 7, '2025-11-27 21:49:44.024068 +00:00')
ON CONFLICT (course_id, tag_id) DO NOTHING;

-- Lessons
INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 4, 2, 1, 'Day 1: The Invitation to Presence', 'Introduction to seated meditation and basic breath awareness.', 'Meditation is a practice of present moment awareness, accessible to all.', 'Welcoming, gentle, encouraging', 10, 'SCRIPT_COMPLETED', '[{"type": "speak", "content": "Welcome to Senda. It''s a true privilege to walk this first step of the path with you, as we begin ''The Definitive Beginner''s Meditation Journey: 30 Days to Inner Peace.'' This is Lesson 1, ''The Invitation to Presence.'' Today, we explore a profound truth: meditation is a practice of present moment awareness, and it is truly accessible to all.", "duration": null}, {"type": "speak", "content": "To begin, find a comfortable position, seated or lying, with a gentle lift through the spine and relaxed shoulders. Feel the points where your body makes contact with the surface beneath you, anchored and steady. If it feels comfortable, softly close your eyes; if not, allow a soft, downward gaze.", "duration": null}, {"type": "pause", "content": null, "duration": 4.0}, {"type": "speak", "content": "Let''s gently bring your awareness to your breath.", "duration": null}, {"type": "speak", "content": "Notice the natural rhythm.", "duration": null}, {"type": "speak", "content": "The simple in-breath.", "duration": null}, {"type": "speak", "content": "The gentle out-breath.", "duration": null}, {"type": "pause", "content": null, "duration": 60.0}, {"type": "speak", "content": "There''s no need to change anything.", "duration": null}, {"type": "speak", "content": "Simply observe.", "duration": null}, {"type": "speak", "content": "The breath breathing itself.", "duration": null}, {"type": "speak", "content": "Perhaps feel the sensation at your nostrils.", "duration": null}, {"type": "speak", "content": "Or the rise and fall of your abdomen.", "duration": null}, {"type": "pause", "content": null, "duration": 60.0}, {"type": "speak", "content": "Just allowing the breath to be your anchor.", "duration": null}, {"type": "speak", "content": "A simple point of presence.", "duration": null}, {"type": "pause", "content": null, "duration": 60.0}, {"type": "speak", "content": "As you observe your breath, your mind may wander.", "duration": null}, {"type": "speak", "content": "This is entirely natural.", "duration": null}, {"type": "speak", "content": "When you notice your attention has drifted,", "duration": null}, {"type": "speak", "content": "Simply and gently guide it back.", "duration": null}, {"type": "speak", "content": "Back to the sensation of your breath.", "duration": null}, {"type": "speak", "content": "No judgment, just a gentle return.", "duration": null}, {"type": "pause", "content": null, "duration": 90.0}, {"type": "speak", "content": "Each time you return,", "duration": null}, {"type": "speak", "content": "You are strengthening your capacity for presence.", "duration": null}, {"type": "speak", "content": "This is the practice.", "duration": null}, {"type": "pause", "content": null, "duration": 90.0}, {"type": "speak", "content": "As we near the end of this first guided practice, gently broaden your awareness.", "duration": null}, {"type": "speak", "content": "Notice the feeling of your body supported.", "duration": null}, {"type": "speak", "content": "The sounds around you.", "duration": null}, {"type": "speak", "content": "Remember the key point from today: this practice of present moment awareness is always here, always accessible to you.", "duration": null}, {"type": "speak", "content": "This simple invitation to presence is the first step in building an unshakeable foundation for inner peace.", "duration": null}, {"type": "pause", "content": null, "duration": 3.0}, {"type": "speak", "content": "This practice ends, and the journey goes on. Take this awareness with you — carry this simple presence into the rest of your day. Thank you for walking this profound first step of the path with me today.", "duration": null}]', NULL, '2025-11-27 21:51:43.377757', NULL, '2025-11-27 21:49:44.030095 +00:00', '2025-11-27 21:51:43.377757 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 1);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 5, 2, 2, 'Day 2: Finding Your Anchor: The Breath', 'Focused attention on the natural rhythm of the breath.', 'The breath is a constant and available anchor to the present moment.', 'Grounding, calm, focused', 12, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.038194 +00:00', '2025-11-27 21:49:44.038194 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 2);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 6, 2, 3, 'Day 3: The Body as Home: Posture & Sensation', 'Mindful body scan, focusing on comfortable and stable posture.', 'A stable, relaxed body provides a strong foundation for a settled mind.', 'Nurturing, settling, mindful', 12, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.040749 +00:00', '2025-11-27 21:49:44.040749 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 3);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 7, 2, 4, 'Day 4: Befriending Distraction: Working with Thoughts', 'Observing thoughts as mental events, returning gently to the breath.', 'Thoughts are not facts, and we can choose not to follow every thought.', 'Patient, understanding, non-judgmental', 15, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.040749 +00:00', '2025-11-27 21:49:44.040749 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 4);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 8, 2, 5, 'Day 5: Sounds as Objects of Awareness', 'Expanding awareness to include the sounds in the environment.', 'All sensory experiences can serve as anchors for present moment awareness.', 'Expansive, curious, open', 15, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.040749 +00:00', '2025-11-27 21:49:44.040749 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 5);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 9, 2, 6, 'Day 6: Short Sits: Bringing Mindfulness into the Day', 'Guided 3-minute mindful pause, integrating mindfulness into daily activity.', 'You don''t need a lot of time to practice mindfulness; short pauses add up.', 'Practical, empowering, brief', 10, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.052965 +00:00', '2025-11-27 21:49:44.052965 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 6);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 10, 2, 7, 'Day 7: Review & Intention Setting', 'Gentle guided reflection on the week''s experiences and setting intentions.', 'Consistency and kind intention are more valuable than striving for perfection.', 'Reflective, encouraging, affirming', 15, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.056872 +00:00', '2025-11-27 21:49:44.056872 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 7);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 11, 2, 8, 'Day 8: Deepening the Body Scan', 'A more extensive body scan, systematically exploring sensations head to toe.', 'Cultivating intimate awareness of physical sensations anchors us to the present.', 'Detailed, relaxing, observant', 18, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.060848 +00:00', '2025-11-27 21:49:44.060848 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 8);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 12, 2, 9, 'Day 9: Expanding Your Field: Open Awareness', 'Non-directive awareness, allowing whatever arises (thoughts, sounds, sensations) to be noticed.', 'Allowing experiences to be as they are, without grasping or pushing away, fosters peace.', 'Spacious, accepting, non-striving', 18, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.060848 +00:00', '2025-11-27 21:49:44.060848 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 9);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 13, 2, 10, 'Day 10: Walking with Purpose: Mindful Movement', 'Guided walking meditation, focusing on the sensations of the feet and movement.', 'Mindfulness is not confined to sitting; it can be integrated into all daily activities.', 'Active, engaging, grounding', 15, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.068099 +00:00', '2025-11-27 21:49:44.068099 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 10);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 14, 2, 11, 'Day 11: Cultivating Kindness: Metta Meditation Introduction', 'Sending kind wishes to oneself (Metta or Loving-Kindness meditation).', 'Self-compassion is the essential foundation for extending kindness to others.', 'Warm, compassionate, gentle', 18, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.072164 +00:00', '2025-11-27 21:49:44.072164 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 11);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 15, 2, 12, 'Day 12: Mindful Eating/Drinking', 'Experiential practice with a small piece of food or drink, engaging all senses.', 'Engaging all senses brings richness and appreciation to everyday acts.', 'Sensorial, appreciative, present', 15, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.075159 +00:00', '2025-11-27 21:49:44.075159 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 12);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 16, 2, 13, 'Day 13: Working with Difficulties: Finding Space', 'Noticing discomfort (physical or emotional) and creating space around it through awareness.', 'Resistance often amplifies suffering; acceptance creates space for healing.', 'Supportive, gentle, understanding', 20, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.075159 +00:00', '2025-11-27 21:49:44.075159 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 13);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 17, 2, 14, 'Day 14: The Pause: Integrating Practice into Busy Moments', 'Practicing short, informal pauses throughout the day to check in with breath and body.', 'Interrupting autopilot creates opportunities for conscious choice and presence.', 'Practical, empowering, brief', 10, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.081646 +00:00', '2025-11-27 21:49:44.081646 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 14);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 18, 2, 15, 'Day 15: Halfway Review & Renewed Commitment', 'Guided reflection on progress and challenges encountered, re-establishing commitment.', 'Acknowledge your growth and commit to continued practice with self-kindness and patience.', 'Encouraging, hopeful, reflective', 15, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.087524 +00:00', '2025-11-27 21:49:44.087524 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 15);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 19, 2, 16, 'Day 16: Extending Metta: Kindness to Others', 'Sending loving-kindness wishes to loved ones and benefactors.', 'Cultivating compassion expands our capacity for connection and empathy.', 'Loving, expansive, connected', 18, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.087524 +00:00', '2025-11-27 21:49:44.087524 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 16);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 20, 2, 17, 'Day 17: Noting Practice: Labeling Experiences', 'Gently noting or labeling experiences (thinking, feeling, hearing, etc.) as they arise.', 'Labeling helps create a little space between ourselves and our experiences.', 'Clear, precise, observant', 18, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.095287 +00:00', '2025-11-27 21:49:44.095287 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 17);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 21, 2, 18, 'Day 18: Gratitude as Practice', 'Reflecting on and appreciating the good in daily life and practice.', 'Cultivating gratitude shifts our focus towards abundance and connection.', 'Appreciative, warm, uplifting', 15, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.095287 +00:00', '2025-11-27 21:49:44.095287 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 18);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 22, 2, 19, 'Day 19: Impermanence: Observing Change', 'Observing the ever-changing nature of sensations, thoughts, and emotions.', 'Recognizing impermanence reduces our tendency to cling to pleasure and push away pain.', 'Contemplative, wise, accepting', 20, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.109042 +00:00', '2025-11-27 21:49:44.109042 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 19);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 23, 2, 20, 'Day 20: The Body Under Stress: RAIN Practice', 'Using the RAIN framework (Recognize, Allow, Investigate, Nurture) to work with challenging emotions.', 'Skillfully working with difficulty through compassion reduces its power.', 'Supportive, structured, kind', 20, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.115016 +00:00', '2025-11-27 21:49:44.115016 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 20);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 24, 2, 21, 'Day 21: Cultivating Equanimity: Accepting What Is', 'Practice of equanimity: balanced acceptance of the pleasant, unpleasant, and neutral.', 'Equanimity allows us to meet all experiences with a calm, balanced heart.', 'Balanced, stable, accepting', 18, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.118080 +00:00', '2025-11-27 21:49:44.118080 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 21);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 25, 2, 22, 'Day 22: The Practice Deepens: Sitting in Silence', 'Extended period of silent sitting, minimal guidance, exploring your own practice.', 'Your own inner teacher is developing; learn to trust your capacity for presence.', 'Quiet, empowering, spacious', 22, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.118080 +00:00', '2025-11-27 21:49:44.118080 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 22);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 26, 2, 23, 'Day 23: Mindfulness of Daily Activities', 'Bringing present moment awareness to routine tasks (showering, cooking, cleaning).', 'Every moment is an opportunity to practice; daily life is the real dojo.', 'Practical, grounded, engaged', 12, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.134008 +00:00', '2025-11-27 21:49:44.134008 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 23);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 27, 2, 24, 'Day 24: Metta for Difficult People', 'Extending loving-kindness to someone who has caused difficulty or hurt.', 'Practicing kindness towards difficulty frees us from the burden of resentment.', 'Challenging, compassionate, brave', 20, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.138097 +00:00', '2025-11-27 21:49:44.138097 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 24);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 28, 2, 25, 'Day 25: The Witness: Non-Identification', 'Cultivating the capacity to observe experience without identifying with it (thoughts, sensations, emotions).', 'You are not your thoughts, feelings, or sensations; you are the aware space that holds them.', 'Spacious, insightful, liberating', 20, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.138097 +00:00', '2025-11-27 21:49:44.138097 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 25);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 29, 2, 26, 'Day 26: Mindful Communication & Listening', 'Bringing awareness to the practice of listening and speaking with intention.', 'Mindful communication deepens connection and reduces misunderstanding.', 'Relational, clear, intentional', 15, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.142123 +00:00', '2025-11-27 21:49:44.142123 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 26);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 30, 2, 27, 'Day 27: Acceptance and Commitment', 'Accepting what is beyond our control and committing to values-driven action.', 'Acceptance frees us; committed action empowers us to live according to our values.', 'Empowering, purposeful, strong', 18, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.146231 +00:00', '2025-11-27 21:49:44.146231 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 27);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 31, 2, 28, 'Day 28: Boundless Heart: Universal Metta', 'Expanding loving-kindness to all beings, without exception.', 'The heart that is truly open knows no bounds; we are all connected.', 'Universal, boundless, loving', 20, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.146231 +00:00', '2025-11-27 21:49:44.146231 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 28);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 32, 2, 29, 'Day 29: Integrating Your Practice: Commitment to the Path', 'Reflecting on the journey, solidifying commitment, creating a sustainable daily practice plan.', 'This is just the beginning; your practice is a lifelong commitment to yourself and the world.', 'Reflective, hopeful, committed', 20, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.149270 +00:00', '2025-11-27 21:49:44.149270 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 29);

INSERT INTO lesson (id, course_id, lesson_number, title, core_practice, key_point, tone, duration_minutes, status, script, audio_url, script_generated_at, audio_generated_at, created_at, updated_at)
SELECT 33, 2, 30, 'Day 30: The Journey Continues', 'Celebrating completion of the course, reinforcing core teachings, blessing for the path ahead.', 'You have built an unshakeable foundation; now, continue building your house of peace, one breath at a time.', 'Celebratory, encouraging, hopeful', 15, 'PENDING', NULL, NULL, NULL, NULL, '2025-11-27 21:49:44.158289 +00:00', '2025-11-27 21:49:44.158289 +00:00'
WHERE NOT EXISTS (SELECT 1 FROM lesson WHERE course_id = 2 AND lesson_number = 30);

COMMIT;
