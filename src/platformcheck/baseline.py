"""Hardening baseline for a Compose-based platform stack. Each rule has an id so an audit can cite it."""
from __future__ import annotations

import re

import yaml

LOOPBACK = ("127.0.0.1", "::1", "localhost")


def check(compose_text: str) -> list[dict]:
    doc = yaml.safe_load(compose_text)
    findings: list[dict] = []
    for name, svc in (doc.get("services") or {}).items():
        def add(rule, ok, detail):
            findings.append({"service": name, "rule": rule, "passed": bool(ok), "detail": detail})

        image = svc.get("image", "")
        tag = image.rsplit(":", 1)[1] if ":" in image.rsplit("/", 1)[-1] else ""
        pinned = bool(tag) and not re.search(r"latest|^\$\{[A-Z_]+\}$", tag)
        add("B1 image tag is pinned", pinned, image)

        pub = [p for p in svc.get("ports", [])]
        add("B2 published ports bind to loopback", all(str(p).split(":")[0] in LOOPBACK for p in pub if ":" in str(p)), pub or "none published")

        env = svc.get("environment") or {}
        pairs = env.items() if isinstance(env, dict) else (e.split("=", 1) for e in env)
        literal = [k for k, v in pairs if re.search(r"PASSWORD|SECRET|KEY|TOKEN", k) and v and not str(v).startswith("${")]
        add("B3 no literal secrets in the file", not literal, literal or "all secrets come from the environment")

        add("B4 restart policy set", svc.get("restart") in ("unless-stopped", "always", "on-failure"), svc.get("restart"))
        add("B5 healthcheck defined", "healthcheck" in svc, "yes" if "healthcheck" in svc else "missing")
        add("B6 no-new-privileges", "no-new-privileges:true" in (svc.get("security_opt") or []), svc.get("security_opt"))

        if image.startswith("redis"):
            cmd = " ".join(svc.get("command") or [])
            add("B7 redis uses noeviction (queue data must not be evicted)", "noeviction" in cmd, cmd)
            add("B8 redis persistence on", "appendonly yes" in cmd, cmd)
    return findings


def summarize(findings: list[dict]) -> tuple[int, int]:
    failed = sum(1 for f in findings if not f["passed"])
    return len(findings) - failed, failed
