from client import load_record
from store import Store


def test_load_record_returns_value():
    store = Store({"one": {"active": True, "value": "payload"}})
    assert load_record(store, "one") == "payload"
