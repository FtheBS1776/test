#!/usr/bin/env python3
"""Capture a bounded NONCLAIM etcd implementation-integration run."""
import argparse
import hashlib
import json
import os
import pathlib
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from secure_fixture import make_certificates, tls_context, bootstrap_rbac

BASE = pathlib.Path(__file__).resolve().parent
ARCHIVE_SHA = "66bad39ed920f6fc15fd74adcb8bfd38ba9a6412f8c7852d09eb11670e88cac3"
ARCHIVE_URL = "https://github.com/etcd-io/etcd/releases/download/v3.6.5/etcd-v3.6.5-linux-amd64.tar.gz"
BIN_SHA = {
    "etcd": "030b4b2efd1bcc9ab043080c35f7bb68551e962b23efe62e2f2713429bd9e0f2",
    "etcdctl": "18416269c49d0f25624938b0b45d5bd5d3eb980ab92048dc4652c66a4246141e",
}


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def write(path, value):
    pathlib.Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def command(argv, log, env=None, timeout=20):
    with open(log, "wb") as f:
        try:
            p = subprocess.Popen(argv, stdout=f, stderr=subprocess.STDOUT, env=env,
                                 start_new_session=True)
            rc = p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try: os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            p.wait()
            f.write(b"\nHARNESS_COMMAND_TIMEOUT\n")
            rc = 124
        except OSError as e:
            f.write(("HARNESS_COMMAND_ERROR " + repr(e) + "\n").encode())
            rc = 127
    write(str(log) + ".command.json", {"argv": argv, "exit_code": rc})
    return rc


def verify_source(expected):
    manifest = BASE / "SOURCE_MANIFEST.json"
    if not manifest.is_file() or sha(manifest) != expected:
        raise ValueError("SOURCE_MANIFEST_SHA256_MISMATCH")
    members = json.loads(manifest.read_text())
    actual = {p.name for p in BASE.iterdir() if p.is_file()}
    if actual != set(members) | {"SOURCE_MANIFEST.json"}:
        raise ValueError("SOURCE_INVENTORY_MISMATCH")
    for name, digest in members.items():
        if pathlib.PurePath(name).name != name or sha(BASE / name) != digest:
            raise ValueError("SOURCE_MEMBER_MISMATCH:" + name)


def verify_github_context():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return {"mode": "LOCAL_REHEARSAL"}
    required = ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_REPOSITORY_ID",
                "GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_WORKFLOW_REF",
                "GITHUB_WORKFLOW_SHA", "GITHUB_EVENT_NAME")
    ctx = {k: os.environ.get(k) for k in required}
    for k in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_REPOSITORY_ID"):
        if not re.fullmatch(r"[1-9][0-9]*", ctx[k] or ""):
            raise ValueError("BAD_GITHUB_CONTEXT:" + k)
    if not re.fullmatch(r"[0-9a-f]{40}", ctx["GITHUB_SHA"] or ""):
        raise ValueError("BAD_GITHUB_CONTEXT:GITHUB_SHA")
    return {"mode": "GITHUB_HOSTED", **ctx}


def extract_release(archive, work):
    if sha(archive) != ARCHIVE_SHA:
        raise ValueError("ETCD_ARCHIVE_SHA256_MISMATCH")
    out = work / "bin"
    out.mkdir()
    with tarfile.open(archive, "r:gz") as tf:
        for name in BIN_SHA:
            member = tf.getmember("etcd-v3.6.5-linux-amd64/" + name)
            if not member.isfile():
                raise ValueError("NONREGULAR_RELEASE_BINARY:" + name)
            dest = out / name
            dest.write_bytes(tf.extractfile(member).read())
            dest.chmod(0o700)
            if sha(dest) != BIN_SHA[name]:
                raise ValueError("ETCD_BINARY_SHA256_MISMATCH:" + name)
    return out / "etcd", out / "etcdctl"


def find_cluster_id(status_path):
    obj = json.loads(pathlib.Path(status_path).read_text())
    if isinstance(obj, list) and obj:
        obj = obj[0]
    if isinstance(obj, dict) and "Status" in obj:
        obj = obj["Status"]
    for candidate in (obj, obj.get("header", {}) if isinstance(obj, dict) else {}):
        if isinstance(candidate, dict):
            x = candidate.get("cluster_id") or candidate.get("clusterId")
            if x is not None:
                return str(x)
    raise ValueError("CLUSTER_ID_NOT_CAPTURED")


def seal(out):
    files = {}
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "EVIDENCE_MANIFEST.json":
            files[p.relative_to(out).as_posix()] = sha(p)
    write(out / "EVIDENCE_MANIFEST.json", files)


def verify_no_secret_leak(out, secret_values, private_key_paths):
    needles = [x.encode("utf-8") for x in secret_values if x]
    needles.extend(pathlib.Path(p).read_bytes() for p in private_key_paths)
    leaked = []
    for path in pathlib.Path(out).rglob("*"):
        if path.is_file():
            raw = path.read_bytes()
            if any(needle in raw for needle in needles):
                leaked.append(path)
    for path in leaked:
        path.write_text("EVIDENCE_REDACTED_EPHEMERAL_SECRET_LEAK; original bytes removed\n")
    if leaked:
        raise ValueError("EPHEMERAL_SECRET_IN_EVIDENCE:" +
                         ",".join(path.relative_to(out).as_posix() for path in leaked))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--expected-source-manifest", required=True)
    ap.add_argument("--release-archive", help="only for clearly labelled local rehearsal")
    args = ap.parse_args()
    out = pathlib.Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    status = {"state": "INDETERMINATE", "controlling_pass": 186,
              "promotion": False, "freeze": False,
              "claim_scope": "bounded single-member etcd 3.6.5 HTTPS + password-RBAC gateway fixture"}
    proc = None
    server_log = None
    try:
        context = verify_github_context()
        if args.release_archive and context["mode"] != "LOCAL_REHEARSAL":
            raise ValueError("ARCHIVE_OVERRIDE_FORBIDDEN_ON_GITHUB")
        verify_source(args.expected_source_manifest)
        status["context"] = context
        status["source_manifest_sha256"] = sha(BASE / "SOURCE_MANIFEST.json")
        source_out = out / "SOURCE"
        source_out.mkdir()
        shutil.copy2(BASE / "SOURCE_MANIFEST.json", source_out / "SOURCE_MANIFEST.json")
        source_manifest = json.loads((BASE / "SOURCE_MANIFEST.json").read_text())
        for name in source_manifest:
            shutil.copy2(BASE / name, source_out / name)
        workflow = BASE.parent / ".github" / "workflows" / "pass219-etcd-tls-rbac.yml"
        if workflow.is_file():
            shutil.copy2(workflow, out / "EXECUTED_WORKFLOW.yml")
            status["workflow_sha256"] = sha(workflow)
        with tempfile.TemporaryDirectory(prefix="pass219-etcd-") as td:
            work = pathlib.Path(td)
            archive = work / "release.tar.gz"
            if args.release_archive:
                shutil.copyfile(args.release_archive, archive)
            else:
                rc = command(["curl", "--fail", "--location", "--silent", "--show-error",
                              "--proto", "=https", "--tlsv1.2", "--max-time", "120",
                              "--output", str(archive), ARCHIVE_URL], out / "DOWNLOAD.txt", timeout=130)
                if rc != 0:
                    raise RuntimeError("ETCD_DOWNLOAD_FAILED")
            status["release_archive_sha256"] = sha(archive)
            etcd, etcdctl = extract_release(archive, work)
            status["binary_sha256"] = {k: sha(work / "bin" / k) for k in BIN_SHA}
            env = {k: v for k, v in os.environ.items() if not k.startswith(("ETCD_", "ETCDCTL_"))}
            client_port, peer_port = port(), port()
            endpoint = f"https://127.0.0.1:{client_port}"
            peer = f"http://127.0.0.1:{peer_port}"
            data = work / "data"
            ca_file, server_cert_file, server_key_file = make_certificates(work / "pki")
            argv = [str(etcd), "--name", "pass219-integration", "--data-dir", str(data),
                    "--listen-client-urls", endpoint, "--advertise-client-urls", endpoint,
                    "--listen-peer-urls", peer, "--initial-advertise-peer-urls", peer,
                    "--initial-cluster", "pass219-integration=" + peer,
                    "--initial-cluster-token", work.name, "--initial-cluster-state", "new",
                    "--cert-file", str(server_cert_file), "--key-file", str(server_key_file)]
            write(out / "SERVER_COMMAND.json", argv)
            server_log = open(out / "SERVER_LOG.txt", "wb")
            proc = subprocess.Popen(argv, stdout=server_log, stderr=subprocess.STDOUT, env=env,
                                   start_new_session=True)
            ctl = [str(etcdctl), "--endpoints=" + endpoint, "--cacert=" + str(ca_file),
                   "--command-timeout=3s", "--dial-timeout=2s"]
            ready = False
            for i in range(40):
                if proc.poll() is not None:
                    raise RuntimeError("ETCD_EXITED_BEFORE_READY")
                rc = command(ctl + ["endpoint", "health"], out / f"HEALTH_{i:02}.txt", env, timeout=5)
                if rc == 0:
                    ready = True
                    break
                time.sleep(0.25)
            if not ready:
                raise RuntimeError("ETCD_READINESS_TIMEOUT")
            command(ctl + ["endpoint", "status", "-w", "json"], out / "ENDPOINT_BEFORE.json", env)
            cluster_id = find_cluster_id(out / "ENDPOINT_BEFORE.json")
            test_scope = (context.get("GITHUB_RUN_ID", "local") + "." +
                          context.get("GITHUB_RUN_ATTEMPT", str(os.getpid())) + "." +
                          secrets.token_hex(8))
            namespace = "/brains10/pass219-etcd/" + test_scope
            auth = bootstrap_rbac(endpoint, tls_context(ca_file), namespace, out, work)
            status["tls_server_certificate_sha256"] = sha(server_cert_file)
            status["tls_ca_certificate_sha256"] = sha(ca_file)
            status["tls"] = "server-authenticated-https"
            status["auth_mode"] = "password-rbac-simple-test-token"
            test_env = dict(env)
            test_env.update({"BRAINS10_ETCD_ENDPOINT": endpoint,
                             "BRAINS10_ETCD_CLUSTER_ID": cluster_id,
                             "BRAINS10_TEST_SCOPE": test_scope,
                             "BRAINS10_ETCD_CA_FILE": str(ca_file),
                             "BRAINS10_ETCD_WRONG_CA_FILE": auth["wrong_ca_path"],
                             "BRAINS10_ETCD_AUTH_TOKEN": auth["user_token"],
                             "BRAINS10_ETCD_ROOT_TOKEN": auth["root_token"],
                             "BRAINS10_ETCD_TEST_USER": auth["user_name"],
                             "BRAINS10_EVIDENCE_DIR": str(out)})
            py = sys.executable
            rc = command([py, "-B", str(BASE / "test_integration.py")],
                         out / "TEST_RESULTS.txt", test_env, timeout=180)
            status["integration_exit_code"] = rc
            key_paths = [p for p in work.rglob("*.key") if p.is_file()]
            verify_no_secret_leak(out, auth["secret_values"], key_paths)
            status["secret_and_private_key_scan"] = "PASS"
            status["server_version_exit_code"] = command([str(etcd), "--version"], out / "SERVER_VERSION.txt", env)
            status["client_version_exit_code"] = command([str(etcdctl), "version"], out / "CLIENT_VERSION.txt", env)
            status.update({"endpoint": endpoint, "cluster_id": cluster_id, "member_count": 1,
                           "namespace": namespace, "credentials_durable": False,
                           "client_certificate_auth": False})
            if rc == 0 and proc.poll() is None:
                status["state"] = "CAPTURE_COMPLETE_PENDING_ADJUDICATION"
            else:
                status["error"] = "INTEGRATION_TEST_OR_SERVER_FAILED"
    except Exception as e:
        status["error"] = type(e).__name__ + ": " + str(e)
    finally:
        if proc is not None:
            proc.terminate()
            try: proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait()
                status["cleanup_forced_kill"] = True
        if server_log:
            server_log.close()
        write(out / "CAPTURE_STATUS.json", status)
        seal(out)
    print(json.dumps(status, sort_keys=True))
    return 0 if status["state"] == "CAPTURE_COMPLETE_PENDING_ADJUDICATION" else 2


if __name__ == "__main__":
    sys.exit(main())
