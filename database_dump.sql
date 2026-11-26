-- CSCI 341 Assignment 3 - plain SQL export of the schema, seed data and view.
-- Generated with: pg_dump --no-owner --no-privileges -d conference_db -f database_dump.sql (pg_dump 16.15)
-- The \restrict/\unrestrict psql meta-commands added by recent pg_dump releases were removed so the file
-- also runs in older psql versions and in GUI query tools.
-- Restore into an EMPTY database:  psql -d conference_db -f database_dump.sql

--
-- PostgreSQL database dump
--


-- Dumped from database version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: app_user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.app_user (
    user_id integer NOT NULL,
    given_name character varying(100) NOT NULL,
    surname character varying(100) NOT NULL,
    email character varying(255) NOT NULL,
    affiliation character varying(200) NOT NULL,
    country character varying(100) NOT NULL,
    phone_number character varying(30) NOT NULL,
    CONSTRAINT ck_app_user_email_format CHECK ((POSITION(('@'::text) IN (email)) > 1)),
    CONSTRAINT ck_app_user_names_not_blank CHECK (((TRIM(BOTH FROM given_name) <> ''::text) AND (TRIM(BOTH FROM surname) <> ''::text))),
    CONSTRAINT ck_app_user_phone_format CHECK (((phone_number)::text ~ '^[+]?[0-9 ()-]{5,30}$'::text))
);


--
-- Name: conference; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conference (
    conference_id integer NOT NULL,
    name character varying(200) NOT NULL,
    acronym character varying(30) NOT NULL,
    description text NOT NULL,
    city character varying(100) NOT NULL,
    country character varying(100) NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    submission_deadline date NOT NULL,
    review_deadline date NOT NULL,
    CONSTRAINT ck_conference_dates CHECK ((end_date >= start_date)),
    CONSTRAINT ck_conference_deadlines CHECK ((review_deadline >= submission_deadline))
);


--
-- Name: conference_session; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conference_session (
    session_id integer NOT NULL,
    conference_id integer NOT NULL,
    title character varying(200) NOT NULL,
    session_date date NOT NULL,
    start_time time(0) without time zone NOT NULL,
    end_time time(0) without time zone NOT NULL,
    room_label character varying(100) NOT NULL,
    chair_id integer NOT NULL,
    CONSTRAINT ck_session_times CHECK ((end_time > start_time))
);


--
-- Name: paper; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.paper (
    paper_id integer NOT NULL,
    track_id integer NOT NULL,
    title character varying(300) NOT NULL,
    abstract text NOT NULL,
    submission_date date NOT NULL,
    status character varying(20) DEFAULT 'submitted'::character varying NOT NULL,
    session_id integer,
    CONSTRAINT ck_paper_session_requires_accepted CHECK (((session_id IS NULL) OR ((status)::text = 'accepted'::text))),
    CONSTRAINT ck_paper_status CHECK (((status)::text = ANY ((ARRAY['submitted'::character varying, 'under review'::character varying, 'accepted'::character varying, 'rejected'::character varying, 'withdrawn'::character varying])::text[])))
);


--
-- Name: paper_author; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.paper_author (
    paper_id integer NOT NULL,
    author_id integer NOT NULL,
    author_position integer NOT NULL,
    is_corresponding boolean DEFAULT false NOT NULL,
    CONSTRAINT ck_pa_position_positive CHECK ((author_position > 0))
);


--
-- Name: track; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.track (
    track_id integer NOT NULL,
    conference_id integer NOT NULL,
    name character varying(200) NOT NULL,
    description text NOT NULL,
    research_area character varying(100) NOT NULL,
    coordinator_id integer NOT NULL
);


--
-- Name: accepted_paper_schedule; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.accepted_paper_schedule AS
 SELECT p.paper_id,
    p.title AS paper_title,
    c.conference_id,
    c.acronym AS conference_acronym,
    t.name AS track_name,
    s.session_id,
    s.title AS session_title,
    s.session_date,
    s.start_time,
    s.end_time,
    s.room_label,
    (((ch.given_name)::text || ' '::text) || (ch.surname)::text) AS chair_full_name,
    (((ca.given_name)::text || ' '::text) || (ca.surname)::text) AS corresponding_author_full_name,
    ca.email AS corresponding_author_email
   FROM ((((((public.paper p
     JOIN public.conference_session s ON ((s.session_id = p.session_id)))
     JOIN public.conference c ON ((c.conference_id = s.conference_id)))
     JOIN public.track t ON ((t.track_id = p.track_id)))
     JOIN public.app_user ch ON ((ch.user_id = s.chair_id)))
     LEFT JOIN public.paper_author pa ON (((pa.paper_id = p.paper_id) AND pa.is_corresponding)))
     LEFT JOIN public.app_user ca ON ((ca.user_id = pa.author_id)))
  WHERE ((p.status)::text = 'accepted'::text);


--
-- Name: app_user_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.app_user ALTER COLUMN user_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.app_user_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: author; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.author (
    author_id integer NOT NULL,
    orcid character varying(19),
    CONSTRAINT ck_author_orcid_format CHECK (((orcid IS NULL) OR ((orcid)::text ~ '^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$'::text)))
);


--
-- Name: author_research_area; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.author_research_area (
    author_id integer NOT NULL,
    area_label character varying(100) NOT NULL,
    CONSTRAINT ck_ara_label_not_blank CHECK ((TRIM(BOTH FROM area_label) <> ''::text))
);


--
-- Name: conference_conference_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.conference ALTER COLUMN conference_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.conference_conference_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: conference_host; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conference_host (
    conference_id integer NOT NULL,
    host_name character varying(200) NOT NULL,
    CONSTRAINT ck_ch_host_not_blank CHECK ((TRIM(BOTH FROM host_name) <> ''::text))
);


--
-- Name: conference_reviewer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conference_reviewer (
    conference_id integer NOT NULL,
    reviewer_id integer NOT NULL
);


--
-- Name: conference_session_session_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.conference_session ALTER COLUMN session_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.conference_session_session_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: paper_keyword; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.paper_keyword (
    paper_id integer NOT NULL,
    keyword character varying(100) NOT NULL,
    CONSTRAINT ck_pk_keyword_not_blank CHECK ((TRIM(BOTH FROM keyword) <> ''::text))
);


--
-- Name: paper_paper_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.paper ALTER COLUMN paper_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.paper_paper_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: paper_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.paper_version (
    paper_id integer NOT NULL,
    version_no integer NOT NULL,
    file_location character varying(500) NOT NULL,
    uploaded_at timestamp(0) without time zone DEFAULT LOCALTIMESTAMP(0) NOT NULL,
    change_note text,
    CONSTRAINT ck_pv_location_not_blank CHECK ((TRIM(BOTH FROM file_location) <> ''::text)),
    CONSTRAINT ck_pv_version_positive CHECK ((version_no > 0))
);


--
-- Name: review; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.review (
    review_id integer NOT NULL,
    paper_id integer NOT NULL,
    reviewer_id integer NOT NULL,
    overall_score integer NOT NULL,
    recommendation character varying(10) NOT NULL,
    comments_for_authors text NOT NULL,
    confidential_comments text,
    review_submission_date date DEFAULT CURRENT_DATE NOT NULL,
    CONSTRAINT ck_review_comments_not_blank CHECK ((TRIM(BOTH FROM comments_for_authors) <> ''::text)),
    CONSTRAINT ck_review_recommendation CHECK (((recommendation)::text = ANY ((ARRAY['accept'::character varying, 'reject'::character varying])::text[]))),
    CONSTRAINT ck_review_score CHECK (((overall_score >= 1) AND (overall_score <= 5)))
);


--
-- Name: review_review_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.review ALTER COLUMN review_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.review_review_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: reviewer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reviewer (
    reviewer_id integer NOT NULL,
    years_experience integer NOT NULL,
    CONSTRAINT ck_reviewer_experience_nonnegative CHECK ((years_experience >= 0))
);


--
-- Name: reviewer_expertise; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reviewer_expertise (
    reviewer_id integer NOT NULL,
    area_label character varying(100) NOT NULL,
    CONSTRAINT ck_re_label_not_blank CHECK ((TRIM(BOTH FROM area_label) <> ''::text))
);


--
-- Name: track_track_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.track ALTER COLUMN track_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.track_track_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Data for Name: app_user; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.app_user (user_id, given_name, surname, email, affiliation, country, phone_number) FROM stdin;
1	Arman	Armanov	arman.armanov@example.com	Nazarbayev University	Kazakhstan	+77011234501
2	Amina	Aminova	amina.aminova@example.com	Al-Farabi Kazakh National University	Kazakhstan	+77011234502
3	Dana	Bekova	dana.bekova@example.com	Nazarbayev University	Kazakhstan	+77011234503
4	Timur	Sadykov	timur.sadykov@example.com	Kazakh-British Technical University	Kazakhstan	+77011234504
5	Aigerim	Nurlanova	aigerim.nurlanova@example.com	L.N. Gumilyov Eurasian National University	Kazakhstan	+77011234505
6	Daniyar	Omarov	daniyar.omarov@example.com	Satbayev University	Kazakhstan	+77011234506
7	Madina	Kassymova	madina.kassymova@example.com	Astana IT University	Kazakhstan	+77011234507
8	Yerlan	Zhakupov	yerlan.zhakupov@example.com	Nazarbayev University	Kazakhstan	+77011234508
9	Saule	Tulegenova	saule.tulegenova@example.com	Kazakh-British Technical University	Kazakhstan	+77011234509
10	Nurlan	Abenov	nurlan.abenov@example.com	Suleyman Demirel University	Kazakhstan	+77011234510
11	Gulnara	Iskakova	gulnara.iskakova@example.com	KIMEP University	Kazakhstan	+77011234511
12	Askar	Mukhametov	askar.mukhametov@example.com	Astana IT University	Kazakhstan	+77011234512
13	Elena	Petrova	elena.petrova@example.com	Novosibirsk State University	Russia	+73832345613
14	Marco	Rossi	marco.rossi@example.com	Politecnico di Milano	Italy	+390212345614
15	Arman	Armanov	arman.armanov.kbtu@example.com	Kazakh-British Technical University	Kazakhstan	+77011234515
\.


--
-- Data for Name: author; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.author (author_id, orcid) FROM stdin;
1	0000-0002-1825-0097
2	0000-0001-5109-3700
4	\N
5	0000-0003-1415-9269
7	\N
9	0000-0002-7183-4421
10	0000-0001-2345-6789
12	\N
14	0000-0003-0000-000X
15	\N
\.


--
-- Data for Name: author_research_area; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.author_research_area (author_id, area_label) FROM stdin;
1	Databases
1	Query Optimization
2	Information Retrieval
2	Privacy-Preserving Computation
4	Databases
4	Machine Learning
5	Databases
5	Transaction Processing
7	Machine Learning
9	Machine Learning
9	Databases
10	Machine Learning Systems
10	Natural Language Processing
12	Query Optimization
12	Information Retrieval
14	Data Compression
14	Machine Learning Systems
15	Software Engineering
\.


--
-- Data for Name: conference; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.conference (conference_id, name, acronym, description, city, country, start_date, end_date, submission_deadline, review_deadline) FROM stdin;
1	Central Asian Conference on Database Systems	CADS 2026	Annual meeting on data management, query processing and learned database systems.	Astana	Kazakhstan	2026-06-15	2026-06-17	2026-02-15	2026-04-01
2	International Symposium on Machine Learning Systems	ISMLS 2026	Systems research for training, serving and evaluating machine learning models.	Almaty	Kazakhstan	2026-09-21	2026-09-23	2026-05-01	2026-07-01
3	Workshop on Graph Data Management	GDM 2027	Workshop on graph databases, graph query languages and graph analytics.	Astana	Kazakhstan	2027-04-12	2027-04-13	2027-01-15	2027-02-20
\.


--
-- Data for Name: conference_host; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.conference_host (conference_id, host_name) FROM stdin;
1	Nazarbayev University
1	L.N. Gumilyov Eurasian National University
2	Kazakh-British Technical University
2	Al-Farabi Kazakh National University
3	Astana IT University
\.


--
-- Data for Name: conference_reviewer; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.conference_reviewer (conference_id, reviewer_id) FROM stdin;
1	1
1	3
1	4
1	7
1	8
2	1
2	3
2	6
2	7
2	10
2	11
2	13
3	6
3	8
3	10
3	13
\.


--
-- Data for Name: conference_session; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.conference_session (session_id, conference_id, title, session_date, start_time, end_time, room_label, chair_id) FROM stdin;
1	1	Query Processing I	2026-06-15	10:00:00	11:30:00	Hall A	1
2	1	Learned Database Components	2026-06-16	14:00:00	15:30:00	Room 204	7
3	1	Late-Breaking Results	2026-06-17	09:00:00	10:00:00	Room 105	8
4	2	Training and Serving Systems	2026-09-22	11:00:00	12:30:00	Auditorium 1	10
5	2	Poster Session	2026-09-23	16:00:00	17:30:00	Main Foyer	3
6	3	Opening Session	2027-04-12	09:00:00	10:30:00	Room 301	6
\.


--
-- Data for Name: paper; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.paper (paper_id, track_id, title, abstract, submission_date, status, session_id) FROM stdin;
1	1	Adaptive Indexing for Hybrid Transactional and Analytical Workloads	We present an adaptive indexing scheme that incrementally builds B+-tree partitions in response to mixed transactional and analytical queries, reducing index maintenance cost by up to 40 percent.	2026-02-10	accepted	1
2	1	Cost-Based Join Ordering with Learned Cardinality Estimates	This paper combines a classical cost-based optimizer with Machine Learning models that estimate join cardinalities. Experiments on the Join Order Benchmark show more stable plans than histogram-based estimation.	2026-02-12	accepted	1
3	2	Learned Query Optimizers in Practice: An Experimental Study	We evaluate five learned query optimizers and report when machine learning improves plan quality over traditional heuristics and when it introduces regressions.	2026-02-14	accepted	2
4	2	Workload Forecasting for Autonomous Database Tuning	We forecast query arrival rates with machine-learned seasonal models and use the forecasts to schedule index creation and memory reconfiguration before demand peaks.	2026-02-13	accepted	\N
5	1	Compression-Aware Storage Layouts for Column Stores	We study how dictionary and run-length encoding interact with page layout in column stores and propose a cost model for choosing encodings per column.	2026-02-11	rejected	\N
6	1	Detecting Isolation Anomalies in Cloud Database Services	We describe a black-box testing tool that detects write skew and lost-update anomalies in managed cloud databases that claim snapshot isolation or serializability.	2026-02-15	under review	\N
7	1	Secure Multi-Party Query Processing for Healthcare Data	We propose a protocol for evaluating selection and aggregation queries over horizontally partitioned patient records without revealing individual rows to other hospitals.	2026-02-09	withdrawn	\N
8	2	Federated Learning over Relational Data Silos	We show how MACHINE LEARNING models can be trained across relational databases owned by different organizations by pushing feature extraction into SQL views.	2026-02-14	withdrawn	\N
9	2	Benchmarking Vector Similarity Search in Relational Engines	We benchmark approximate nearest-neighbour indexes implemented as extensions of open-source relational database systems.	2026-02-15	submitted	\N
10	4	Scalable Training Pipelines for Large Language Models	We describe a data-loading and checkpointing pipeline that keeps accelerators busy when training large machine learning models on shared clusters.	2026-04-28	accepted	4
11	5	Neural Ranking for Kazakh-Language Web Search	We build a test collection for Kazakh web search and compare lexical retrieval with neural re-ranking models fine-tuned on translated queries.	2026-04-25	rejected	\N
12	5	Query Expansion with Large Language Models for Low-Resource Languages	We study prompt-based query expansion for low-resource languages and analyse when generated expansions drift from the user intent.	2026-04-30	withdrawn	\N
\.


--
-- Data for Name: paper_author; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.paper_author (paper_id, author_id, author_position, is_corresponding) FROM stdin;
1	4	1	t
1	5	2	f
2	1	1	t
2	9	2	f
3	12	1	t
3	7	2	f
3	5	3	f
4	9	1	t
5	14	1	t
5	4	2	f
6	5	1	t
6	12	2	f
7	2	1	t
7	10	2	f
8	9	1	f
8	2	2	t
9	10	1	t
10	10	1	t
10	14	2	f
11	2	1	t
11	12	2	f
12	9	1	t
12	2	2	f
\.


--
-- Data for Name: paper_keyword; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.paper_keyword (paper_id, keyword) FROM stdin;
1	adaptive indexing
1	B+-tree
1	HTAP
2	query optimization
2	cardinality estimation
2	join ordering
3	learned query optimization
3	benchmarking
4	workload forecasting
4	autonomous databases
5	column stores
5	compression
6	transaction isolation
6	testing
6	cloud databases
7	secure computation
7	healthcare
7	query processing
8	federated learning
8	relational databases
9	vector search
9	benchmarking
10	distributed training
10	large language models
11	neural ranking
11	Kazakh language
11	web search
12	query expansion
12	large language models
12	low-resource languages
\.


--
-- Data for Name: paper_version; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.paper_version (paper_id, version_no, file_location, uploaded_at, change_note) FROM stdin;
1	1	/files/cads2026/paper-01/v1.pdf	2026-02-10 09:15:00	Initial submission
1	2	/files/cads2026/paper-01/v2.pdf	2026-05-02 18:40:00	Camera-ready version
2	1	/files/cads2026/paper-02/v1.pdf	2026-02-12 11:00:00	Initial submission
2	2	/files/cads2026/paper-02/v2.pdf	2026-02-14 16:20:00	Fixed typos in Section 3
2	4	/files/cads2026/paper-02/v4.pdf	2026-05-03 10:05:00	Camera-ready version (draft v3 was never uploaded)
3	1	/files/cads2026/paper-03/v1.pdf	2026-02-14 20:00:00	\N
4	1	/files/cads2026/paper-04/v1.pdf	2026-02-13 08:30:00	\N
5	1	/files/cads2026/paper-05/v1.pdf	2026-02-11 13:45:00	\N
6	1	/files/cads2026/paper-06/v1.pdf	2026-02-15 23:10:00	\N
7	1	/files/cads2026/paper-07/v1.pdf	2026-02-09 17:00:00	\N
8	1	/files/cads2026/paper-08/v1.pdf	2026-02-14 12:00:00	Initial submission
8	2	/files/cads2026/paper-08/v2.pdf	2026-03-01 09:30:00	Added experiments
9	1	/files/cads2026/paper-09/v1.pdf	2026-02-15 22:55:00	\N
10	1	/files/ismls2026/paper-10/v1.pdf	2026-04-28 10:00:00	Initial submission
10	2	/files/ismls2026/paper-10/v2.pdf	2026-08-01 15:00:00	Camera-ready version
11	1	/files/ismls2026/paper-11/v1.pdf	2026-04-25 14:10:00	\N
12	1	/files/ismls2026/paper-12/v1.pdf	2026-04-30 19:45:00	\N
\.


--
-- Data for Name: review; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.review (review_id, paper_id, reviewer_id, overall_score, recommendation, comments_for_authors, confidential_comments, review_submission_date) FROM stdin;
1	1	1	5	accept	Clear motivation and convincing experiments.	\N	2026-03-10
2	1	3	4	accept	Good paper; please compare with cracking-based indexing.	\N	2026-03-12
3	2	3	4	accept	Solid evaluation on JOB.	Strong candidate for the best paper shortlist.	2026-03-14
4	2	8	4	accept	Well written; the cost model section could be shorter.	\N	2026-03-15
5	3	1	5	accept	Very useful experimental study for practitioners.	\N	2026-03-11
6	3	3	5	accept	Excellent reproducibility package.	\N	2026-03-16
7	3	4	4	accept	Please discuss training overhead in more detail.	\N	2026-03-18
8	4	4	4	accept	Interesting forecasting approach.	\N	2026-03-19
9	4	8	3	accept	Borderline; the baseline set is limited.	I would not object to rejection.	2026-03-20
10	5	1	2	reject	The cost model is not validated on real workloads.	\N	2026-03-13
11	5	3	2	reject	Limited novelty compared with existing column-store work.	\N	2026-03-17
12	6	8	3	accept	Promising tool; the anomaly taxonomy needs clarification.	\N	2026-03-25
13	7	3	3	reject	Security proof is incomplete.	\N	2026-03-05
14	8	4	2	reject	Experiments use only synthetic data.	\N	2026-03-21
15	10	11	5	accept	Impressive engineering and clear ablations.	\N	2026-06-10
16	10	13	4	accept	Good paper; add energy measurements.	\N	2026-06-12
17	10	7	4	accept	Relevant to the community.	\N	2026-06-15
18	11	13	2	reject	Test collection is too small for the claims made.	\N	2026-06-11
19	11	11	3	reject	Interesting language resource but weak baselines.	Encourage resubmission to a workshop.	2026-06-18
20	12	10	2	reject	Analysis of drift is mostly anecdotal.	\N	2026-06-20
\.


--
-- Data for Name: reviewer; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.reviewer (reviewer_id, years_experience) FROM stdin;
1	6
3	8
4	2
6	4
7	5
8	3
10	7
11	10
13	4
\.


--
-- Data for Name: reviewer_expertise; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.reviewer_expertise (reviewer_id, area_label) FROM stdin;
1	Databases
1	Query Optimization
3	Databases
3	Data Mining
3	Information Retrieval
4	Machine Learning
4	Databases
6	Databases
6	Graph Data
7	Machine Learning
7	Computer Vision
8	Distributed Systems
8	Databases
10	Natural Language Processing
10	Machine Learning
11	Data Mining
11	Databases
13	Information Retrieval
13	Natural Language Processing
\.


--
-- Data for Name: track; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.track (track_id, conference_id, name, description, research_area, coordinator_id) FROM stdin;
1	1	Data Management and Query Processing	Storage, indexing, transactions and query optimization.	Databases	3
2	1	Machine Learning for Data Systems	Learned components inside database systems.	Machine Learning	7
3	1	Spatial and Temporal Databases	Moving objects, time series and spatial indexing.	Databases	8
4	2	Machine Learning Systems	Training and serving infrastructure for machine learning.	Machine Learning	10
5	2	Information Retrieval and NLP	Search, ranking and language technologies.	Information Retrieval	13
6	3	Graph Query Processing	Evaluation and optimization of graph queries.	Databases	6
\.


--
-- Name: app_user_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.app_user_user_id_seq', 15, true);


--
-- Name: conference_conference_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.conference_conference_id_seq', 3, true);


--
-- Name: conference_session_session_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.conference_session_session_id_seq', 6, true);


--
-- Name: paper_paper_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.paper_paper_id_seq', 12, true);


--
-- Name: review_review_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.review_review_id_seq', 20, true);


--
-- Name: track_track_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.track_track_id_seq', 6, true);


--
-- Name: app_user pk_app_user; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_user
    ADD CONSTRAINT pk_app_user PRIMARY KEY (user_id);


--
-- Name: author pk_author; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.author
    ADD CONSTRAINT pk_author PRIMARY KEY (author_id);


--
-- Name: author_research_area pk_author_research_area; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.author_research_area
    ADD CONSTRAINT pk_author_research_area PRIMARY KEY (author_id, area_label);


--
-- Name: conference pk_conference; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conference
    ADD CONSTRAINT pk_conference PRIMARY KEY (conference_id);


--
-- Name: conference_host pk_conference_host; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conference_host
    ADD CONSTRAINT pk_conference_host PRIMARY KEY (conference_id, host_name);


--
-- Name: conference_reviewer pk_conference_reviewer; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conference_reviewer
    ADD CONSTRAINT pk_conference_reviewer PRIMARY KEY (conference_id, reviewer_id);


--
-- Name: conference_session pk_conference_session; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conference_session
    ADD CONSTRAINT pk_conference_session PRIMARY KEY (session_id);


--
-- Name: paper pk_paper; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper
    ADD CONSTRAINT pk_paper PRIMARY KEY (paper_id);


--
-- Name: paper_author pk_paper_author; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper_author
    ADD CONSTRAINT pk_paper_author PRIMARY KEY (paper_id, author_id);


--
-- Name: paper_keyword pk_paper_keyword; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper_keyword
    ADD CONSTRAINT pk_paper_keyword PRIMARY KEY (paper_id, keyword);


--
-- Name: paper_version pk_paper_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper_version
    ADD CONSTRAINT pk_paper_version PRIMARY KEY (paper_id, version_no);


--
-- Name: review pk_review; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review
    ADD CONSTRAINT pk_review PRIMARY KEY (review_id);


--
-- Name: reviewer pk_reviewer; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reviewer
    ADD CONSTRAINT pk_reviewer PRIMARY KEY (reviewer_id);


--
-- Name: reviewer_expertise pk_reviewer_expertise; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reviewer_expertise
    ADD CONSTRAINT pk_reviewer_expertise PRIMARY KEY (reviewer_id, area_label);


--
-- Name: track pk_track; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.track
    ADD CONSTRAINT pk_track PRIMARY KEY (track_id);


--
-- Name: app_user uq_app_user_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_user
    ADD CONSTRAINT uq_app_user_email UNIQUE (email);


--
-- Name: author uq_author_orcid; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.author
    ADD CONSTRAINT uq_author_orcid UNIQUE (orcid);


--
-- Name: paper_author uq_paper_author_position; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper_author
    ADD CONSTRAINT uq_paper_author_position UNIQUE (paper_id, author_position);


--
-- Name: review uq_review_paper_reviewer; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review
    ADD CONSTRAINT uq_review_paper_reviewer UNIQUE (paper_id, reviewer_id);


--
-- Name: track uq_track_name_per_conference; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.track
    ADD CONSTRAINT uq_track_name_per_conference UNIQUE (conference_id, name);


--
-- Name: ix_conference_reviewer_reviewer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conference_reviewer_reviewer ON public.conference_reviewer USING btree (reviewer_id);


--
-- Name: ix_paper_author_author; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_paper_author_author ON public.paper_author USING btree (author_id);


--
-- Name: ix_paper_session; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_paper_session ON public.paper USING btree (session_id);


--
-- Name: ix_paper_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_paper_status ON public.paper USING btree (status);


--
-- Name: ix_paper_track; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_paper_track ON public.paper USING btree (track_id);


--
-- Name: ix_review_reviewer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_review_reviewer ON public.review USING btree (reviewer_id);


--
-- Name: ix_reviewer_expertise_label; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_reviewer_expertise_label ON public.reviewer_expertise USING btree (area_label);


--
-- Name: ix_session_chair; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_session_chair ON public.conference_session USING btree (chair_id);


--
-- Name: ix_session_conference; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_session_conference ON public.conference_session USING btree (conference_id);


--
-- Name: ix_track_conference; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_track_conference ON public.track USING btree (conference_id);


--
-- Name: ix_track_coordinator; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_track_coordinator ON public.track USING btree (coordinator_id);


--
-- Name: uq_paper_one_corresponding; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_paper_one_corresponding ON public.paper_author USING btree (paper_id) WHERE is_corresponding;


--
-- Name: author_research_area fk_ara_author; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.author_research_area
    ADD CONSTRAINT fk_ara_author FOREIGN KEY (author_id) REFERENCES public.author(author_id) ON DELETE CASCADE;


--
-- Name: author fk_author_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.author
    ADD CONSTRAINT fk_author_user FOREIGN KEY (author_id) REFERENCES public.app_user(user_id) ON DELETE CASCADE;


--
-- Name: conference_host fk_ch_conference; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conference_host
    ADD CONSTRAINT fk_ch_conference FOREIGN KEY (conference_id) REFERENCES public.conference(conference_id) ON DELETE CASCADE;


--
-- Name: conference_reviewer fk_cr_conference; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conference_reviewer
    ADD CONSTRAINT fk_cr_conference FOREIGN KEY (conference_id) REFERENCES public.conference(conference_id) ON DELETE CASCADE;


--
-- Name: conference_reviewer fk_cr_reviewer; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conference_reviewer
    ADD CONSTRAINT fk_cr_reviewer FOREIGN KEY (reviewer_id) REFERENCES public.reviewer(reviewer_id) ON DELETE CASCADE;


--
-- Name: paper_author fk_pa_author; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper_author
    ADD CONSTRAINT fk_pa_author FOREIGN KEY (author_id) REFERENCES public.author(author_id) ON DELETE RESTRICT;


--
-- Name: paper_author fk_pa_paper; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper_author
    ADD CONSTRAINT fk_pa_paper FOREIGN KEY (paper_id) REFERENCES public.paper(paper_id) ON DELETE CASCADE;


--
-- Name: paper fk_paper_session; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper
    ADD CONSTRAINT fk_paper_session FOREIGN KEY (session_id) REFERENCES public.conference_session(session_id) ON DELETE SET NULL;


--
-- Name: paper fk_paper_track; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper
    ADD CONSTRAINT fk_paper_track FOREIGN KEY (track_id) REFERENCES public.track(track_id) ON DELETE RESTRICT;


--
-- Name: paper_keyword fk_pk_paper; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper_keyword
    ADD CONSTRAINT fk_pk_paper FOREIGN KEY (paper_id) REFERENCES public.paper(paper_id) ON DELETE CASCADE;


--
-- Name: paper_version fk_pv_paper; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper_version
    ADD CONSTRAINT fk_pv_paper FOREIGN KEY (paper_id) REFERENCES public.paper(paper_id) ON DELETE CASCADE;


--
-- Name: reviewer_expertise fk_re_reviewer; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reviewer_expertise
    ADD CONSTRAINT fk_re_reviewer FOREIGN KEY (reviewer_id) REFERENCES public.reviewer(reviewer_id) ON DELETE CASCADE;


--
-- Name: review fk_review_paper; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review
    ADD CONSTRAINT fk_review_paper FOREIGN KEY (paper_id) REFERENCES public.paper(paper_id) ON DELETE CASCADE;


--
-- Name: review fk_review_reviewer; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review
    ADD CONSTRAINT fk_review_reviewer FOREIGN KEY (reviewer_id) REFERENCES public.reviewer(reviewer_id) ON DELETE RESTRICT;


--
-- Name: reviewer fk_reviewer_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reviewer
    ADD CONSTRAINT fk_reviewer_user FOREIGN KEY (reviewer_id) REFERENCES public.app_user(user_id) ON DELETE CASCADE;


--
-- Name: conference_session fk_session_chair; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conference_session
    ADD CONSTRAINT fk_session_chair FOREIGN KEY (chair_id) REFERENCES public.reviewer(reviewer_id) ON DELETE RESTRICT;


--
-- Name: conference_session fk_session_chair_in_pool; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conference_session
    ADD CONSTRAINT fk_session_chair_in_pool FOREIGN KEY (conference_id, chair_id) REFERENCES public.conference_reviewer(conference_id, reviewer_id);


--
-- Name: conference_session fk_session_conference; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conference_session
    ADD CONSTRAINT fk_session_conference FOREIGN KEY (conference_id) REFERENCES public.conference(conference_id) ON DELETE CASCADE;


--
-- Name: track fk_track_conference; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.track
    ADD CONSTRAINT fk_track_conference FOREIGN KEY (conference_id) REFERENCES public.conference(conference_id) ON DELETE CASCADE;


--
-- Name: track fk_track_coordinator; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.track
    ADD CONSTRAINT fk_track_coordinator FOREIGN KEY (coordinator_id) REFERENCES public.reviewer(reviewer_id) ON DELETE RESTRICT;


--
-- Name: track fk_track_coordinator_in_pool; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.track
    ADD CONSTRAINT fk_track_coordinator_in_pool FOREIGN KEY (conference_id, coordinator_id) REFERENCES public.conference_reviewer(conference_id, reviewer_id);


--
-- PostgreSQL database dump complete
--


