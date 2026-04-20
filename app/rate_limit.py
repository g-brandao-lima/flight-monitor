"""Shared slowapi Limiter instance.

Phase 15.1: limite por IP em endpoints de login.
Phase 19: key_func hibrido (user_id quando autenticado, IP quando anonimo)
e limites diferenciados por tipo de endpoint (leitura, escrita, polling).
"""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_user_or_ip(request: Request) -> str:
    """Key func hibrido: usa user_id da sessao se autenticado, senao IP.

    Evita que um IP compartilhado (NAT, corporativo) bloqueie todos os
    usuarios daquele IP, e evita que um usuario malicioso contorne limite
    trocando de IP.
    """
    try:
        user_id = request.session.get("user_id")
        if user_id:
            return f"user:{user_id}"
    except (AssertionError, AttributeError):
        pass
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=get_user_or_ip)

LIMIT_LOGIN = "10/minute"
LIMIT_READ = "60/minute"
LIMIT_WRITE = "20/minute"
LIMIT_POLLING = "5/minute"
LIMIT_AUTOCOMPLETE = "30/minute"
