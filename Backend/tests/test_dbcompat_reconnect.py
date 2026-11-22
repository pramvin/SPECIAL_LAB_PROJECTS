"""Run from Backend/:  .venv/bin/python -m unittest tests.test_dbcompat_reconnect -v"""
import unittest
from unittest import mock

from app import dbcompat

psycopg = dbcompat.psycopg


class Cursor:
    def __init__(self, raw):
        self.raw = raw

    def execute(self, sql, params=None):
        self.raw.calls += 1
        if self.raw.dead:
            raise psycopg.OperationalError("the connection is lost")
        self.raw.sql.append(sql)


class Raw:
    def __init__(self, dead=False):
        self.dead, self.calls, self.sql, self.closed = dead, 0, [], False

    def cursor(self):
        return Cursor(self)

    def close(self):
        self.closed = True

    def commit(self):
        if self.dead:
            raise psycopg.OperationalError("the connection is lost")

    def rollback(self):
        if self.dead:
            raise psycopg.OperationalError("the connection is lost")


@unittest.skipIf(psycopg is None, "psycopg not installed")
class ReconnectTest(unittest.TestCase):
    def test_a_dropped_connection_is_reopened_and_the_statement_retried(self):
        fresh = Raw()
        conn = dbcompat.PgConnection(Raw(dead=True), "postgresql://x")
        with mock.patch.object(psycopg, "connect", return_value=fresh) as connect:
            conn.execute("SELECT 1")
        connect.assert_called_once()
        self.assertEqual(fresh.sql, ["SELECT 1"])

    def test_without_a_url_the_error_is_raised(self):
        with self.assertRaises(psycopg.OperationalError):
            dbcompat.PgConnection(Raw(dead=True)).execute("SELECT 1")

    def test_rolling_back_a_dead_connection_does_not_raise_a_second_error(self):
        fresh = Raw()
        conn = dbcompat.PgConnection(Raw(dead=True), "postgresql://x")
        with mock.patch.object(psycopg, "connect", return_value=fresh):
            conn.__exit__(RuntimeError, RuntimeError("original"), None)  # must not raise


if __name__ == "__main__":
    unittest.main()
