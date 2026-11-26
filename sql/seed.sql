-- =====================================================================
-- CSCI 341 Assignment 3 - seed data (fictional)
-- Run after schema.sql, e.g.  psql -d conference_db -1 -f sql/seed.sql
--
-- Coverage of the sample-data requirements (see README, "Sample data"):
--   * 15 users: author-only (2,5,9,12,14,15), reviewer-only (3,6,8,11,13),
--     both roles (1,4,7,10)
--   * 12 papers covering all five statuses, 17 versions, 20 reviews
--   * 3 conferences: CADS 2026 (Astana), ISMLS 2026 (Almaty),
--     GDM 2027 (Astana, no papers)
--   * empty tracks 3 and 6; reviewer 6 has no reviews;
--     accepted papers 1,2,3,10 have sessions, accepted paper 4 has none
--   * Amina Aminova is corresponding author of withdrawn papers 7 and 8;
--     withdrawn paper 12 (Amina is NOT corresponding) and rejected paper 11
--     (Amina IS corresponding) must survive task 4.1
--   * empty sessions 3 and 6 are in Astana conferences (deleted by 4.2);
--     empty session 5 is in Almaty (kept)
-- =====================================================================

-- ---------------------------------------------------------------------
-- Users
-- ---------------------------------------------------------------------
INSERT INTO app_user (user_id, given_name, surname, email, affiliation, country, phone_number) VALUES
 ( 1, 'Arman',   'Armanov',     'arman.armanov@example.com',       'Nazarbayev University',                       'Kazakhstan', '+77011234501'),
 ( 2, 'Amina',   'Aminova',     'amina.aminova@example.com',       'Al-Farabi Kazakh National University',        'Kazakhstan', '+77011234502'),
 ( 3, 'Dana',    'Bekova',      'dana.bekova@example.com',         'Nazarbayev University',                       'Kazakhstan', '+77011234503'),
 ( 4, 'Timur',   'Sadykov',     'timur.sadykov@example.com',       'Kazakh-British Technical University',         'Kazakhstan', '+77011234504'),
 ( 5, 'Aigerim', 'Nurlanova',   'aigerim.nurlanova@example.com',   'L.N. Gumilyov Eurasian National University',  'Kazakhstan', '+77011234505'),
 ( 6, 'Daniyar', 'Omarov',      'daniyar.omarov@example.com',      'Satbayev University',                         'Kazakhstan', '+77011234506'),
 ( 7, 'Madina',  'Kassymova',   'madina.kassymova@example.com',    'Astana IT University',                        'Kazakhstan', '+77011234507'),
 ( 8, 'Yerlan',  'Zhakupov',    'yerlan.zhakupov@example.com',     'Nazarbayev University',                       'Kazakhstan', '+77011234508'),
 ( 9, 'Saule',   'Tulegenova',  'saule.tulegenova@example.com',    'Kazakh-British Technical University',         'Kazakhstan', '+77011234509'),
 (10, 'Nurlan',  'Abenov',      'nurlan.abenov@example.com',       'Suleyman Demirel University',                 'Kazakhstan', '+77011234510'),
 (11, 'Gulnara', 'Iskakova',    'gulnara.iskakova@example.com',    'KIMEP University',                            'Kazakhstan', '+77011234511'),
 (12, 'Askar',   'Mukhametov',  'askar.mukhametov@example.com',    'Astana IT University',                        'Kazakhstan', '+77011234512'),
 (13, 'Elena',   'Petrova',     'elena.petrova@example.com',       'Novosibirsk State University',                'Russia',     '+73832345613'),
 (14, 'Marco',   'Rossi',       'marco.rossi@example.com',         'Politecnico di Milano',                       'Italy',      '+390212345614'),
 -- namesake of user 1: shows why task 3.1 identifies the user by e-mail
 (15, 'Arman',   'Armanov',     'arman.armanov.kbtu@example.com',  'Kazakh-British Technical University',         'Kazakhstan', '+77011234515');

INSERT INTO author (author_id, orcid) VALUES
 ( 1, '0000-0002-1825-0097'),
 ( 2, '0000-0001-5109-3700'),
 ( 4, NULL),
 ( 5, '0000-0003-1415-9269'),
 ( 7, NULL),
 ( 9, '0000-0002-7183-4421'),
 (10, '0000-0001-2345-6789'),
 (12, NULL),
 (14, '0000-0003-0000-000X'),
 (15, NULL);

INSERT INTO author_research_area (author_id, area_label) VALUES
 ( 1, 'Databases'), ( 1, 'Query Optimization'),
 ( 2, 'Information Retrieval'), ( 2, 'Privacy-Preserving Computation'),
 ( 4, 'Databases'), ( 4, 'Machine Learning'),
 ( 5, 'Databases'), ( 5, 'Transaction Processing'),
 ( 7, 'Machine Learning'),
 ( 9, 'Machine Learning'), ( 9, 'Databases'),
 (10, 'Machine Learning Systems'), (10, 'Natural Language Processing'),
 (12, 'Query Optimization'), (12, 'Information Retrieval'),
 (14, 'Data Compression'), (14, 'Machine Learning Systems'),
 (15, 'Software Engineering');

INSERT INTO reviewer (reviewer_id, years_experience) VALUES
 ( 1,  6),
 ( 3,  8),
 ( 4,  2),
 ( 6,  4),
 ( 7,  5),
 ( 8,  3),
 (10,  7),
 (11, 10),
 (13,  4);

INSERT INTO reviewer_expertise (reviewer_id, area_label) VALUES
 ( 1, 'Databases'), ( 1, 'Query Optimization'),
 ( 3, 'Databases'), ( 3, 'Data Mining'), ( 3, 'Information Retrieval'),
 ( 4, 'Machine Learning'), ( 4, 'Databases'),
 ( 6, 'Databases'), ( 6, 'Graph Data'),
 ( 7, 'Machine Learning'), ( 7, 'Computer Vision'),
 ( 8, 'Distributed Systems'), ( 8, 'Databases'),
 (10, 'Natural Language Processing'), (10, 'Machine Learning'),
 (11, 'Data Mining'), (11, 'Databases'),
 (13, 'Information Retrieval'), (13, 'Natural Language Processing');

-- ---------------------------------------------------------------------
-- Conferences, hosts, reviewer pools
-- ---------------------------------------------------------------------
INSERT INTO conference (conference_id, name, acronym, description, city, country,
                        start_date, end_date, submission_deadline, review_deadline) VALUES
 (1, 'Central Asian Conference on Database Systems', 'CADS 2026',
     'Annual meeting on data management, query processing and learned database systems.',
     'Astana', 'Kazakhstan', DATE '2026-06-15', DATE '2026-06-17', DATE '2026-02-15', DATE '2026-04-01'),
 (2, 'International Symposium on Machine Learning Systems', 'ISMLS 2026',
     'Systems research for training, serving and evaluating machine learning models.',
     'Almaty', 'Kazakhstan', DATE '2026-09-21', DATE '2026-09-23', DATE '2026-05-01', DATE '2026-07-01'),
 (3, 'Workshop on Graph Data Management', 'GDM 2027',
     'Workshop on graph databases, graph query languages and graph analytics.',
     'Astana', 'Kazakhstan', DATE '2027-04-12', DATE '2027-04-13', DATE '2027-01-15', DATE '2027-02-20');

INSERT INTO conference_host (conference_id, host_name) VALUES
 (1, 'Nazarbayev University'),
 (1, 'L.N. Gumilyov Eurasian National University'),
 (2, 'Kazakh-British Technical University'),
 (2, 'Al-Farabi Kazakh National University'),
 (3, 'Astana IT University');

INSERT INTO conference_reviewer (conference_id, reviewer_id) VALUES
 (1, 1), (1, 3), (1, 4), (1, 7), (1, 8),
 (2, 1), (2, 3), (2, 6), (2, 7), (2, 10), (2, 11), (2, 13),
 (3, 6), (3, 8), (3, 10), (3, 13);

-- ---------------------------------------------------------------------
-- Tracks (coordinators belong to the conference pool)
-- ---------------------------------------------------------------------
INSERT INTO track (track_id, conference_id, name, description, research_area, coordinator_id) VALUES
 (1, 1, 'Data Management and Query Processing', 'Storage, indexing, transactions and query optimization.', 'Databases', 3),
 (2, 1, 'Machine Learning for Data Systems', 'Learned components inside database systems.', 'Machine Learning', 7),
 (3, 1, 'Spatial and Temporal Databases', 'Moving objects, time series and spatial indexing.', 'Databases', 8),           -- empty track
 (4, 2, 'Machine Learning Systems', 'Training and serving infrastructure for machine learning.', 'Machine Learning', 10),
 (5, 2, 'Information Retrieval and NLP', 'Search, ranking and language technologies.', 'Information Retrieval', 13),
 (6, 3, 'Graph Query Processing', 'Evaluation and optimization of graph queries.', 'Databases', 6);                    -- empty track, conference without papers

-- ---------------------------------------------------------------------
-- Sessions (chairs belong to the conference pool)
-- ---------------------------------------------------------------------
INSERT INTO conference_session (session_id, conference_id, title, session_date, start_time, end_time, room_label, chair_id) VALUES
 (1, 1, 'Query Processing I',            DATE '2026-06-15', TIME '10:00', TIME '11:30', 'Hall A',       1),
 (2, 1, 'Learned Database Components',   DATE '2026-06-16', TIME '14:00', TIME '15:30', 'Room 204',     7),
 (3, 1, 'Late-Breaking Results',         DATE '2026-06-17', TIME '09:00', TIME '10:00', 'Room 105',     8),  -- empty, Astana
 (4, 2, 'Training and Serving Systems',  DATE '2026-09-22', TIME '11:00', TIME '12:30', 'Auditorium 1', 10),
 (5, 2, 'Poster Session',                DATE '2026-09-23', TIME '16:00', TIME '17:30', 'Main Foyer',   3),  -- empty, Almaty
 (6, 3, 'Opening Session',               DATE '2027-04-12', TIME '09:00', TIME '10:30', 'Room 301',     6);  -- empty, Astana

-- ---------------------------------------------------------------------
-- Papers
-- ---------------------------------------------------------------------
INSERT INTO paper (paper_id, track_id, title, abstract, submission_date, status, session_id) VALUES
 ( 1, 1, 'Adaptive Indexing for Hybrid Transactional and Analytical Workloads',
   'We present an adaptive indexing scheme that incrementally builds B+-tree partitions in response to mixed transactional and analytical queries, reducing index maintenance cost by up to 40 percent.',
   DATE '2026-02-10', 'accepted', 1),
 ( 2, 1, 'Cost-Based Join Ordering with Learned Cardinality Estimates',
   'This paper combines a classical cost-based optimizer with Machine Learning models that estimate join cardinalities. Experiments on the Join Order Benchmark show more stable plans than histogram-based estimation.',
   DATE '2026-02-12', 'accepted', 1),
 ( 3, 2, 'Learned Query Optimizers in Practice: An Experimental Study',
   'We evaluate five learned query optimizers and report when machine learning improves plan quality over traditional heuristics and when it introduces regressions.',
   DATE '2026-02-14', 'accepted', 2),
 ( 4, 2, 'Workload Forecasting for Autonomous Database Tuning',
   'We forecast query arrival rates with machine-learned seasonal models and use the forecasts to schedule index creation and memory reconfiguration before demand peaks.',
   DATE '2026-02-13', 'accepted', NULL),
 ( 5, 1, 'Compression-Aware Storage Layouts for Column Stores',
   'We study how dictionary and run-length encoding interact with page layout in column stores and propose a cost model for choosing encodings per column.',
   DATE '2026-02-11', 'rejected', NULL),
 ( 6, 1, 'Detecting Isolation Anomalies in Cloud Database Services',
   'We describe a black-box testing tool that detects write skew and lost-update anomalies in managed cloud databases that claim snapshot isolation or serializability.',
   DATE '2026-02-15', 'under review', NULL),
 ( 7, 1, 'Secure Multi-Party Query Processing for Healthcare Data',
   'We propose a protocol for evaluating selection and aggregation queries over horizontally partitioned patient records without revealing individual rows to other hospitals.',
   DATE '2026-02-09', 'withdrawn', NULL),
 ( 8, 2, 'Federated Learning over Relational Data Silos',
   'We show how MACHINE LEARNING models can be trained across relational databases owned by different organizations by pushing feature extraction into SQL views.',
   DATE '2026-02-14', 'withdrawn', NULL),
 ( 9, 2, 'Benchmarking Vector Similarity Search in Relational Engines',
   'We benchmark approximate nearest-neighbour indexes implemented as extensions of open-source relational database systems.',
   DATE '2026-02-15', 'submitted', NULL),
 (10, 4, 'Scalable Training Pipelines for Large Language Models',
   'We describe a data-loading and checkpointing pipeline that keeps accelerators busy when training large machine learning models on shared clusters.',
   DATE '2026-04-28', 'accepted', 4),
 (11, 5, 'Neural Ranking for Kazakh-Language Web Search',
   'We build a test collection for Kazakh web search and compare lexical retrieval with neural re-ranking models fine-tuned on translated queries.',
   DATE '2026-04-25', 'rejected', NULL),
 (12, 5, 'Query Expansion with Large Language Models for Low-Resource Languages',
   'We study prompt-based query expansion for low-resource languages and analyse when generated expansions drift from the user intent.',
   DATE '2026-04-30', 'withdrawn', NULL);

INSERT INTO paper_keyword (paper_id, keyword) VALUES
 ( 1, 'adaptive indexing'), ( 1, 'B+-tree'), ( 1, 'HTAP'),
 ( 2, 'query optimization'), ( 2, 'cardinality estimation'), ( 2, 'join ordering'),
 ( 3, 'learned query optimization'), ( 3, 'benchmarking'),
 ( 4, 'workload forecasting'), ( 4, 'autonomous databases'),
 ( 5, 'column stores'), ( 5, 'compression'),
 ( 6, 'transaction isolation'), ( 6, 'testing'), ( 6, 'cloud databases'),
 ( 7, 'secure computation'), ( 7, 'healthcare'), ( 7, 'query processing'),
 ( 8, 'federated learning'), ( 8, 'relational databases'),
 ( 9, 'vector search'), ( 9, 'benchmarking'),
 (10, 'distributed training'), (10, 'large language models'),
 (11, 'neural ranking'), (11, 'Kazakh language'), (11, 'web search'),
 (12, 'query expansion'), (12, 'large language models'), (12, 'low-resource languages');

INSERT INTO paper_author (paper_id, author_id, author_position, is_corresponding) VALUES
 ( 1,  4, 1, TRUE ), ( 1,  5, 2, FALSE),
 ( 2,  1, 1, TRUE ), ( 2,  9, 2, FALSE),
 ( 3, 12, 1, TRUE ), ( 3,  7, 2, FALSE), ( 3,  5, 3, FALSE),
 ( 4,  9, 1, TRUE ),
 ( 5, 14, 1, TRUE ), ( 5,  4, 2, FALSE),
 ( 6,  5, 1, TRUE ), ( 6, 12, 2, FALSE),
 ( 7,  2, 1, TRUE ), ( 7, 10, 2, FALSE),
 ( 8,  9, 1, FALSE), ( 8,  2, 2, TRUE ),
 ( 9, 10, 1, TRUE ),
 (10, 10, 1, TRUE ), (10, 14, 2, FALSE),
 (11,  2, 1, TRUE ), (11, 12, 2, FALSE),
 (12,  9, 1, TRUE ), (12,  2, 2, FALSE);

INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note) VALUES
 ( 1, 1, '/files/cads2026/paper-01/v1.pdf', TIMESTAMP '2026-02-10 09:15:00', 'Initial submission'),
 ( 1, 2, '/files/cads2026/paper-01/v2.pdf', TIMESTAMP '2026-05-02 18:40:00', 'Camera-ready version'),
 ( 2, 1, '/files/cads2026/paper-02/v1.pdf', TIMESTAMP '2026-02-12 11:00:00', 'Initial submission'),
 ( 2, 2, '/files/cads2026/paper-02/v2.pdf', TIMESTAMP '2026-02-14 16:20:00', 'Fixed typos in Section 3'),
 ( 2, 4, '/files/cads2026/paper-02/v4.pdf', TIMESTAMP '2026-05-03 10:05:00', 'Camera-ready version (draft v3 was never uploaded)'),
 ( 3, 1, '/files/cads2026/paper-03/v1.pdf', TIMESTAMP '2026-02-14 20:00:00', NULL),
 ( 4, 1, '/files/cads2026/paper-04/v1.pdf', TIMESTAMP '2026-02-13 08:30:00', NULL),
 ( 5, 1, '/files/cads2026/paper-05/v1.pdf', TIMESTAMP '2026-02-11 13:45:00', NULL),
 ( 6, 1, '/files/cads2026/paper-06/v1.pdf', TIMESTAMP '2026-02-15 23:10:00', NULL),
 ( 7, 1, '/files/cads2026/paper-07/v1.pdf', TIMESTAMP '2026-02-09 17:00:00', NULL),
 ( 8, 1, '/files/cads2026/paper-08/v1.pdf', TIMESTAMP '2026-02-14 12:00:00', 'Initial submission'),
 ( 8, 2, '/files/cads2026/paper-08/v2.pdf', TIMESTAMP '2026-03-01 09:30:00', 'Added experiments'),
 ( 9, 1, '/files/cads2026/paper-09/v1.pdf', TIMESTAMP '2026-02-15 22:55:00', NULL),
 (10, 1, '/files/ismls2026/paper-10/v1.pdf', TIMESTAMP '2026-04-28 10:00:00', 'Initial submission'),
 (10, 2, '/files/ismls2026/paper-10/v2.pdf', TIMESTAMP '2026-08-01 15:00:00', 'Camera-ready version'),
 (11, 1, '/files/ismls2026/paper-11/v1.pdf', TIMESTAMP '2026-04-25 14:10:00', NULL),
 (12, 1, '/files/ismls2026/paper-12/v1.pdf', TIMESTAMP '2026-04-30 19:45:00', NULL);

-- ---------------------------------------------------------------------
-- Completed reviews (no reviewer reviews a paper they authored)
-- review counts: 1->3, 3->5, 4->3, 6->0, 7->1, 8->3, 10->1, 11->2, 13->2
-- ---------------------------------------------------------------------
INSERT INTO review (review_id, paper_id, reviewer_id, overall_score, recommendation,
                    comments_for_authors, confidential_comments, review_submission_date) VALUES
 ( 1,  1,  1, 5, 'accept', 'Clear motivation and convincing experiments.', NULL, DATE '2026-03-10'),
 ( 2,  1,  3, 4, 'accept', 'Good paper; please compare with cracking-based indexing.', NULL, DATE '2026-03-12'),
 ( 3,  2,  3, 4, 'accept', 'Solid evaluation on JOB.', 'Strong candidate for the best paper shortlist.', DATE '2026-03-14'),
 ( 4,  2,  8, 4, 'accept', 'Well written; the cost model section could be shorter.', NULL, DATE '2026-03-15'),
 ( 5,  3,  1, 5, 'accept', 'Very useful experimental study for practitioners.', NULL, DATE '2026-03-11'),
 ( 6,  3,  3, 5, 'accept', 'Excellent reproducibility package.', NULL, DATE '2026-03-16'),
 ( 7,  3,  4, 4, 'accept', 'Please discuss training overhead in more detail.', NULL, DATE '2026-03-18'),
 ( 8,  4,  4, 4, 'accept', 'Interesting forecasting approach.', NULL, DATE '2026-03-19'),
 ( 9,  4,  8, 3, 'accept', 'Borderline; the baseline set is limited.', 'I would not object to rejection.', DATE '2026-03-20'),
 (10,  5,  1, 2, 'reject', 'The cost model is not validated on real workloads.', NULL, DATE '2026-03-13'),
 (11,  5,  3, 2, 'reject', 'Limited novelty compared with existing column-store work.', NULL, DATE '2026-03-17'),
 (12,  6,  8, 3, 'accept', 'Promising tool; the anomaly taxonomy needs clarification.', NULL, DATE '2026-03-25'),
 (13,  7,  3, 3, 'reject', 'Security proof is incomplete.', NULL, DATE '2026-03-05'),
 (14,  8,  4, 2, 'reject', 'Experiments use only synthetic data.', NULL, DATE '2026-03-21'),
 (15, 10, 11, 5, 'accept', 'Impressive engineering and clear ablations.', NULL, DATE '2026-06-10'),
 (16, 10, 13, 4, 'accept', 'Good paper; add energy measurements.', NULL, DATE '2026-06-12'),
 (17, 10,  7, 4, 'accept', 'Relevant to the community.', NULL, DATE '2026-06-15'),
 (18, 11, 13, 2, 'reject', 'Test collection is too small for the claims made.', NULL, DATE '2026-06-11'),
 (19, 11, 11, 3, 'reject', 'Interesting language resource but weak baselines.', 'Encourage resubmission to a workshop.', DATE '2026-06-18'),
 (20, 12, 10, 2, 'reject', 'Analysis of drift is mostly anecdotal.', NULL, DATE '2026-06-20');

-- ---------------------------------------------------------------------
-- Advance identity sequences past the explicit ids used above
-- ---------------------------------------------------------------------
SELECT setval(pg_get_serial_sequence('app_user', 'user_id'),                (SELECT MAX(user_id) FROM app_user));
SELECT setval(pg_get_serial_sequence('conference', 'conference_id'),        (SELECT MAX(conference_id) FROM conference));
SELECT setval(pg_get_serial_sequence('track', 'track_id'),                  (SELECT MAX(track_id) FROM track));
SELECT setval(pg_get_serial_sequence('conference_session', 'session_id'),   (SELECT MAX(session_id) FROM conference_session));
SELECT setval(pg_get_serial_sequence('paper', 'paper_id'),                  (SELECT MAX(paper_id) FROM paper));
SELECT setval(pg_get_serial_sequence('review', 'review_id'),                (SELECT MAX(review_id) FROM review));
