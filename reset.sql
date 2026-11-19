truncate patient.patients, scheduling.appointments, scheduling.outbox, queue.checkins, queue.outbox restart identity;
update scheduling.slots set status = 'free';