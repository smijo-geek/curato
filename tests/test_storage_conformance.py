"""Storage port conformance — the SAME contract run against every backend.

This is the cloud-agnostic promise, exercised: the local adapter and a (mocked) S3 adapter must
behave identically. A backend that fails this is not a drop-in replacement.
"""
import pytest

from curato.ports.storage import StoragePort, LocalStorage


def run_contract(store: StoragePort) -> None:
    store.put_bytes("landing/a.txt", b"hello")
    store.put_bytes("landing/sub/b.txt", b"world")

    keys = set(store.list("landing"))
    assert "landing/a.txt" in keys
    assert "landing/sub/b.txt" in keys

    assert store.read_bytes("landing/a.txt") == b"hello"
    assert store.read_bytes("landing/sub/b.txt") == b"world"

    # keys returned by list() must be directly usable by read_bytes()
    for k in keys:
        assert isinstance(store.read_bytes(k), bytes)

    assert store.local_path("landing/a.txt")  # a non-empty engine-usable path/URI
    assert store.list("nope") == []            # empty prefix -> empty list, never an error


def test_local_backend(tmp_path):
    run_contract(LocalStorage(str(tmp_path)))


def test_s3_backend():
    moto = pytest.importorskip("moto")
    pytest.importorskip("boto3")
    from moto import mock_aws
    import boto3
    from curato.ports.storage import S3Storage

    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="curato-test")
        run_contract(S3Storage("curato-test", prefix="proj", region_name="us-east-1"))
