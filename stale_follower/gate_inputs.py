import json
import re


_SAFE_SEGMENT = re.compile(r"[A-Za-z0-9._-]+\Z")


def normalize_namespace(value):
    """Require one exact, non-root slash-prefixed etcd key namespace."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("namespace must be a nonempty exact string")
    if not value.startswith("/") or value.endswith("/"):
        raise ValueError("namespace must start with / and have no trailing slash")
    segments = value[1:].split("/")
    if any(segment in ("", ".", "..") or not _SAFE_SEGMENT.fullmatch(segment) for segment in segments):
        raise ValueError("namespace must contain only safe, nonempty path segments")
    return value


def build_txn_script(head, receipt_key, initial, successor, receipt_value):
    """Build etcdctl's blank-line-delimited, noninteractive transaction input."""
    compare = f"value({json.dumps(head)}) = {json.dumps(initial)}"
    success = "\n".join((
        f"put {json.dumps(head)} {json.dumps(successor)}",
        f"put {json.dumps(receipt_key)} {json.dumps(receipt_value)}",
    ))
    failure = f"get {json.dumps(head)}"
    return f"{compare}\n\n{success}\n\n{failure}\n\n"


def build_init_script(head, receipt_key, initial):
    """Initialize only when both exact target keys are absent, atomically."""
    compare = f'version({json.dumps(head)}) = "0"\nversion({json.dumps(receipt_key)}) = "0"'
    success = f"put {json.dumps(head)} {json.dumps(initial)}"
    failure = f"get {json.dumps(head)}\nget {json.dumps(receipt_key)}"
    return f"{compare}\n\n{success}\n\n{failure}\n\n"


def child_environment(environ):
    """Preserve connection credentials, but control test semantics explicitly."""
    env = dict(environ)
    connection_options = {'ETCDCTL_CACERT', 'ETCDCTL_CERT', 'ETCDCTL_KEY',
                          'ETCDCTL_USER', 'ETCDCTL_PASSWORD',
                          'ETCDCTL_INSECURE_TRANSPORT', 'ETCDCTL_TLS_SERVER_NAME'}
    for name in list(env):
        if name.startswith('ETCDCTL_') and name not in connection_options:
            del env[name]
    env['ETCDCTL_API'] = '3'
    return env


def txn_outcome(stdout):
    """Return etcdctl's reported transaction outcome, or None if absent."""
    for line in stdout.splitlines():
        line = line.strip()
        if line:
            return line if line in ("SUCCESS", "FAILURE") else None
    return None
