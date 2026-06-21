import pymysql
import logging
from contextlib import contextmanager
from config import DB_CONNECTIONS

logger = logging.getLogger(__name__)

class DatabasePool:
    def __init__(self):
        self._configs = {}
        for key, cfg in DB_CONNECTIONS.items():
            self._configs[key] = {
                "host": cfg["host"], "port": cfg["port"],
                "user": cfg["user"], "password": cfg["password"],
                "database": cfg["database"], "charset": cfg["charset"],
                "connect_timeout": 3,
                "cursorclass": pymysql.cursors.DictCursor, "autocommit": True,
            }

    def get_conn(self, alias):
        if alias not in self._configs:
            for k, c in self._configs.items():
                if c["database"] == alias: alias = k; break
            else: raise ValueError(f"Unknown: {alias}")
        return pymysql.connect(**self._configs[alias])

    def query(self, alias, sql, params=None):
        try:
            conn = self.get_conn(alias)
            try:
                cur = conn.cursor()
                cur.execute(sql, params)
                return cur.fetchall()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("DB query failed [%s]: %s", alias, str(e)[:150])
            raise

    def query_one(self, alias, sql, params=None):
        try:
            conn = self.get_conn(alias)
            try:
                cur = conn.cursor()
                cur.execute(sql, params)
                return cur.fetchone()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("DB query_one failed [%s]: %s", alias, str(e)[:150])
            raise

db = DatabasePool()
