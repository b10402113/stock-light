"""Rich logging configuration for ARQ workers."""

import logging
import sys

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme


# Custom theme for stock monitoring logs
custom_theme = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "red bold",
        "debug": "dim white",
        "success": "green",
        "stock": "blue",
        "job": "magenta",
        "time": "dim cyan",
    }
)

# Create console with custom theme
console = Console(theme=custom_theme, stderr=True)


def setup_worker_logging(level: str = "INFO") -> logging.Logger:
    """Setup rich logging for ARQ worker.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger for src.tasks.jobs module
    """
    # Create RichHandler with custom formatting
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_level=True,
        show_path=False,  # Hide file path for cleaner output
        markup=True,  # Enable rich markup in log messages
        rich_tracebacks=True,  # Beautiful traceback formatting
        tracebacks_show_locals=True,  # Show local variables in tracebacks
        tracebacks_width=100,
    )

    # Get the jobs module logger
    logger = logging.getLogger("src.tasks.jobs")
    logger.addHandler(rich_handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False  # Prevent duplicate logs from root logger

    return logger


def setup_all_task_logging(level: str = "INFO") -> None:
    """Setup rich logging for all task-related modules.

    This configures logging for:
    - src.tasks.jobs.* (all job modules)
    - src.stock_indicator.service
    - src.backtest.service
    - src.subscriptions.service

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_level=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
        tracebacks_width=100,
    )

    log_level = getattr(logging, level.upper(), logging.INFO)

    # Configure all task-related module loggers
    modules = [
        "src.tasks.jobs",
        "src.tasks.jobs.price_update_jobs",
        "src.tasks.jobs.sync_jobs",
        "src.tasks.jobs.indicator_jobs",
        "src.tasks.jobs.subscription_jobs",
        "src.tasks.jobs.reminder_jobs",
        "src.tasks.jobs.backtest_jobs",
        "src.stock_indicator.service",
        "src.backtest.service",
        "src.subscriptions.service",
    ]

    for module in modules:
        logger = logging.getLogger(module)
        logger.addHandler(rich_handler)
        logger.setLevel(log_level)
        logger.propagate = False


def get_console() -> Console:
    """Get the shared rich console instance.

    Returns:
        Console instance with custom theme
    """
    return console