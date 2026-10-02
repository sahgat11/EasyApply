import json
import sqlite3
from pathlib import Path


DB_PATH = Path("data/easyapply.db")


def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():
    connection = get_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS email_classifications (
            message_id TEXT PRIMARY KEY,
            sender TEXT,
            subject TEXT,
            email_date TEXT,
            classification TEXT
        )
        """
    )

    connection.commit()
    connection.close()


def get_classification(message_id):
    connection = get_connection()

    row = connection.execute(
        """
        SELECT classification
        FROM email_classifications
        WHERE message_id = ?
        """,
        (message_id,)
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return json.loads(row["classification"])


def save_classification(email, classification):
    connection = get_connection()

    connection.execute(
        """
        INSERT OR REPLACE INTO email_classifications (
            message_id,
            sender,
            subject,
            email_date,
            classification
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            email["id"],
            email["from"],
            email["subject"],
            email["date"],
            json.dumps(classification)
        )
    )

    connection.commit()
    connection.close()