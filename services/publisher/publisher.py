import json
import os
import sys
import time

import boto3
import psycopg

DB_URL = os.getenv("DATABASE_URL", "postgresql://sehat:sehat_local_pw@localhost:5433/sehatsaathi")
TOPIC_ARN = os.getenv("TOPIC_ARN", "arn:aws:sns:ap-southeast-2:131585551270:sehatsaathi-events")
SCHEMAS = sys.argv[1:] or ["scheduling", "queue"]

sns = boto3.client("sns", region_name="ap-southeast-2")


def publish_pending(schema):
    sent = 0
    with psycopg.connect(DB_URL) as conn:
        rows = conn.execute(
            f"SELECT id, event_type, payload, correlation_id FROM {schema}.outbox "
            "WHERE published_at IS NULL ORDER BY id LIMIT 10 FOR UPDATE SKIP LOCKED"
        ).fetchall()
        for outbox_id, event_type, payload, cid in rows:
            sns.publish(TopicArn=TOPIC_ARN, Message=json.dumps(payload))
            conn.execute(f"UPDATE {schema}.outbox SET published_at = now() WHERE id = %s", (outbox_id,))
            conn.commit()
            sent += 1
            print(json.dumps({"service": "publisher", "event": "published",
                              "schema": schema, "type": event_type,
                              "correlation_id": cid}), flush=True)
    return sent


if __name__ == "__main__":
    print(f"publisher started for: {SCHEMAS}", flush=True)
    while True:
        try:
            for s in SCHEMAS:
                publish_pending(s)
        except Exception as e:
            print(json.dumps({"service": "publisher", "event": "error", "error": str(e)}), flush=True)
        time.sleep(2)