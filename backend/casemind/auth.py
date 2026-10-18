"""Google identity verification and revocable opaque sessions."""
import hashlib
import hmac
import secrets
import re
import time

from google.auth.transport.requests import Request
from google.oauth2 import id_token

from .store import mutate


def owner_hash(owner: str) -> str:
    return hashlib.sha256(owner.encode()).hexdigest()


class BoundedIdentityRequest:
    def __init__(self):
        self.request = Request()

    def __call__(self, url, method="GET", body=None, headers=None, timeout=5, **kwargs):
        return self.request(url=url, method=method, body=body, headers=headers,
                            timeout=min(float(timeout), 5), **kwargs)


class Sessions:
    def __init__(self, store, secret: str, audience: str, allowlist, verifier=None):
        if len(secret) < 32:
            raise ValueError("Session signing secret must contain at least thirty-two characters")
        self.store, self.secret, self.audience = store, secret.encode(), audience
        self.allowlist = set(allowlist)
        self.verifier = verifier or id_token.verify_oauth2_token

    def verify_google(self, credential: str, csrf_cookie: str, csrf_body: str):
        if not csrf_cookie or not hmac.compare_digest(csrf_cookie, csrf_body):
            raise PermissionError("Login CSRF token mismatch")
        if not self.audience or not self.allowlist:
            raise PermissionError("Google sign-in is not configured")
        if self.verifier is id_token.verify_oauth2_token and (not isinstance(credential, str) or len(credential) > 8192 or not re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", credential)):
            raise PermissionError("Malformed Google credential")
        claims = self.verifier(credential, BoundedIdentityRequest(), self.audience)
        if (claims.get("aud") != self.audience
                or claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com")
                or claims.get("exp", 0) <= time.time()
                or claims.get("sub") not in self.allowlist):
            raise PermissionError("Google identity is not authorized")
        return claims["sub"]

    def issue(self, owner: str, anonymous_session: str | None = None, previous=None):
        if owner not in self.allowlist:
            raise PermissionError("Identity is not authorized")
        # Persist proof before rotation so a restarted bootstrap can continue.
        if anonymous_session:
            key = f"claims/{owner_hash(owner)}/{owner_hash(anonymous_session)}"
            mutate(self.store, key, lambda old: old or {
                "owner": owner, "session": anonymous_session, "cursor": None, "complete": False,
            })
        if anonymous_session:
            mutate(self.store, f"claimed-sessions/{owner_hash(anonymous_session)}",
                   lambda old: old or {"owner": owner, "revoked": True})
        if previous:
            self.revoke(previous)
        opaque = secrets.token_hex(32)
        signature = hmac.new(self.secret, opaque.encode(), hashlib.sha256).hexdigest()
        self.store.put(f"sessions/{owner_hash(opaque)}", {
            "owner": owner, "expires": time.time() + 86400, "revoked": False,
            "created": time.time(), "version": 1,
        })
        return opaque + "." + signature

    def _key(self, cookie):
        opaque, _, signature = (cookie or "").partition(".")
        if len(opaque) != 64 or not hmac.compare_digest(
            signature, hmac.new(self.secret, opaque.encode(), hashlib.sha256).hexdigest()
        ):
            raise PermissionError("Invalid authenticated session")
        return f"sessions/{owner_hash(opaque)}"

    def resolve(self, cookie):
        record, _ = self.store.get(self._key(cookie))
        if not record or record["revoked"] or record["expires"] <= time.time():
            raise PermissionError("Authenticated session expired or revoked")
        if record["owner"] not in self.allowlist:
            raise PermissionError("Identity is no longer authorized")
        return record["owner"]

    def revoke(self, cookie):
        key = self._key(cookie)
        def revoke(record):
            if not record:
                raise PermissionError("Unknown session")
            return record | {"revoked": True, "version": record["version"] + 1}
        mutate(self.store, key, revoke)

    def owns_run(self, owner, run):
        if run.get("owner_id") == owner:
            return True
        session = run.get("session")
        if not session:
            return False
        proof, _ = self.store.get(f"claims/{owner_hash(owner)}/{owner_hash(session)}")
        return bool(proof and proof["owner"] == owner and proof["session"] == session)

    def bootstrap(self, owner, anonymous_session, limit=100):
        key = f"claims/{owner_hash(owner)}/{owner_hash(anonymous_session)}"
        proof, version = self.store.get(key)
        if not proof or proof["session"] != anonymous_session or proof["owner"] != owner:
            raise PermissionError("No persisted anonymous claim proof")
        if proof["complete"]:
            return proof
        keys, cursor = self.store.scan_keys("runs/", cursor=proof["cursor"], limit=limit)
        for run_key in keys:
            run, _ = self.store.get(run_key)
            if run and run.get("session") == anonymous_session:
                run_id = run_key.removeprefix("runs/")
                mutate(self.store, f"claimed-runs/{owner_hash(owner)}/{run_id}",
                       lambda old: old or {"run_id": run_id, "owner": owner,
                                           "proof": key, "case_id": run["case_id"]})
                from .continuity import index_run
                index_run(self.store, owner, run_id)
        proof = proof | {"cursor": cursor, "complete": cursor is None}
        self.store.put(key, proof, version)
        return proof

    def owner_scopes(self, owner, cursor=None, limit=100):
        """Old artifact namespaces are accessible only through persisted claim proof."""
        keys, cursor = self.store.scan_keys(f"claims/{owner_hash(owner)}/", cursor=cursor, limit=limit)
        owners = [owner]
        for key in keys:
            proof, _ = self.store.get(key)
            if proof and proof.get("owner") == owner and proof.get("session"):
                owners.append(proof["session"])
        return sorted(set(owners)), cursor

    def bootstrap_all(self, owner, cursor=None, limit=100):
        keys, cursor = self.store.scan_keys(f"claims/{owner_hash(owner)}/", cursor=cursor, limit=limit)
        proofs = []
        for key in keys:
            proof, _ = self.store.get(key)
            if proof and proof.get("owner") == owner:
                proofs.append(self.bootstrap(owner, proof["session"], limit=limit))
        return {"claims": proofs, "cursor": cursor,
                "complete": cursor is None and all(p["complete"] for p in proofs)}
