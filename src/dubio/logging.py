import logging

import structlog


def configure_logging(json_logs: bool = False, level: int = logging.INFO) -> None:
    renderer = (
        structlog.processors.JSONRenderer()
        if json_logs
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
    )


def get_logger(name: str):
    return structlog.get_logger(name)
