"""Unit tests for image_service JobQueue state machine (no browser, no HTTP)."""

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = REPO_ROOT / "skills" / "web-operator" / "scripts" / "image_service.py"

spec = importlib.util.spec_from_file_location("image_service", MODULE_PATH)
image_service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(image_service)

Job = image_service.Job
JobQueue = image_service.JobQueue
QUEUED = image_service.QUEUED
RUNNING = image_service.RUNNING
DONE = image_service.DONE
CANCELED = image_service.CANCELED


def make_job(prompt="p"):
    return Job(prompt, "chatgpt", 180, Path("/tmp/x.png"))


def test_positions_reflect_submission_order():
    q = JobQueue()
    a, b, c = make_job("a"), make_job("b"), make_job("c")
    for j in (a, b, c):
        q.submit(j)
    a.status = RUNNING
    assert q.position(a) == 0
    assert q.position(b) == 1
    assert q.position(c) == 2
    assert q.queue_length() == 3


def test_next_queued_skips_finished_and_canceled():
    q = JobQueue()
    a, b = make_job("a"), make_job("b")
    q.submit(a)
    q.submit(b)
    a.status = DONE
    assert q.next_queued() is b


def test_cancel_queued_job():
    q = JobQueue()
    a, b = make_job("a"), make_job("b")
    q.submit(a)
    q.submit(b)
    assert q.cancel(a) is True
    assert a.status == CANCELED
    assert q.position(b) == 0  # nothing running, nothing ahead
    assert q.queue_length() == 1


def test_cancel_refuses_non_queued():
    q = JobQueue()
    a = make_job()
    q.submit(a)
    a.status = RUNNING
    assert q.cancel(a) is False  # running jobs are killed by the worker path
    a.status = DONE
    assert q.cancel(a) is False


def test_position_none_for_finished():
    q = JobQueue()
    a = make_job()
    q.submit(a)
    a.status = DONE
    assert q.position(a) is None


def test_history_trim_keeps_active_jobs():
    q = JobQueue()
    keep = make_job("active")
    q.submit(keep)
    for i in range(image_service.MAX_HISTORY + 10):
        j = make_job(str(i))
        q.submit(j)
        j.status = DONE
        q._trim_history()
    assert keep.id in q.jobs
    finished = [j for j in q.jobs.values() if j.status == DONE]
    assert len(finished) <= image_service.MAX_HISTORY
