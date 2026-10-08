import time
from django.conf import settings
from pyairtable import Api
from requests.exceptions import RequestException

TRANSIENT_STATUS = {429, 500, 502, 503, 504}


def _status_of(exc):
    resp = getattr(exc, 'response', None)
    return getattr(resp, 'status_code', None)


def _with_retry(fn, *, retries=3, base_delay=0.5):
    """Retry transient failures (429/5xx/network) with bounded backoff.
    Permanent failures (other 4xx) are re-raised immediately."""
    attempt = 0
    while True:
        try:
            return fn()
        except RequestException as exc:
            code = _status_of(exc)
            transient = code in TRANSIENT_STATUS or code is None
            if not transient or attempt >= retries:
                raise
            time.sleep(base_delay * (2 ** attempt))
            attempt += 1


def get_table():
    api = Api(settings.AIRTABLE_API_KEY)
    return api.table(settings.AIRTABLE_BASE_ID, settings.AIRTABLE_TABLE_NAME)


def fields_for(task):
    return {
        'TaskId': str(task.id),
        'Title': task.title,
        'Description': task.description or '',
        'Status': task.status,
        'Assignee': task.assignee.name if task.assignee else '',
        'Position': task.position,
        'ProjectId': str(task.project_id),
    }


def export_tasks(tasks, table=None):
    """Idempotent upsert keyed on TaskId, with per-record failure isolation."""
    table = table or get_table()
    existing = _with_retry(lambda: table.all(fields=['TaskId']))
    index = {r['fields'].get('TaskId'): r['id'] for r in existing}
    created = updated = failed = 0
    errors = []
    for task in tasks:
        f = fields_for(task)
        try:
            rec_id = index.get(str(task.id))
            if rec_id:
                _with_retry(lambda: table.update(rec_id, f))
                updated += 1
            else:
                _with_retry(lambda: table.create(f))
                created += 1
        except Exception as exc:
            failed += 1
            errors.append({'taskId': str(task.id), 'error': str(exc)})
    return {'created': created, 'updated': updated, 'failed': failed,
            'exported': created + updated, 'errors': errors}
