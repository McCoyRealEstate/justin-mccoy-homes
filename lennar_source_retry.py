"""Bounded retry policy for read-only Lennar source requests."""
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def configure_source_session(session):
    policy = Retry(total=2, connect=2, read=2, status=2,
                   allowed_methods=frozenset({"GET", "HEAD"}),
                   status_forcelist=(408, 429, 500, 502, 503, 504),
                   backoff_factor=1, raise_on_status=False,
                   respect_retry_after_header=False)
    session.mount("https://", HTTPAdapter(max_retries=policy))
    return session
