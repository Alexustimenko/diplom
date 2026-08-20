"""Backward-compatible import for the application factory."""

from app import create_app

__all__ = ["create_app"]
