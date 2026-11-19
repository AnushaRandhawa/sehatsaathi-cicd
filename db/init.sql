CREATE SCHEMA IF NOT EXISTS patient;
CREATE SCHEMA IF NOT EXISTS scheduling;
CREATE SCHEMA IF NOT EXISTS queue;

CREATE TABLE patient.patients (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  phone TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE scheduling.doctors (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  department TEXT NOT NULL
);

CREATE TABLE scheduling.slots (
  id SERIAL PRIMARY KEY,
  doctor_id INT NOT NULL REFERENCES scheduling.doctors(id),
  start_time TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL DEFAULT 'free' CHECK (status IN ('free','booked')),
  UNIQUE (doctor_id, start_time)
);

CREATE TABLE scheduling.appointments (
  id SERIAL PRIMARY KEY,
  slot_id INT NOT NULL UNIQUE REFERENCES scheduling.slots(id),
  patient_id INT NOT NULL,
  status TEXT NOT NULL DEFAULT 'booked',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE scheduling.outbox (
  id BIGSERIAL PRIMARY KEY,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  correlation_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  published_at TIMESTAMPTZ
);

CREATE TABLE queue.checkins (
  id SERIAL PRIMARY KEY,
  doctor_id INT NOT NULL,
  patient_id INT NOT NULL,
  appointment_id INT,
  token_no INT NOT NULL,
  status TEXT NOT NULL DEFAULT 'waiting' CHECK (status IN ('waiting','called','no_show')),
  checked_in_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE queue.outbox (
  id BIGSERIAL PRIMARY KEY,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  correlation_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  published_at TIMESTAMPTZ
);

-- demo data: 2 doctors, 20 slots each (every 15 min from tomorrow 9am)
INSERT INTO scheduling.doctors (name, department) VALUES
  ('Dr. Ayesha Khan', 'General Medicine'),
  ('Dr. Imran Siddiqui', 'Cardiology');

INSERT INTO scheduling.slots (doctor_id, start_time)
SELECT d.id, date_trunc('day', now()) + interval '1 day 9 hours' + (g * interval '15 minutes')
FROM scheduling.doctors d, generate_series(0, 19) g;