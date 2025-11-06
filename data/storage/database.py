"""Simple SQLite backed storage layer."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator

import pandas as pd


@dataclass(slots=True)
class Database:
    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            self._create_schema(conn)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.commit()
            conn.close()

    def _create_schema(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS options_instruments (
                symbol TEXT PRIMARY KEY,
                strike REAL,
                expiry DATE,
                type TEXT,
                base_coin TEXT
            );

            CREATE TABLE IF NOT EXISTS options_klines (
                timestamp TEXT,
                symbol TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                bid REAL,
                ask REAL,
                mark_iv REAL,
                PRIMARY KEY(timestamp, symbol)
            );

            CREATE TABLE IF NOT EXISTS futures_klines (
                timestamp TEXT,
                symbol TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                PRIMARY KEY(timestamp, symbol)
            );

            CREATE TABLE IF NOT EXISTS calculated_greeks (
                timestamp TEXT,
                symbol TEXT,
                delta REAL,
                gamma REAL,
                vega REAL,
                theta REAL,
                rho REAL,
                PRIMARY KEY(timestamp, symbol)
            );

            CREATE TABLE IF NOT EXISTS historical_volatility (
                timestamp TEXT,
                base_coin TEXT,
                period INTEGER,
                volatility REAL,
                PRIMARY KEY(timestamp, base_coin, period)
            );
            """
        )

    def insert_klines_batch(self, df: pd.DataFrame, table_name: str) -> None:
        if df.empty:
            return
        with self._connect() as conn:
            df.to_sql(table_name, conn, if_exists="append", index=False)

    def insert_options(self, instruments: pd.DataFrame) -> None:
        if instruments.empty:
            return
        with self._connect() as conn:
            instruments.rename(
                columns={"strike_price": "strike", "option_type": "type", "expiry_date": "expiry"},
                inplace=False,
            ).to_sql("options_instruments", conn, if_exists="append", index=False)

    def get_options_chain(self, timestamp: datetime, base_coin: str) -> pd.DataFrame:
        with self._connect() as conn:
            query = """
                SELECT k.*, i.strike, i.expiry, i.type, i.base_coin
                FROM options_klines k
                JOIN options_instruments i ON i.symbol = k.symbol
                WHERE i.base_coin = ? AND k.timestamp = ?
            """
            df = pd.read_sql_query(query, conn, params=(base_coin, timestamp.isoformat()))
        return df

    def get_option_data(self, symbol: str, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        with self._connect() as conn:
            query = """
                SELECT * FROM options_klines
                WHERE symbol = ? AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp
            """
            df = pd.read_sql_query(
                query,
                conn,
                params=(symbol, start_time.isoformat(), end_time.isoformat()),
                parse_dates=["timestamp"],
            )
        return df
