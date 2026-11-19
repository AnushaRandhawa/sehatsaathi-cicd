import json
import os
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = os.getenv("SCHEDULING_URL", "http://127.0.0.1:8002")


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None


def test_double_booking():
    _, data = call("GET", "/doctors/2/slots")
    slot_id = next(s["id"] for s in data["slots"] if s["status"] == "free")

    def attempt(i):
        return call("POST", "/appointments", {"slot_id": slot_id, "patient_id": 1000 + i})[0]

    with ThreadPoolExecutor(max_workers=50) as pool:
        results = list(pool.map(attempt, range(50)))

    print(f"slot {slot_id}: 201 x {results.count(201)}, 409 x {results.count(409)}")
    assert results.count(201) == 1
    assert results.count(409) == 49


if __name__ == "__main__":
    test_double_booking()
    print("PASS")