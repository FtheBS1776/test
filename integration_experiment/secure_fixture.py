"""Run-scoped HTTPS and RBAC fixture setup for NONCLAIM integration tests."""
from __future__ import annotations

import base64
import datetime
import hashlib
import ipaddress
import json
import os
import pathlib
import secrets
import ssl
import urllib.error
import urllib.request

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def prefix_end(prefix: bytes) -> bytes:
    """Return etcd's lexical exclusive end for the exact byte prefix."""
    data = bytearray(prefix)
    for i in range(len(data) - 1, -1, -1):
        if data[i] != 0xFF:
            data[i] += 1
            return bytes(data[:i + 1])
    return b"\0"


def _private_key(path: pathlib.Path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
    path.chmod(0o600)
    return key


def make_certificates(directory: pathlib.Path):
    directory.mkdir(parents=True, exist_ok=True)
    ca_key_path, ca_cert_path = directory / "fixture-ca.key", directory / "fixture-ca.pem"
    server_key_path, server_cert_path = directory / "server.key", directory / "server.pem"
    ca_key = _private_key(ca_key_path)
    now = datetime.datetime.now(datetime.timezone.utc)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "BRAINS10 ephemeral test CA")])
    ca_cert = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
        .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False,
            key_encipherment=False, data_encipherment=False, key_agreement=False,
            key_cert_sign=True, crl_sign=True, encipher_only=False, decipher_only=False), critical=True)
        .sign(ca_key, hashes.SHA256()))
    ca_cert_path.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
    ca_cert_path.chmod(0o600)

    server_key = _private_key(server_key_path)
    server_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    server_cert = (x509.CertificateBuilder().subject_name(server_name).issuer_name(ca_name)
        .public_key(server_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([
            x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
            x509.DNSName("localhost")]), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256()))
    server_cert_path.write_bytes(server_cert.public_bytes(serialization.Encoding.PEM))
    server_cert_path.chmod(0o600)
    return ca_cert_path, server_cert_path, server_key_path


def tls_context(ca_path: pathlib.Path) -> ssl.SSLContext:
    context = ssl.create_default_context(cafile=str(ca_path))
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    return context


def _post(endpoint: str, path: str, value: dict, context: ssl.SSLContext,
          auth_token: str | None = None) -> tuple[int, dict]:
    body = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = auth_token
    request = urllib.request.Request(endpoint + path, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, context=context, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        # Setup and negative auth responses are never copied into durable evidence.
        return error.code, {}


def bootstrap_rbac(endpoint: str, context: ssl.SSLContext, namespace: str,
                   evidence_dir: pathlib.Path, work_dir: pathlib.Path) -> dict:
    """Create ephemeral fixture-only users; return secrets for in-memory runner use."""
    root_password = secrets.token_urlsafe(32)
    user_password = secrets.token_urlsafe(32)
    user_name = "fixture_" + secrets.token_hex(8)
    role_name = "fixture_role_" + secrets.token_hex(8)
    prefix = (namespace.rstrip("/") + "/").encode("utf-8")
    steps = []

    def call(path, body, expected=(200,)):
        status, _ = _post(endpoint, path, body, context)
        steps.append({"path": path, "http_status": status})
        if status not in expected:
            raise RuntimeError("RBAC_SETUP_FAILED:" + path + ":" + str(status))

    call("/v3/auth/user/add", {"name": "root", "password": root_password})
    call("/v3/auth/user/grant", {"user": "root", "role": "root"})
    call("/v3/auth/role/add", {"name": role_name})
    call("/v3/auth/role/grant", {"name": role_name, "key": b64(prefix),
         "range_end": b64(prefix_end(prefix)), "permType": "READWRITE"})
    call("/v3/auth/user/add", {"name": user_name, "password": user_password})
    call("/v3/auth/user/grant", {"user": user_name, "role": role_name})
    call("/v3/auth/enable", {})

    def authenticate(name, password):
        status, result = _post(endpoint, "/v3/auth/authenticate",
            {"name": name, "password": password}, context)
        steps.append({"path": "/v3/auth/authenticate", "http_status": status,
                      "token_redacted": True})
        if status != 200 or type(result.get("token")) is not str or not result["token"]:
            raise RuntimeError("FIXTURE_AUTHENTICATE_FAILED:" + str(status))
        return result["token"]

    root_token = authenticate("root", root_password)
    user_token = authenticate(user_name, user_password)
    # A second unrelated CA supports negative chain-validation tests.
    wrong_ca, _, _ = make_certificates(work_dir / "wrong-ca")
    metadata = {"fixture": "one-member-etcd-3.6.5", "tls": "server-auth-only",
        "auth_mode": "password-authenticated-simple-test-token",
        "user_name": user_name, "role_name": role_name,
        "namespace_prefix_sha256": hashlib.sha256(prefix).hexdigest(),
        "steps": steps, "passwords_and_tokens_captured": False}
    (evidence_dir / "AUTH_SETUP_REDACTED.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return {"user_name": user_name, "user_password": user_password,
            "root_token": root_token, "user_token": user_token,
            "wrong_ca_path": str(wrong_ca),
            "secret_values": [root_password, user_password, root_token, user_token]}
