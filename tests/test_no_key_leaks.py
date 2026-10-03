"""No key or password value reaches report.html, handoff.md, vibexray.json, or the terminal.

Each value below is a test vector for one leak path that a code review reproduced. The
strings are split so that this file never holds a whole key, and the repo's own key
scanner stays quiet.
"""

import json

import pytest
from conftest import load_report_json

from vibexray.rules.base import hide, redact

BEGIN = "-----BEGIN " + "PRIVATE KEY-----"
END = "-----END " + "PRIVATE KEY-----"
KEY_BODY = "QUJDREVGR0hJSktMTU5PUFFSU1RVVldY"
STRIPE_TEST = "sk_" + "test_51HxAbCdEfGhIjKlMnOpQrSt"
STRIPE_LIVE = "sk_" + "live_AbCdEfGhIjKlMnOpQrStUv"
SLACK = "xo" + "xs-1234567890-abcdefghij"

VALUES = {
    "url password": "hunter2pass",
    "env password": "correcthorsebattery",
    "private key body": KEY_BODY,
    "stripe test key": STRIPE_TEST[8:],
    "stripe live key": STRIPE_LIVE[8:],
    "slack token": SLACK[5:],
    "jwt literal": "supersecretword9",
    "fallback literal": "fallback-signing-secret",
}


@pytest.mark.parametrize(
    "text, value",
    [
        ("DATABASE_URL=postgres://admin:hunter2pass@db.internal:5432/app", "hunter2pass"),
        ("ADMIN_PASSWORD=correcthorsebattery", "correcthorsebattery"),
        (f'FIREBASE_PRIVATE_KEY="{BEGIN}\\n{KEY_BODY}\\n{END}\\n"', KEY_BODY),
        (f"{BEGIN}\n{KEY_BODY}\n{END}", KEY_BODY),
        (f'const stripe = new Stripe("{STRIPE_TEST}");', STRIPE_TEST[8:]),
        (f'const token = "{SLACK}";', SLACK[5:]),
        ("const t = jwt.sign(payload, 'supersecretword9');", "supersecretword9"),
        (
            "const s = process.env.JWT_SECRET || 'fallback-signing-secret';",
            "fallback-signing-secret",
        ),
        ('const apiKey = "abc123def456ghi789";', "abc123def456ghi789"),
    ],
)
def test_hide_removes_the_value(text, value):
    assert value not in hide(text)
    assert value not in redact(text)


@pytest.mark.parametrize(
    "text",
    [
        "const password = req.body.password;",
        "if (!user.password) return res.status(401).end();",
        "const url = 'https://api.example.com/v1/orders';",
        "task-runner-config",
        "password: z.string().min(8),",
    ],
)
def test_hide_leaves_ordinary_code_alone(text):
    assert hide(text) == text


def _project(root):
    (root / "src").mkdir(parents=True)
    (root / ".env").write_text(
        "DATABASE_URL=postgres://admin:hunter2pass@db.internal:5432/app\n"
        "ADMIN_PASSWORD=correcthorsebattery\n"
        f'FIREBASE_PRIVATE_KEY="{BEGIN}\\n{KEY_BODY}\\n{END}\\n"\n'
    )
    (root / "src" / "pay.ts").write_text(f'const stripe = new Stripe("{STRIPE_TEST}");\n')
    (root / "src" / "slack.ts").write_text(f'export const token = "{SLACK}";\n')
    (root / "src" / "auth.ts").write_text(
        "import jwt from 'jsonwebtoken';\n"
        "const secret = process.env.JWT_SECRET || 'fallback-signing-secret';\n"
        "export const sign = (payload) => jwt.sign(payload, 'supersecretword9');\n"
    )
    (root / "src" / "a.ts").write_text("export const refundThreshold = 100;\n")
    (root / "src" / "b.ts").write_text(
        f'export const refundThreshold = 200; const k = "{STRIPE_LIVE}";\n'
    )


def test_no_value_reaches_any_output(cli, tmp_path):
    root = tmp_path / "app"
    _project(root)
    out = tmp_path / "report"
    scan = cli("scan", str(root), "--out", str(out), "--no-run", "--no-history", "--json")
    assert scan.returncode == 0, scan.stderr
    review = [
        {
            "category": "secret_exposure",
            "file": ".env",
            "line": 1,
            "quote": "DATABASE_URL",
            "pm_text": "The database password sits in a committed file.",
            "engineer_text": "Move DATABASE_URL to the host's key store and rotate it.",
            "label": "rewrite",
            "severity": "high",
            "related_file": ".env",
            "related_line": 3,
        }
    ]
    (out / "review.json").write_text(json.dumps(review))
    merged = cli("review", str(out))
    assert merged.returncode == 0, merged.stderr
    assert "Kept 1 of 1" in merged.stdout
    outputs = {
        "scan --json": scan.stdout,
        "report.html": (out / "report.html").read_text(),
        "handoff.md": (out / "handoff.md").read_text(),
        "vibexray.json": (out / "vibexray.json").read_text(),
        "review stdout": merged.stdout,
    }
    for where, text in outputs.items():
        for name, value in VALUES.items():
            assert value not in text, f"{name} leaked into {where}"
    assert load_report_json(out)["findings"]
