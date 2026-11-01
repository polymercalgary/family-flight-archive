#!/usr/bin/env python3
"""Offline test of flights.Google.user() re-login logic with stub Google modules. Run: python3 -I flights/test_auth.py"""
import importlib.util, sys, tempfile, types, threading
from pathlib import Path
calls = []
class RefreshError(Exception): pass
class Creds:
    mode = "ok"
    def __init__(self, src): self.src, self.refresh_token, self.valid = src, "r", False
    @classmethod
    def from_authorized_user_file(cls, path, scopes): calls.append("load"); return cls("file")
    def refresh(self, req):
        calls.append("refresh")
        if Creds.mode == "revoked": raise RefreshError("invalid_grant: Token has been expired or revoked.")
        self.valid = True
    def to_json(self): return '{"src": "%s"}' % self.src
class Flow:
    @classmethod
    def from_client_secrets_file(cls, path, scopes): return cls()
    def run_local_server(self, port): calls.append("browser"); c = Creds("browser"); c.valid = True; return c
def mod(name, **kw):
    m = types.ModuleType(name); m.__dict__.update(kw); sys.modules[name] = m
mod("google"); mod("google.auth"); mod("google.auth.exceptions", RefreshError=RefreshError)
mod("google.auth.transport"); mod("google.auth.transport.requests", Request=lambda: None)
mod("google.oauth2"); mod("google.oauth2.credentials", Credentials=Creds)
mod("google_auth_oauthlib"); mod("google_auth_oauthlib.flow", InstalledAppFlow=Flow)
mod("googleapiclient"); mod("googleapiclient.discovery", build=lambda *a, **k: ("svc", a[0]))
spec = importlib.util.spec_from_file_location("fl", Path(__file__).resolve().parent.parent / "flights.py")
F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
T = Path(tempfile.mkdtemp()); F.UPLOAD_TOKEN_FILE = T / "upload_token.json"; F.CLIENT_SECRET_FILE = T / "client_secret.json"
F.CLIENT_SECRET_FILE.write_text("{}")
fails = 0
def check(c, m):
    global fails; print(("PASS " if c else "FAIL ") + m); fails += 0 if c else 1
def new_g():
    g = F.Google.__new__(F.Google); g._user = None; return g
F.UPLOAD_TOKEN_FILE.write_text('{"src":"old"}'); Creds.mode = "revoked"; calls.clear()
u = new_g().user()
check(calls == ["load", "refresh", "browser"] and '"browser"' in F.UPLOAD_TOKEN_FILE.read_text(), "R1 revoked token -> deleted, browser login, new token saved: %s" % calls)
Creds.mode = "ok"; calls.clear()
u = new_g().user()
check(calls == ["load", "refresh"], "R2 valid token -> refreshed, no browser: %s" % calls)
F.UPLOAD_TOKEN_FILE.unlink(); calls.clear()
u = new_g().user()
check(calls == ["browser"] and F.UPLOAD_TOKEN_FILE.exists(), "R3 no token -> browser login: %s" % calls)
g = new_g(); calls.clear(); g.user(); g.user()
check(calls.count("refresh") == 1, "R4 checked once per run, reused after")
print("RESULT " + ("ALL PASS" if not fails else "FAIL %d" % fails)); sys.exit(1 if fails else 0)
