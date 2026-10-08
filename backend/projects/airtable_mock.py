class MockTable:
    """In-memory stand-in for a pyairtable Table (unit tests only).
    Pass fail_ids to simulate permanent per-record failures."""
    def __init__(self, fail_ids=None):
        self._rows = {}
        self._seq = 0
        self.fail_ids = set(fail_ids or [])

    def all(self, fields=None):
        return [{'id': rid, 'fields': f} for rid, f in self._rows.items()]

    def create(self, fields):
        if fields.get('TaskId') in self.fail_ids:
            raise RuntimeError('permanent 422 for ' + str(fields.get('TaskId')))
        self._seq += 1
        rid = f'rec{self._seq}'
        self._rows[rid] = fields
        return {'id': rid, 'fields': fields}

    def update(self, rid, fields):
        if fields.get('TaskId') in self.fail_ids:
            raise RuntimeError('permanent 422 for ' + str(fields.get('TaskId')))
        self._rows[rid] = {**self._rows.get(rid, {}), **fields}
        return {'id': rid, 'fields': self._rows[rid]}
