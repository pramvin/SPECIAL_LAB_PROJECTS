"""Financial API replay and rollback on disposable default/WAL SQLite databases."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
import os
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app import dbcompat, idempotency, trading, wallet


class IdempotencyApiTest(unittest.TestCase):
    journal_mode = "delete"
    operations = ("deposit", "withdraw", "open", "close")

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = str(Path(directory.name) / "idempotency.db")
        environment = patch.dict(os.environ, {"PLANWISE_DB": self.path})
        environment.start()
        self.addCleanup(environment.stop)
        self.busy_timeout = 5000
        self.active_connections = set()
        with self.db() as conn:
            conn.executescript("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT);"
                               "INSERT INTO users VALUES (1, 'one@example.test');"
                               "INSERT INTO users VALUES (2, 'two@example.test');")
        self.client = self.new_client()
        with self.db() as conn:
            self.assertEqual(conn.execute(f"PRAGMA journal_mode={self.journal_mode}").fetchone()[0],
                             self.journal_mode)
        quote = patch.object(trading, "fetch_latest_bar", side_effect=self.bar)
        quote.start()
        self.addCleanup(quote.stop)

    @staticmethod
    def bar(_ticker):
        return dict(date="2026-01-02", open=100, high=100, low=100, close=100, volume=1)

    @contextmanager
    def db(self):
        conn = dbcompat.connect(self.path)
        conn.execute(f"PRAGMA busy_timeout={self.busy_timeout}")
        self.active_connections.add(id(conn))
        try:
            with conn:
                yield conn
        finally:
            conn.close()
            self.active_connections.remove(id(conn))

    @staticmethod
    def user(conn, session):
        if session not in ("one", "two"):
            raise HTTPException(401, "Not signed in")
        return conn.execute("SELECT id FROM users WHERE id = ?",
                            (1 if session == "one" else 2,)).fetchone()

    def new_client(self):
        app = FastAPI()
        app.include_router(wallet.build_router(self.db, self.user))
        app.include_router(trading.build_router(self.db, self.user))
        client = TestClient(app)
        self.addCleanup(client.close)
        return client

    def post(self, url, body=None, key=None, user="one", client=None):
        headers = {"Cookie": f"session={user}"}
        if key is not None:
            headers["Idempotency-Key"] = key
        return (client or self.client).post(url, json=body, headers=headers)

    def arrange(self, operation, user="one"):
        response = self.client.get("/api/wallet", headers={"Cookie": f"session={user}"})
        self.assertEqual(response.status_code, 200)
        if operation in ("deposit", "withdraw"):
            return f"/api/wallet/{operation}", {"amount": 20, "note": "test"}
        body = {"ticker": "AAPL", "side": "long", "amount": 20, "leverage": 1}
        if operation == "open":
            return "/api/positions", body
        opened = self.post("/api/positions", body, user=user)
        self.assertEqual(opened.status_code, 200)
        return f"/api/positions/{opened.json()['position']['id']}/close", None

    def state(self):
        with self.db() as conn:
            return {table: [dict(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY rowid")]
                    for table in ("wallets", "positions", "trades", "wallet_transactions",
                                  "balance_history", "prices", "financial_requests")}

    def test_sequential_retries_all_endpoints(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                url, body = self.arrange(operation)
                first = self.post(url, body, key=operation)
                self.assertEqual(first.status_code, 200, first.text)
                before = self.state()
                with patch.object(trading, "fetch_latest_bar", side_effect=AssertionError("replay fetched quote")):
                    replay = self.post(url, body, key=operation)
                self.assertEqual(replay.status_code, 200)
                self.assertEqual(replay.content, first.content)
                self.assertEqual(self.state(), before)

    def test_concurrent_retries_all_endpoints(self):
        original_lookup = idempotency.lookup
        for operation in self.operations:
            with self.subTest(operation=operation):
                url, body = self.arrange(operation)
                before = self.state()
                barrier = threading.Barrier(2)

                def lookup(conn, user_id, key, digest):
                    result = original_lookup(conn, user_id, key, digest)
                    if not conn.in_transaction:
                        barrier.wait(timeout=5)
                    return result

                with patch.object(idempotency, "lookup", side_effect=lookup), \
                        ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(self.post, url, body, operation) for _ in range(2)]
                    responses = [future.result(timeout=10) for future in futures]
                self.assertEqual([r.status_code for r in responses], [200, 200])
                self.assertEqual(responses[0].content, responses[1].content)
                after = self.state()
                self.assertEqual(len(after["financial_requests"]), len(before["financial_requests"]) + 1)
                self.assertEqual(len(after["balance_history"]), len(before["balance_history"]) + 1)
                delta = {"deposit": 20, "withdraw": -20, "open": -20, "close": 20}[operation]
                self.assertEqual(after["wallets"][0]["balance"], before["wallets"][0]["balance"] + delta)

    def test_key_conflicts_cover_operation_target_and_all_inputs(self):
        for operation in self.operations:
            with self.subTest(operation=operation):
                url, body = self.arrange(operation)
                self.assertEqual(self.post(url, body, key=operation).status_code, 200)
                alternatives = []
                if body is not None:
                    alternatives.append((url, dict(body, amount=21)))
                    if operation in ("deposit", "withdraw"):
                        alternatives.append((url, dict(body, note="changed")))
                    else:
                        alternatives.extend((url, dict(body, **change)) for change in (
                            {"ticker": "MSFT"}, {"side": "short"}, {"leverage": 2}))
                else:
                    alternatives.append(("/api/positions/999/close", None))
                alternatives.append(("/api/wallet/deposit", {"amount": 1}))
                before = self.state()
                for changed_url, changed_body in alternatives:
                    response = self.post(changed_url, changed_body, key=operation)
                    self.assertEqual(response.status_code, 409, response.text)
                    self.assertEqual(self.state(), before)

    def test_concurrent_different_inputs_conflict(self):
        url, body = self.arrange("deposit")
        barrier = threading.Barrier(2)
        original = idempotency.lookup

        def lookup(conn, *args):
            result = original(conn, *args)
            if not conn.in_transaction:
                barrier.wait(timeout=5)
            return result

        with patch.object(idempotency, "lookup", side_effect=lookup), ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.post, url, dict(body, amount=amount), "conflict") for amount in (20, 30)]
            results = [future.result(timeout=10) for future in futures]
        self.assertCountEqual([r.status_code for r in results], [200, 409])
        winner = next(r.json() for r in results if r.status_code == 200)
        self.assertEqual(self.state()["wallets"][0]["balance"], winner["wallet"]["balance"])
        self.assertEqual(len(self.state()["financial_requests"]), 1)

    def test_failed_claimant_rolls_back_and_waiting_retry_succeeds(self):
        original_lookup = idempotency.lookup
        original_record = idempotency.record
        for operation in self.operations:
            url, body = self.arrange(operation)
            before = self.state()
            barrier = threading.Barrier(2)
            attempted = []

            def lookup(conn, *args):
                result = original_lookup(conn, *args)
                if not conn.in_transaction:
                    barrier.wait(timeout=5)
                return result

            def record(conn, *args):
                if not attempted:
                    attempted.append(True)
                    original_record(conn, *args)
                    raise sqlite3.IntegrityError("injected failure after response record")
                return original_record(conn, *args)

            def request():
                try:
                    return self.post(url, body, key=operation).status_code
                except sqlite3.IntegrityError:
                    return "rolled_back"

            with patch.object(idempotency, "lookup", side_effect=lookup), \
                    patch.object(idempotency, "record", side_effect=record), \
                    ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(request) for _ in range(2)]
                results = [future.result(timeout=10) for future in futures]
            self.assertCountEqual(results, [200, "rolled_back"])
            after = self.state()
            self.assertEqual(len(after["financial_requests"]), len(before["financial_requests"]) + 1)
            self.assertEqual(len(after["balance_history"]), len(before["balance_history"]) + 1)

    def test_user_scoping_all_endpoints(self):
        for operation in self.operations:
            for user in ("one", "two"):
                with self.subTest(operation=operation, user=user):
                    url, body = self.arrange(operation, user)
                    result = self.post(url, body, key=operation, user=user)
                    self.assertEqual(result.status_code, 200, result.text)
                    self.assertEqual(self.post(url, body, key=operation, user=user).content, result.content)
        self.assertEqual(len(self.state()["financial_requests"]), 8)

    def test_original_responses_survive_changes_closure_and_restart(self):
        requests = []
        for operation in self.operations:
            url, body = self.arrange(operation)
            result = self.post(url, body, key=operation)
            self.assertEqual(result.status_code, 200)
            requests.append((operation, url, body, result.content))
            if operation == "open":
                position_id = result.json()["position"]["id"]
                self.assertEqual(self.post(f"/api/positions/{position_id}/close").status_code, 200)
        self.post("/api/wallet/deposit", {"amount": 77})
        restarted = self.new_client()
        before = self.state()
        with patch.object(trading, "fetch_latest_bar", side_effect=trading.MarketDataUnavailable("offline")):
            for key, url, body, expected in requests:
                result = self.post(url, body, key=key, client=restarted)
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.content, expected)
        self.assertEqual(self.state(), before)

    def test_canonical_effective_inputs(self):
        first = self.post("/api/wallet/deposit", {"amount": 20.001, "note": " x "}, key="money")
        replay = self.post("/api/wallet/deposit", {"amount": 20.004, "note": "x"}, key="money")
        self.assertEqual(first.content, replay.content)
        first = self.post("/api/positions", {"ticker": " aapl ", "side": "long", "amount": 20}, key="trade")
        replay = self.post("/api/positions", {"ticker": "AAPL", "side": "long", "amount": 20.0, "leverage": 1.0}, key="trade")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.content, replay.content)

    def test_missing_invalid_keys_and_authentication(self):
        for operation in self.operations:
            url, body = self.arrange(operation)
            before = self.state()
            for key in ("", "contains space", "\t", "x" * 129):
                self.assertEqual(self.post(url, body, key=key).status_code, 422)
                self.assertEqual(self.state(), before)
            self.assertEqual(self.post(url, body, key="auth", user="expired").status_code, 401)
            self.assertEqual(self.state(), before)
            self.assertEqual(self.post(url, body).status_code, 200)
        before = self.state()
        self.assertEqual(before["financial_requests"], [])
        for _ in range(2):
            self.assertEqual(self.post("/api/wallet/deposit", {"amount": 1}).status_code, 200)
        self.assertEqual(self.state()["wallets"][0]["balance"], before["wallets"][0]["balance"] + 2)

    def test_replay_requires_authentication_and_preserves_ownership(self):
        url, body = self.arrange("close")
        original = self.post(url, body, key="owner")
        self.assertEqual(original.status_code, 200)
        before = self.state()
        self.assertEqual(self.post(url, body, key="owner", user="expired").status_code, 401)
        self.assertEqual(self.post(url, body, key="owner", user="two").status_code, 404)
        self.assertEqual(self.state(), before)

    def test_insufficient_funds_does_not_consume_key(self):
        url, _ = self.arrange("withdraw")
        body = {"amount": 2000}
        before = self.state()
        self.assertEqual(self.post(url, body, key="funds").status_code, 409)
        self.assertEqual(self.state(), before)
        self.assertEqual(self.post("/api/wallet/deposit", {"amount": 2000}).status_code, 200)
        self.assertEqual(self.post(url, body, key="funds").status_code, 200)

    def test_quote_failures_leave_no_effects_or_record(self):
        for operation in ("open", "close"):
            url, body = self.arrange(operation)
            before = self.state()
            with patch.object(trading, "fetch_latest_bar", side_effect=trading.MarketDataUnavailable("offline")):
                self.assertEqual(self.post(url, body, key=operation).status_code, 502)
            self.assertEqual(self.state(), before)
            self.assertEqual(self.post(url, body, key=operation).status_code, 200)

    def test_winner_response_precedes_quote_failure(self):
        for operation in ("open", "close"):
            url, body = self.arrange(operation)
            fetching = threading.Event()
            release = threading.Event()

            def quote(ticker):
                if not fetching.is_set():
                    fetching.set()
                    self.assertTrue(release.wait(10))
                    raise trading.MarketDataUnavailable("loser quote failed")
                return self.bar(ticker)

            with patch.object(trading, "fetch_latest_bar", side_effect=quote), ThreadPoolExecutor(max_workers=1) as pool:
                loser = pool.submit(self.post, url, body, operation)
                try:
                    self.assertTrue(fetching.wait(5))
                    winner = self.post(url, body, key=operation)
                    self.assertEqual(winner.status_code, 200)
                    before = self.state()
                finally:
                    release.set()
                replay = loser.result(timeout=5)
            self.assertEqual(replay.status_code, 200)
            self.assertEqual(replay.content, winner.content)
            self.assertEqual(self.state(), before)

    def test_winner_response_precedes_missing_position_during_preparation(self):
        url, body = self.arrange("close")
        waiting = threading.Event()
        release = threading.Event()
        original = trading.owned_position_ticker

        def ticker(conn, *args):
            if not waiting.is_set():
                waiting.set()
                self.assertTrue(release.wait(10))
            return original(conn, *args)

        with patch.object(trading, "owned_position_ticker", side_effect=ticker), ThreadPoolExecutor(max_workers=1) as pool:
            loser = pool.submit(self.post, url, body, "close")
            try:
                self.assertTrue(waiting.wait(5))
                winner = self.post(url, body, key="close")
                self.assertEqual(winner.status_code, 200)
                before = self.state()
            finally:
                release.set()
            replay = loser.result(timeout=5)
        self.assertEqual(replay.content, winner.content)
        self.assertEqual(self.state(), before)

    def test_financial_and_record_failures_roll_back_all_endpoints(self):
        for operation in self.operations:
            for failure in ("financial", "record"):
                with self.subTest(operation=operation, failure=failure):
                    url, body = self.arrange(operation)
                    table, event = (("financial_requests", "INSERT") if failure == "record" else
                                    {"deposit": ("wallets", "UPDATE"), "withdraw": ("wallets", "UPDATE"),
                                     "open": ("positions", "INSERT"), "close": ("trades", "INSERT")}[operation])
                    with self.db() as conn:
                        conn.execute(f"CREATE TRIGGER fail_write AFTER {event} ON {table} "
                                     "BEGIN SELECT RAISE(ABORT, 'injected failure'); END")
                    before = self.state()
                    key = operation + failure
                    with self.assertRaises(sqlite3.IntegrityError):
                        self.post(url, body, key=key)
                    self.assertEqual(self.state(), before)
                    with self.db() as conn:
                        conn.execute("DROP TRIGGER fail_write")
                    self.assertEqual(self.post(url, body, key=key).status_code, 200)

    def test_commit_failure_rolls_back_all_endpoints(self):
        with self.db() as conn:
            conn.execute("CREATE TABLE deferred_failure (user_id INTEGER REFERENCES users(id) "
                         "DEFERRABLE INITIALLY DEFERRED)")
        for operation in self.operations:
            with self.subTest(operation=operation):
                url, body = self.arrange(operation)
                with self.db() as conn:
                    conn.execute("CREATE TRIGGER fail_commit AFTER INSERT ON financial_requests "
                                 "BEGIN INSERT INTO deferred_failure VALUES (999); END")
                before = self.state()
                with self.assertRaises(sqlite3.IntegrityError) as error:
                    self.post(url, body, key=operation)
                self.assertEqual(error.exception.sqlite_errorcode, sqlite3.SQLITE_CONSTRAINT_FOREIGNKEY)
                self.assertEqual(self.state(), before)
                with self.db() as conn:
                    self.assertEqual(conn.execute("SELECT COUNT(*) FROM deferred_failure").fetchone()[0], 0)
                    conn.execute("DROP TRIGGER fail_commit")
                self.assertEqual(self.post(url, body, key=operation).status_code, 200)

    def test_lock_exhaustion_returns_retryable_503(self):
        for operation in self.operations:
            url, body = self.arrange(operation)
            before = self.state()
            holder = dbcompat.connect(self.path)
            self.busy_timeout = 20
            try:
                holder.execute("BEGIN IMMEDIATE")
                response = self.post(url, body, key=operation)
                self.assertEqual(response.status_code, 503, response.text)
                self.assertEqual(response.headers["Retry-After"], "1")
            finally:
                holder.rollback()
                holder.close()
                self.busy_timeout = 5000
            self.assertEqual(self.state(), before)
            self.assertEqual(self.post(url, body, key=operation).status_code, 200)

    def test_initial_lookup_is_read_only_and_connections_close_before_quote(self):
        url, body = self.arrange("open")
        phases = []
        original = idempotency.lookup

        def lookup(conn, *args):
            phases.append(conn.in_transaction)
            return original(conn, *args)

        def quote(ticker):
            self.assertEqual(self.active_connections, set())
            return self.bar(ticker)

        with patch.object(idempotency, "lookup", side_effect=lookup), \
                patch.object(trading, "fetch_latest_bar", side_effect=quote):
            self.assertEqual(self.post(url, body, key="phases").status_code, 200)
        self.assertEqual(phases, [False, True])
        self.assertEqual(self.active_connections, set())

    def test_raw_sqlite_connections_close_before_prepare(self):
        connections = []

        def db():
            conn = dbcompat.connect(self.path)
            connections.append(conn)
            return conn

        def prepare(_user_id):
            self.assertEqual(len(connections), 1)
            with self.assertRaises(sqlite3.ProgrammingError):
                connections[0].execute("SELECT 1")

        def execute(conn, user_id, _prepared):
            result, _ = wallet.deposit(conn, user_id, 1)
            return {"wallet": wallet.wallet_payload(result)}

        result = idempotency.run(db, self.user, "one", "raw", "wallet.deposit", {"amount": 1}, execute, prepare)
        self.assertEqual(result.status_code, 200)
        for conn in connections:
            with self.assertRaises(sqlite3.ProgrammingError):
                conn.execute("SELECT 1")

    def test_keyed_slow_quotes_allow_other_users_deposits(self):
        for operation in ("open", "close"):
            url, body = self.arrange(operation)
            fetching = threading.Event()
            release = threading.Event()

            def quote(ticker):
                fetching.set()
                self.assertTrue(release.wait(10))
                return self.bar(ticker)

            with patch.object(trading, "fetch_latest_bar", side_effect=quote), ThreadPoolExecutor(max_workers=2) as pool:
                trade = pool.submit(self.post, url, body, operation)
                try:
                    self.assertTrue(fetching.wait(5))
                    deposit = pool.submit(self.post, "/api/wallet/deposit", {"amount": 1}, "deposit" + operation, "two")
                    self.assertEqual(deposit.result(timeout=3).status_code, 200)
                    self.assertFalse(trade.done())
                finally:
                    release.set()
                self.assertEqual(trade.result(timeout=5).status_code, 200)

    def test_keyed_closes_keep_own_quote_and_newer_cache(self):
        first_url, _ = self.arrange("close")
        second_url, _ = self.arrange("close")
        observed = threading.Event()
        release = threading.Event()
        original = idempotency.begin_financial_write

        def begin(conn):
            if not observed.is_set():
                self.assertFalse(conn.in_transaction)
                observed.set()
                self.assertTrue(release.wait(10))
            original(conn)

        def close_first():
            return self.post(first_url, key="old")

        old_bar = dict(self.bar("AAPL"), open=110, high=110, low=110, close=110)
        new_bar = dict(old_bar, open=120, high=120, low=120, close=120)
        with patch.object(trading, "fetch_latest_bar", side_effect=[old_bar, new_bar]), \
                patch.object(idempotency, "begin_financial_write", side_effect=begin), \
                ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(close_first)
            try:
                self.assertTrue(observed.wait(5))
                second = self.post(second_url, key="new")
                self.assertEqual(second.status_code, 200)
                cache = self.state()["prices"]
                self.assertEqual(cache[0]["close"], 120)
            finally:
                release.set()
            first = first.result(timeout=5)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["trade"]["exit_price"], 110)
        self.assertEqual(first.json()["trade"]["pnl"], 2)
        self.assertEqual(second.json()["trade"]["exit_price"], 120)
        self.assertEqual(second.json()["trade"]["pnl"], 4)
        self.assertEqual(self.state()["prices"], cache)
        self.assertEqual(self.state()["wallets"][0]["balance"], 1006)
        before = self.state()
        self.assertEqual(self.post(first_url, key="old").content, first.content)
        self.assertEqual(self.state(), before)


class IdempotencyWalTest(IdempotencyApiTest):
    journal_mode = "wal"
