"""Configuracao centralizada do Jinja2Templates.

Expoe funcao `get_templates(dir)` que retorna instancia Jinja2Templates
com helpers globais registrados (is_admin, etc). Usado por todas as
rotas que renderizam HTML, garantindo consistencia.
"""
from fastapi.templating import Jinja2Templates

from app.auth.dependencies import is_admin


def get_templates(directory: str) -> Jinja2Templates:
    templates = Jinja2Templates(directory=directory)
    templates.env.globals["is_admin"] = is_admin
    return templates
