import logging
import os
from datetime import datetime

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# Log file path with date
LOG_FILE = os.path.join(LOGS_DIR, f'bot_{datetime.now().strftime("%Y-%m-%d")}.log')


def setup_logger():
    """Setup and return logger"""
    logger = logging.getLogger('info_bot')
    logger.setLevel(logging.INFO)

    # File handler
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Create logger instance
logger = setup_logger()


def log_user_action(user_id: int, username: str, full_name: str, action: str, details: str = ""):
    """Log user actions"""
    username_str = f"@{username}" if username else "None"
    logger.info(f"[USER] ID: {user_id} | Username: {username_str} | Name: {full_name} | Action: {action} | {details}")


def log_message(user_id: int, direction: str, message_type: str, content: str = ""):
    """Log messages"""
    direction_symbol = "📥" if direction == "incoming" else "📤"
    content_preview = content[:100] + "..." if len(content) > 100 else content
    logger.info(f"{direction_symbol} [MESSAGE] User ID: {user_id} | Type: {message_type} | Content: {content_preview}")


def log_error(error: str, context: str = ""):
    """Log errors"""
    logger.error(f"[ERROR] {context} | {error}")


def log_bot_start():
    """Log bot startup"""
    logger.info("=" * 50)
    logger.info("🤖 Bot started successfully!")
    logger.info("=" * 50)
