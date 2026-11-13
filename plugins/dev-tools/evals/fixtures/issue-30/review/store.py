class Store:
    def __init__(self, records):
        self._records = records

    def get_active(self, key):
        record = self._records.get(key)
        if record is None or not record["active"]:
            return None
        return record["value"]
