import pymysql
import logging
from contextlib import contextmanager
from dbutils.pooled_db import PooledDB
from config import DB_CONNECTIONS

logger = logging.getLogger(__name__)


class DatabasePool:
    """带连接池的数据库访问层，基于 DBUtils.PooledDB。

    为每个数据库配置创建一个连接池，复用连接而非每次新建。
    """

    def __init__(self):
        self._pools = {}
        for key, cfg in DB_CONNECTIONS.items():
            self._pools[key] = PooledDB(
                creator=pymysql,
                mincached=2,          # 最小空闲连接数
                maxcached=8,          # 最大空闲连接数
                maxconnections=16,     # 并发上限
                blocking=True,         # 无空闲连接时阻塞等待
                host=cfg["host"],
                port=cfg["port"],
                user=cfg["user"],
                password=cfg["password"],
                database=cfg["database"],
                charset=cfg["charset"],
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True,
            )
        # database 名称 → key 的映射，允许用库名直接索引
        self._alias_map = {}
        for key, cfg in DB_CONNECTIONS.items():
            self._alias_map[cfg["database"]] = key

    def _resolve(self, alias: str) -> PooledDB:
        if alias in self._pools:
            return self._pools[alias]
        if alias in self._alias_map:
            return self._pools[self._alias_map[alias]]
        raise ValueError(f"Unknown database alias: {alias}")

    @contextmanager
    def connection(self, alias: str):
        """返回一个从连接池取出的连接，使用后归还到池中。"""
        pool = self._resolve(alias)
        conn = pool.connection()
        try:
            yield conn
        finally:
            conn.close()   # 归还到池，不真正关闭

    def query(self, alias: str, sql: str, params=None):
        try:
            with self.connection(alias) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    return cur.fetchall()
        except Exception as e:
            logger.warning("DB query error [%s]: %s", alias, str(e)[:200])
            raise

    def query_one(self, alias: str, sql: str, params=None):
        try:
            with self.connection(alias) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    return cur.fetchone()
        except Exception as e:
            logger.warning("DB query_one error [%s]: %s", alias, str(e)[:200])
            raise


db = DatabasePool()
