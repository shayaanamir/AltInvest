"""
shared/app_env.py

Which kind of environment this process runs in, from APP_ENV.

    APP_ENV=dev (or development, local, test)  -> a developer machine or the test suite
    anything else, or unset                     -> production

Unset means production on purpose: a deployment that forgets the variable gets the strict
behaviour (no development JWT secret, no demo user, no reset links in the log), never the
lenient one.
"""
import os

_DEV_VALUES = {"dev", "development", "local", "test"}


def app_env() -> str:
    return (os.getenv("APP_ENV") or "production").strip().lower()


def is_dev() -> bool:
    return app_env() in _DEV_VALUES
