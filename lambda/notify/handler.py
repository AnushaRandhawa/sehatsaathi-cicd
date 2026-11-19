import json
import os


def lambda_handler(event, context):
    for record in event["Records"]:
        body = json.loads(record["body"])
        if "Message" in body and "TopicArn" in body:
            body = json.loads(body["Message"])

        cid = body.get("correlation_id")

        if os.environ.get("FORCE_FAIL") == "true":
            print(json.dumps({"service": "notify", "event": "forced_failure",
                              "correlation_id": cid}))
            raise Exception("forced failure for DLQ demo")

        print(json.dumps({"service": "notify", "event": "sms_sent",
                          "correlation_id": cid, "type": body.get("type"),
                          "message": body}))