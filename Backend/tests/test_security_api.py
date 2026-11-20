"""API contracts with injected disposable DB; real registration in a child process."""
import os
from contextlib import contextmanager
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app import dbcompat, trading, wallet


class SecurityApiTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = str(Path(directory.name) / "api.db")
        environment = patch.dict(os.environ, {"PLANWISE_DB": self.path})
        environment.start()
        self.addCleanup(environment.stop)
        with self.db() as conn:
            conn.executescript("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT);"
                               "INSERT INTO users VALUES (1, 'one@example.test');"
                               "INSERT INTO users VALUES (2, 'two@example.test');")
        app = FastAPI()
        app.include_router(wallet.build_router(self.db, self.user))
        app.include_router(trading.build_router(self.db, self.user))
        client = TestClient(app)
        self.addCleanup(client.close)
        self.client = client
        client.cookies.set("session", "one")
        quote = patch.object(trading, "fetch_latest_bar", return_value={
            "date": "2026-01-01", "open": 100, "high": 100, "low": 100,
            "close": 100, "volume": 1,
        })
        quote.start()
        self.addCleanup(quote.stop)

    @contextmanager
    def db(self):
        conn = dbcompat.connect(self.path)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    @staticmethod
    def user(conn, session):
        if session not in ("one", "two"):
            raise HTTPException(401, "Not signed in")
        return conn.execute("SELECT id FROM users WHERE id=?",
                            (1 if session == "one" else 2,)).fetchone()

    def test_wallet_response_and_history_contracts(self):
        expected_wallet = {"balance", "starting_balance", "change", "change_pct",
                           "currency", "updated_at"}
        response = self.client.get("/api/wallet")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), expected_wallet)
        response = self.client.post("/api/wallet/deposit", json={"amount": 25.25, "note": " x "})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(set(data), {"wallet", "transaction"})
        self.assertEqual(set(data["wallet"]), expected_wallet)
        self.assertEqual(set(data["transaction"]),
                         {"id", "kind", "amount", "balance_after", "note", "created_at"})
        self.assertEqual(data["transaction"]["note"], "x")
        self.assertEqual(data["wallet"]["balance"], 1025.25)
        response = self.client.post("/api/wallet/withdraw", json={"amount": 25.25})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["wallet"]["balance"], 1000)
        response = self.client.post("/api/wallet/withdraw", json={"amount": 1000.01})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {"detail": "Insufficient wallet balance"})
        history = self.client.get("/api/wallet/history").json()
        self.assertEqual(set(history), {"starting_balance", "items"})
        self.assertEqual(set(history["items"][0]), {"balance", "change_pct", "created_at"})
        txs = self.client.get("/api/wallet/transactions?limit=1&search=x&kind=deposit").json()
        self.assertEqual(set(txs), {"items", "total", "offset", "limit", "has_more"})
        self.assertEqual(txs["total"], 1)
        self.client.cookies.set("session", "two")
        self.assertEqual(self.client.get("/api/wallet/transactions").json()["total"], 0)
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/api/wallet").status_code, 401)

    def test_open_response_409_and_final_guard_error_mapping(self):
        self.client.get("/api/wallet")
        with patch.object(trading, "change_balance", side_effect=wallet.InsufficientFunds(
                "Insufficient wallet balance")):
            response = self.client.post("/api/positions", json={
                "ticker": "AAPL", "side": "long", "amount": 700, "leverage": 1})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {"detail": "Insufficient wallet balance"})
        with self.db() as conn:
            for table in ("positions", "trades", "wallet_transactions"):
                self.assertEqual(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM balance_history").fetchone()[0], 1)
        response = self.client.post("/api/positions", json={
            "ticker": "AAPL", "side": "short", "amount": 100, "leverage": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"position", "wallet"})
        self.assertEqual(response.json()["wallet"]["balance"], 900)
        position_id = response.json()["position"]["id"]
        response = self.client.post(f"/api/positions/{position_id}/close")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"trade", "wallet"})
        self.assertEqual(response.json()["trade"]["pnl"], 0)
        self.assertEqual(response.json()["wallet"]["balance"], 1000)

    def test_invalid_external_numbers_return_422_without_wallet_creation(self):
        for amount in (True, False, None, "10", "NaN", "Infinity", [], {}, 0, -1,
                       1_000_000.01, 0.001):
            for endpoint in ("/api/wallet/deposit", "/api/wallet/withdraw", "/api/positions"):
                with self.subTest(amount=amount, endpoint=endpoint):
                    body = {"amount": amount, "ticker": "AAPL", "side": "long"}
                    self.assertEqual(self.client.post(endpoint, json=body).status_code, 422)
        for token in ("NaN", "Infinity", "-Infinity"):
            for endpoint in ("/api/wallet/deposit", "/api/wallet/withdraw", "/api/positions"):
                content = '{"ticker":"AAPL","side":"long","amount":' + token + '}'
                self.assertEqual(self.client.post(endpoint, content=content,
                                 headers={"Content-Type": "application/json"}).status_code, 422)
            content = '{"ticker":"AAPL","side":"long","amount":10,"leverage":' + token + '}'
            self.assertEqual(self.client.post("/api/positions", content=content,
                             headers={"Content-Type": "application/json"}).status_code, 422)
        with self.db() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM wallets").fetchone()[0], 0)

    def test_real_registration_and_late_registration_failure(self):
        self.check_registration_rollback("ensure_wallet")

    def test_registration_rolls_back_after_session_creation(self):
        self.check_registration_rollback("start_session")

    def check_registration_rollback(self, failure_point):
        # Child env is set BEFORE importing main, which initializes schemas/seeds.
        child_path = str(Path(self.path).with_name("registration.db"))
        env = dict(os.environ, PLANWISE_DB=child_path, DATABASE_URL="")
        script = '''
import sys
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import main
with TestClient(main.app) as client:
    r = client.post('/api/auth/register', json={'email':'han@example.test','password':'password123'})
    assert r.status_code == 200, r.text
    assert client.get('/api/wallet').json()['balance'] == 1000
    failure_point = sys.argv[1]
    original = getattr(main, failure_point)
    def fail(*args, **kwargs):
        original(*args, **kwargs)
        if failure_point == 'start_session':
            conn, response, user_id = args
            assert conn.execute('SELECT COUNT(*) FROM sessions WHERE user_id=?', (user_id,)).fetchone()[0] == 1
            assert 'session=' in response.headers['set-cookie']
        raise RuntimeError('late registration failure')
    with patch.object(main, failure_point, side_effect=fail):
        try:
            client.post('/api/auth/register', json={'email':'rollback@example.test','password':'password123'})
        except RuntimeError:
            pass
        else:
            raise AssertionError('failure was swallowed')
with main.db() as conn:
    assert conn.execute("SELECT COUNT(*) FROM users WHERE email='rollback@example.test'").fetchone()[0] == 0
    assert conn.execute('SELECT COUNT(*) FROM wallets').fetchone()[0] == 2  # demo + successful user
    assert conn.execute('SELECT COUNT(*) FROM balance_history').fetchone()[0] == 2
    assert conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM auth_events WHERE email='rollback@example.test'").fetchone()[0] == 0
'''
        result = subprocess.run([sys.executable, "-c", script, failure_point], env=env, cwd=Path(__file__).parents[1],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
