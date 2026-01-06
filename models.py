import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def init_db():
    """Initialize database tables"""
    conn = get_db_connection()
    cur = conn.cursor()

    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            user_id BIGINT UNIQUE NOT NULL,
            username VARCHAR(255),
            full_name VARCHAR(255),
            language VARCHAR(10) DEFAULT 'en',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Messages table to store all messages
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            message_text TEXT,
            message_type VARCHAR(50) DEFAULT 'text',
            direction VARCHAR(10) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)

    # Message mappings table for owner replies
    cur.execute("""
        CREATE TABLE IF NOT EXISTS message_mappings (
            id SERIAL PRIMARY KEY,
            owner_message_id BIGINT UNIQUE NOT NULL,
            user_id BIGINT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


def save_user(user_id: int, username: str, full_name: str, language: str = None):
    """Save or update user"""
    conn = get_db_connection()
    cur = conn.cursor()

    if language:
        cur.execute("""
            INSERT INTO users (user_id, username, full_name, language, updated_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                full_name = EXCLUDED.full_name,
                language = EXCLUDED.language,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, username, full_name, language))
    else:
        cur.execute("""
            INSERT INTO users (user_id, username, full_name, updated_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                full_name = EXCLUDED.full_name,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, username, full_name))

    conn.commit()
    cur.close()
    conn.close()


def get_user_language(user_id: int) -> str:
    """Get user language preference from database"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT language FROM users WHERE user_id = %s", (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else "en"


def save_message(user_id: int, message_text: str, message_type: str, direction: str):
    """
    Save message to database
    direction: 'incoming' (from user) or 'outgoing' (to user)
    message_type: 'text', 'photo', 'video', 'audio', 'voice', 'document'
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO messages (user_id, message_text, message_type, direction)
        VALUES (%s, %s, %s, %s)
    """, (user_id, message_text, message_type, direction))
    conn.commit()
    cur.close()
    conn.close()


def get_user_messages(user_id: int, limit: int = 50):
    """Get message history for a user"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT message_text, message_type, direction, created_at
        FROM messages
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """, (user_id, limit))
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results


def get_all_users():
    """Get all users"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, username, full_name, language, created_at
        FROM users
        ORDER BY created_at DESC
    """)
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results


def get_all_user_ids():
    """Get all user IDs for broadcasting"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users")
    results = cur.fetchall()
    cur.close()
    conn.close()
    return [row[0] for row in results]


def save_message_mapping(owner_message_id: int, user_id: int):
    """Save mapping between owner's message_id and user_id for replies"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO message_mappings (owner_message_id, user_id)
        VALUES (%s, %s)
        ON CONFLICT (owner_message_id) DO NOTHING
    """, (owner_message_id, user_id))
    conn.commit()
    cur.close()
    conn.close()


def get_user_from_message(owner_message_id: int) -> int:
    """Get user_id from owner's message_id"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id FROM message_mappings
        WHERE owner_message_id = %s
    """, (owner_message_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else None
