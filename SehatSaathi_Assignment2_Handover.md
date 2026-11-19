# SehatSaathi - DevOps Assignment 2 (Implementation) - Handover

## 0. How to use this file

The user pastes or uploads this file into a brand new chat. The previous chat is not visible to you. Everything you need is here.

Instructions to the new Claude:
- Read the whole file first. Then ask the user the questions in section 13, one at a time, and start at section 14.
- Anything marked (verify) is from memory or an old search and must be checked before you rely on it. Search the web for current AWS pricing and free-plan rules when it matters.
- Do not pretend to see the user's screen or AWS console. Ask for screenshots or pasted command output.
- Never tell the user to spend real money. Never tell them to click Upgrade.

## 1. The user and how to work with them

- Anusha, final-year computer science student in Karachi, Pakistan. Her class mixes technical and non-technical students, and may include masters students. She wants her work to hold up against more complex classmates, so depth of engineering matters.
- She is tired, short on time (original estimate: 2 days, working in 1-hour windows around other projects) and anxious about money. On Azure she once forgot to turn off a VM and lost all free credits, which hurt her final project. Protecting credits is a top priority.
- Her working style:
  - One step at a time. She asked more than once to slow down and not receive many things at once.
  - Each step explained in baby language ("what we are doing") before the commands.
  - Brief answers to her questions. She wants to save tokens.
  - She works from screenshots and pasted output. Ask for them.
  - She gets frustrated when an answer misses what she asked, so answer the exact question first.
  - Always end any step that creates something billable with a "Running now" list: what is running, and what to stop or delete.
- She wants plain files without decorative formatting.

## 2. The instructor and what he values

- Azhar ul Islam (as she described him, with a LinkedIn "About" text she pasted). Technology executive, 20+ years, part of the founding tech team at Careem (cloud infrastructure, DevOps transformation, platform reliability, continuous delivery), also banking and financial services. CTO at Contrivus. Founded ASF Tech Partners. Skills listed: AI, cloud, DevOps, DevSecOps, MLOps, platform engineering. The profile said visiting faculty at FAST University; she says IBA Karachi. Unconfirmed which, or both.
- Likely to probe: reliability and failure handling, deployment and CI/CD, observability, security, payment-style correctness (idempotency, double booking), consistency trade-offs, and whether the student can explain every part.
- In-person viva is the real grading checkpoint. Easy-to-understand explanations are valued, but not simplistic ones.

## 3. Assignment 1 (DONE and submitted): the design

Brief: choose an application, design a software architecture, draw a diagram, explain the design (7 questions), plus a short presentation (she did a 1 to 2 minute screen recording instead of slides, with sir's permission).

Chosen application: SehatSaathi (say "Sehat Saathi"), a hospital appointment and live-queue system for Karachi OPDs. Patients book a slot or take a digital token, see a live queue, and get an SMS when their turn is near. Users: patient, receptionist, doctor.

Architecture: microservices plus event-driven communication on AWS, with a multi-tier edge.

Diagram (draw.io, left to right):
- Users (Patient, Receptionist, Doctor) -> CloudFront (also serves the web app from S3) -> API Gateway (verifies login token with Cognito) -> three services inside an ECS Fargate box, all inside a dashed VPC box: Patient Service, Scheduling Service, Queue Service.
- Data inside the VPC: PostgreSQL on RDS (Multi-AZ) and Redis (ElastiCache).
- Async side (outside VPC): Scheduling Service publishes AppointmentBooked and Queue Service publishes QueueMoved to SNS; SNS -> main SQS queue -> Lambda -> SMS/WhatsApp provider; after three failed tries messages go to a dead-letter queue (DLQ).
- Bottom strip: CI/CD (GitHub Actions), Terraform, CloudWatch, WAF, with an arrow "deploys new versions" to the ECS box.
- Legend: solid line = someone is waiting for a reply (synchronous REST); dashed line = just announcing an event, not waiting.
- Numbered main flow: 1 patient opens app; 2 booking goes through API Gateway to Scheduling Service; 3 saved in PostgreSQL; 4 AppointmentBooked announced to SNS; 5 event reaches the queue; 6 Lambda sends the SMS; 7 on the day, QueueMoved alerts.

Service responsibilities:
- Patient Service: registration and profiles.
- Scheduling Service: doctors, departments, slots, booking. One slot can only go to one patient. Schedules cached in Redis.
- Queue Service: today's live queue per doctor in Redis, backed by check-ins saved in PostgreSQL so Redis can be rebuilt. Staff call the next patient or mark no-show.
- Notification pipeline: SNS -> SQS -> Lambda, not called directly by services (loose coupling).

Failure story (from her document): SMS or Lambda down -> bookings continue, messages wait in SQS, retried, then DLQ. Redis down -> schedules from PostgreSQL, queue rebuilt from check-ins. Container dies -> ECS replaces it. Primary DB fails -> Multi-AZ standby. Scheduling Service down -> new bookings stop but today's queue runs. Whole system down -> paper tokens.

Honest points she must be ready to explain in the viva:
- All services share one PostgreSQL instance, each using its own schema (cost and simplicity). Would split later.
- Outbox pattern: save the event in the same DB transaction as the booking, publish afterwards.
- SQS can deliver twice, so the consumer is idempotent (checks message ID).
- Live position by polling every 15 to 20 seconds from Redis, SMS for "your turn is near". WebSockets would be an upgrade.
- Booked patients and walk-ins share one queue per doctor; booked patients have priority at their slot time.
- Solid vs dashed lines; microservices are the boxes, event-driven is how some arrows work.

Files she already has: the architecture diagram PNG, a roughly 2.5 page written explanation PDF, and the recorded walkthrough. All submitted.

## 4. Assignment 2 (CURRENT): implement the design

What she told me about sir's instruction (paraphrase, exact wording unknown, ask her to paste it):
- Implement the design, but simplifying the architecture is allowed.
- The core deliverable is to demonstrate that the components are connected to each other: when data is added or changed, it flows through (query or data is passed on, events trigger, and so on). She forgot the end of his sentence ("etc etc"). Ask her what it was, or have her paste the task from the LMS.
- Cost rule from sir: do not pay a penny. Staying within free tier is required. Both always-free usage and credit-funded usage are acceptable, as long as total stays within the $100 free credits limit.
- Deliverables for this assignment, deadline and demo format (live, recorded, report?) are NOT known. Ask.

## 5. Decisions already made

- Keep the original architecture. Do not collapse it into a monolith.
- Limit the application to three functions, end to end, rather than 20 shallow ones:
  1. View a doctor's schedule (first read from PostgreSQL, next reads from Redis).
  2. Book an appointment (saved in PostgreSQL, one slot per patient, AppointmentBooked -> SNS -> SQS -> Lambda -> SMS log line).
  3. Check in and call next patient (Queue Service updates the live queue, QueueMoved -> same pipeline).
  Patient Service stays tiny: register patient and get patient. Everything else is cut.
- Depth over breadth. The engineering underneath must be strong, with evidence she can show sir: concurrency test, cache latency numbers, failure demos, CI pipeline, Terraform, tracing. See section 10.
- Language and framework: Python 3.11 with FastAPI (assumed, she had no preference).
- Build in layers so something always works. Layer 1 is entirely on her laptop at zero cost.
- Spending target: stay under about 20 USD of the 100 USD. Use the minimum needed for full marks.
- AWS region: she chose to stay in Asia Pacific (Sydney), ap-southeast-2, the console default she landed on. It is somewhat pricier than US East (verify). Use one region only.
- Credit activities in the console's Explore AWS box (5 activities, 20 USD each, up to 100 USD extra): do Set up a cost budget (now), Create an RDS database (when we reach the database stage; choose RDS PostgreSQL, not Aurora), Create a web app using Lambda (when we reach Lambda). Save Launch EC2 and Bedrock playground for later; do not use them now. Read each activity's conditions, then confirm the credit appears on the Credits page.
- Never leave anything running. Terraform destroy is the planned kill switch for the AWS layer.

## 6. Current state: AWS account

- Account exists and works. Account name shown: "Array of Sunshine". Created by her on her own email as root user (after earlier failed attempts with a virtual card, a Builder ID confusion, and repeated tries). Now created successfully with a normal non-virtual debit card.
- Console home screenshot showed: Explore AWS with 5 activities, 0 of 5 done, 0 of 100 USD earned; cost widgets said "Unable to load" (probably new account, unconfirmed); a partial date of May 04, 2027 which looks like the Free Plan end date. The credit balance and plan box at the top was not seen. NOT YET CONFIRMED: whether it is the Free Plan, the credit balance, days left.
- Budget: not confirmed as created. MFA: not confirmed enabled.
- Sign-in notes: use "Sign in using root user email" (the IAM user form with account ID is the wrong one). Builder ID is a separate thing and not the AWS account. After a couple of failed attempts stop and wait, do not hammer (lockout risk). The exact root email is the one used at sign-up; she tried several emails earlier, so ask her to confirm which one. She signed in successfully on her personal laptop in an Edge InPrivate window and also on an office laptop. Sessions on shared machines should be logged out.
- Safety to set up: MFA with an authenticator app on her phone; never put AWS keys in code or GitHub; do not use root access keys. For CLI and Terraform, create a non-root IAM user with limited permissions, MFA on, keys only in her local AWS credentials file.

## 7. Current state: laptop and the Docker problem

- Personal Windows laptop (user folder C:\Users\HP). Installed: Docker 29.1.2, Python 3.11.9, Git 2.47.0. Not yet checked: AWS CLI, Terraform, Node, VS Code details (she has VS Code).
- Disk: about 7 GB free on C:, 2.6 GB free on D:. Docker images normally live on C: (she believes Docker may be on D; check Docker Desktop -> Settings -> Resources -> Advanced -> Disk image location). Planned project folder: D:\sehatsaathi (cmd needs `cd /d D:\sehatsaathi` to switch drives). Keep images lean; add LocalStack (about 1 GB) only when needed. `docker system prune` frees space.
- Planned first step before the problem: docker-compose.yml with postgres:16 (user sehat, db sehatsaathi, throwaway password sehat_local_pw, port 5432, volume pgdata) and redis:7 (port 6379), then `docker compose up -d`, then tests `docker compose exec redis redis-cli ping` (PONG) and `docker compose exec db psql -U sehat -d sehatsaathi -c "select 1;"`. She has NOT completed this yet.
- Problem: Docker Desktop engine stuck on "starting" for 20+ minutes. Errors seen: "service desktop proxies failed: getting list of WSL2 integrated distros ... context deadline exceeded", then "Wsl/Service/RegisterDistro/CreateVm/ERROR_TIMEOUT" while importing the docker-desktop distro. Virtualization is enabled in Task Manager. She ran `wsl --shutdown` several times and restarted the LxssManager service; after that Docker Desktop would not open at all. She decided to restart the laptop.
- Repair ladder if still broken after a restart (stop at the first that works):
  1. Reopen Docker Desktop, wait 3 to 5 minutes.
  2. Admin cmd: `wsl --update`, `wsl --shutdown`, reopen.
  3. `wsl --status`. In "Turn Windows features on or off", make sure Virtual Machine Platform and Windows Subsystem for Linux are ticked (restart if changed).
  4. Free some space on C: (low disk can cause timeouts).
  5. If Docker Desktop opens: bug icon (Troubleshoot) -> Reset to factory defaults. She has nothing stored in Docker yet, so this is safe.
  6. `wsl --unregister docker-desktop` (safe, nothing stored), then reopen Docker Desktop.
  7. Uninstall and reinstall the latest Docker Desktop with the WSL 2 backend.
  8. If unfixed after about an hour, consider a fallback (verify availability and limits first): GitHub Codespaces, or Docker Engine inside a WSL Ubuntu distro, or native PostgreSQL and Redis. Tell her honestly what is lost (the container and CI story is part of the DevOps value).
- Also check: `git` global name and email set, a GitHub account exists, and a private repo for the project.

## 8. AWS free plan facts and the cost model

Researched online in November 2026, re-verify anything important:
- New accounts (created after July 15, 2025) get a Free Plan: 100 USD credits at sign-up plus up to 100 USD more by completing 5 activities, valid up to 6 months or until credits are used. Older accounts, or people who ever had an AWS account, may be on the legacy tier or ineligible.
- On the Free Plan, AWS does not bill. When credits or time run out, the account closes and there are 90 days to upgrade and recover resources. Charges are only possible after upgrading to the Paid Plan (and joining AWS Organizations upgrades you; not reversible). Some services are not available on the Free Plan (verify which: ElastiCache, ECS Fargate, WAF, load balancers, NAT were NOT confirmed).
- EC2, RDS and API Gateway usage is credit-funded. Credits can take up to 30 minutes to appear. AWS emails when roughly 50 percent, 25 percent and 10 percent of credits remain.
- Where to check: console home (plan and balance), Billing -> Credits, Billing and Cost Management -> Free Tier page, Billing -> Bills (charges by service and by region, useful to catch forgotten resources), aws.amazon.com/free (eligible services). Set one monthly cost budget of about 10 USD with email alerts; creating a cost budget is also one of the credit activities.
- Always-free allowances from memory (verify): Lambda, SQS and SNS have monthly free requests; DynamoDB has a free allowance. At demo volumes these cost almost nothing.

Rough running costs, my own estimates for US East (Sydney is higher), per day, verify with the AWS pricing calculator and by watching the credit balance:
- RDS PostgreSQL smallest, single-AZ: about 0.40 USD. Multi-AZ doubles it (skip; explain in viva).
- ElastiCache smallest node: about 0.40 USD, cannot be paused.
- ECS Fargate, 3 tiny tasks: about 1 USD.
- Load balancer: about 0.60 USD. NAT gateway: about 1.10 USD (never create it). WAF: skip.
- Public IPv4 addresses are billed hourly, about 0.12 USD per day each (verify).
- Total if everything runs: roughly 3 to 6 USD per day. Forgotten for a month it would eat most of the credits, which is the Azure scenario.
- Plan: laptop work is free; real SNS, SQS, Lambda, DynamoDB cost about nothing; only RDS, Redis and Fargate cost, and only for a few hours or one or two days total.
- Keep a burn log: date, credit balance at start of session, balance at end.

## 9. Build plan in stages

Decision rule: whatever stage is working when time runs out is the demo. Stages 1 and 2 alone are a complete, strong demo. The document and diagram explain the rest as the production design.

Stage 0: safety (free, 15 minutes)
- Confirm Free Plan and credit balance (screenshot of the top of Console Home).
- Create one cost budget (about 10 USD, her email) to earn the 20 USD credit.
- Turn on MFA with her phone. Confirm region is Sydney in the top right.
- Make a private GitHub repo. Start the burn log.

Stage 1: everything on the laptop (free)
- Get Docker working (section 7).
- Project layout:
  - docker-compose.yml
  - db/init.sql
  - services/patient, services/scheduling, services/queue (FastAPI app, requirements.txt, Dockerfile each)
  - lambda/notify/handler.py
  - tests/, scripts/, infra/terraform/, .github/workflows/ci.yml, docs/evidence/
- Compose runs: postgres, redis, localstack (SNS, SQS, Lambda, DynamoDB simulation; large image, add only now), and the three services. A simple local gateway (nginx) is optional.
- Database (one PostgreSQL, separate schemas per service, matching the document):
  - patient.patients(id, name, phone, created_at)
  - scheduling.doctors(id, name, department)
  - scheduling.slots(id, doctor_id, start_time, status) with UNIQUE(doctor_id, start_time)
  - scheduling.appointments(id, slot_id UNIQUE, patient_id, status, created_at); UNIQUE(slot_id) is what makes double booking impossible
  - scheduling.outbox(id, event_type, payload jsonb, correlation_id, created_at, published_at null)
  - queue.checkins(id, doctor_id, patient_id, appointment_id, token_no, status, checked_in_at)
  - queue.outbox (or a shared outbox helper)
- Endpoints (keep it to these):
  - Patient: POST /patients, GET /patients/{id}
  - Scheduling: GET /doctors/{id}/slots (cache-aside: Redis key schedule:{doctor_id}, TTL about 60 s), POST /appointments (one DB transaction: insert appointment, mark slot booked, insert outbox row; return 201 or 409 on conflict; invalidate the cache key)
  - Queue: POST /checkin, GET /queue/{doctor_id}/position/{patient_id}, POST /queue/{doctor_id}/call-next
  - Every request carries an X-Correlation-ID header (generate one if missing).
- Outbox publisher: a small loop in each service that reads unpublished outbox rows, publishes to SNS, then sets published_at.
- Events (JSON, include event_id, type, occurred_at, correlation_id):
  - AppointmentBooked: appointment_id, patient_id, doctor_id, slot_time
  - QueueMoved: doctor_id, called_token, next_patient_ids
- Redis queue state: list or sorted set per doctor. If Redis is empty after a crash, rebuild from queue.checkins where status is waiting.
- Lambda notify: SQS-triggered. Handles both raw and SNS-enveloped bodies. Idempotency: conditional put of message_id into a DynamoDB table (small addition to the original diagram, say so in the viva); if already present, skip. "Sends" the SMS by logging a line (stub). A flag can force failure to demo the DLQ.
- SNS topic sehatsaathi-events -> SQS sehatsaathi-notifications with a redrive policy (maxReceiveCount 3) to sehatsaathi-notifications-dlq.
- Healthy end state: a booking in the API leads to a DB row, an outbox row, an SNS message, an SQS message, a Lambda log line, all visible and tied by one correlation ID.

Stage 2: real SNS, SQS, Lambda, DynamoDB on AWS (about free, 2 to 3 hours)
- Create them with Terraform in ap-southeast-2 (also a depth item). Services still run on the laptop but publish to real SNS using a limited IAM user's credentials.
- Do the "Create a web app using AWS Lambda" credit activity here if it fits, then confirm the credit.
- CloudWatch alarms: DLQ depth above 0, and oldest message age.

Stage 3: managed data stores (optional, costs money, decision gate)
- RDS PostgreSQL (db.t3.micro class, single-AZ, small storage). Do the "Create an Aurora or RDS database" credit activity with RDS. Restrict network access to her IP only (her IP changes between locations; update the rule) and never allow 0.0.0.0/0.
- Redis: either ElastiCache (smallest node, delete after) or, to save money, a Redis container beside the services, with honest viva wording ("production would use ElastiCache").

Stage 4: deploy the services on ECS Fargate (optional, costs money)
- ECR repos, a cluster, three services, small CPU and memory, public subnets with tight security groups (no NAT gateway). Say openly that this deviates from the private-network diagram and why.
- Demo by hitting task public IPs, or an Application Load Balancer, or API Gateway only if budget and time allow. Check pricing before each.
- Tear down right after the demo recording.

Stage 5: final demo and teardown
- Rehearse, record, collect evidence, then destroy everything and confirm the balance stops moving.

## 10. Depth items (evidence for sir) with effort

- Double-booking test: 50 simultaneous requests for one slot, exactly one 201 and 49 409s, in tests/ and in CI. About 1 hour. Free.
- Cache-aside with measured latency: script that times N requests with and without cache; save the numbers. About 1 hour. Free.
- Outbox pattern and idempotent Lambda (both described in her document). About 2 hours. Free.
- Failure demos: stop the consumer (disable the SQS trigger), book anyway, show messages waiting; force a poison message into the DLQ and redrive; stop Redis and show reads fall back to PostgreSQL and the queue rebuilds; send a duplicate message and show one SMS. About 1 hour. Free.
- Load burst: 500 bookings (seed enough slots), show queue depth rising and draining. About 1 hour. Pennies.
- CI/CD with GitHub Actions: lint, tests with PostgreSQL and Redis service containers, Docker build; deploy to ECR/ECS only if Stage 4 is done. Use GitHub OIDC to AWS, not long-lived keys. About 2 to 3 hours. Free.
- Terraform for the AWS layer (SNS, SQS, DLQ, redrive, Lambda, IAM roles, DynamoDB, alarms). terraform destroy is the kill switch. Keep a backup of the state file; losing it orphans resources. About 2 to 3 hours.
- Observability: JSON logs, correlation ID through HTTP, event and Lambda logs; demo by searching one ID across everything; 2 CloudWatch alarms. About 1 to 2 hours.
- Least-privilege IAM: Lambda can only read and delete from its queue, write to its DynamoDB table and write logs; the publisher can only publish to the topic; no admin keys in code. About 1 hour.

Priority if time is short: must = double-booking test, cache numbers, failure demos, outbox and idempotency, basic CI. Should = Terraform for the AWS layer, load burst. If time allows = observability and IAM polish. Total roughly 12 to 16 hours.

At the end produce a one-page evidence summary: test result, latency numbers, DLQ screenshot, green pipeline, a trace of one correlation ID. That is what sir can compare against other students.

## 11. Shutdown and credit-protection checklist (repeat every session)

Start of session: open Billing -> Credits and note the balance in the burn log. `docker compose up -d`.
End of session:
- `docker compose down` (data is kept in the volume).
- List what exists on AWS and delete or stop what is not needed tonight. Check ONLY the chosen region, plus Billing -> Bills by region to catch strays.
- Note the end balance. If it dropped faster than expected, stop and investigate. Never click Upgrade.
- Commit and push to the private GitHub repo.

What bills even when idle (verify each):
- RDS: a stopped instance restarts automatically after about 7 days and storage still bills; for the final teardown, delete it (optionally skip the final snapshot after checking).
- ElastiCache: cannot be stopped; delete it.
- Fargate: delete the services or set desired count to 0; ECR images and CloudWatch Logs also accumulate (set log retention to a few days).
- Load balancers, NAT gateways, unattached Elastic IPs, public IPv4 addresses: delete. Never create a NAT gateway or WAF.
- Lambda, SQS, SNS: no idle cost, but empty the queues and delete when finished.
- S3: empty the buckets before deleting.
- Terraform: `terraform destroy` removes what Terraform created; then verify in the console and in Bills.
Final teardown: after the demo is recorded and graded evidence is saved (screenshots, logs, recording), destroy everything, then confirm in Bills that no service is accruing charges and the credit balance has stopped changing. Delete the IAM user's access keys. Keep the account (credits last up to 6 months) if she may use them for something else later.

## 12. Demo, evidence and viva

Demo script (about 5 minutes):
1. Show the three services and the data stores running.
2. View schedule twice: first from PostgreSQL, then from Redis (show timing).
3. Book an appointment; show the DB row, the outbox row, the SNS publish, the SQS message and the Lambda log line, all with the same correlation ID.
4. Check in and call next; show QueueMoved and the second SMS log.
5. Failure demo: disable the consumer, book anyway, show the message waiting; re-enable and watch it drain. Then the DLQ and redrive.
6. Concurrency test: 50 requests, exactly one booking.
7. Show the CI pipeline and the Terraform file; mention terraform destroy.
Viva topics are the ones in the Assignment 1 failure story and honest points (section 3), plus: how it is deployed, how you know it broke, how you secure it, what you would do next (WebSockets, split databases, Multi-AZ, WAF, Cognito).

## 13. Questions to ask the user first (one at a time)

1. Please paste sir's exact implementation task from the LMS, including the deadline and what must be submitted or demonstrated. What was the end of his "query/data thrown on ... when it changed or added ..." sentence?
2. Did the laptop restart fix Docker? What does `docker ps` print?
3. Screenshot of the top of Console Home: plan (Free or Paid), credit balance, days left.
4. Is the cost budget created? Is MFA on?
5. How many hours can she realistically spend, and until when?
6. Is a GitHub account and a private repo ready? Are AWS CLI and Terraform installed (`aws --version`, `terraform -version`)?
7. Which email is the AWS root login, and does she have her phone for MFA ready?

## 14. First actions for the new chat

1. Get Docker Desktop working (section 7), with one step at a time.
2. Stage 0 safety items (section 9).
3. Then Stage 1 in this order, finishing each before the next: compose with Postgres and Redis, schema, Scheduling Service schedule endpoint with cache-aside and timing, booking with the double-booking test, outbox, LocalStack SNS and SQS, Lambda with idempotency and the DLQ, Queue Service, then the failure demos.
4. After each billable step, give the "Running now" list.

## 15. Notes from the previous chat

- Some of the earlier suggestions were generic. The strongest guidance is the layered plan, the depth items and the shutdown checklist.
- A few AWS facts are unverified (listed with "verify" above): which services the Free Plan blocks, exact idle costs, Sydney pricing, RDS stopped-instance behaviour, public IPv4 pricing. Check before relying on them.
- The previous chat gave her a diagram label fix list and numbering that are already done; do not redo Assignment 1.
