"""Shared slowapi Limiter instance.

Rate limiting emergencial (Phase 15.1): limite por IP em endpoints de login.
Phase 19 ampliara limites por endpoint e por usuario autenticado.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
