"""Servico de controle de quota mensal SerpAPI.

Contador global compartilhado entre todos os usuarios.
Free tier: 250 buscas/mes.
"""
import datetime

from sqlalchemy.orm import Session

from app.models import ApiUsage

MONTHLY_QUOTA = 250


def get_current_year_month() -> str:
    """Retorna o ano-mes atual no formato YYYY-MM."""
    return datetime.datetime.utcnow().strftime("%Y-%m")


def get_monthly_usage(db: Session) -> int:
    """Retorna o total de buscas SerpAPI no mes atual."""
    ym = get_current_year_month()
    record = db.query(ApiUsage).filter(ApiUsage.year_month == ym).first()
    return record.search_count if record else 0


def increment_usage(db: Session, count: int = 1) -> int:
    """Incrementa o contador de buscas do mes atual.

    Cria o registro se nao existir. Retorna o novo total.
    """
    ym = get_current_year_month()
    record = db.query(ApiUsage).filter(ApiUsage.year_month == ym).first()
    if record is None:
        record = ApiUsage(year_month=ym, search_count=0)
        db.add(record)
    record.search_count += count
    db.commit()
    return record.search_count


def get_remaining_quota(db: Session) -> int:
    """Retorna quantas buscas ainda restam no mes atual."""
    used = get_monthly_usage(db)
    return max(0, MONTHLY_QUOTA - used)


def next_reset_date() -> datetime.date:
    """Retorna o primeiro dia do proximo mes (UTC).

    Usado para informar ao usuario quando a quota mensal sera renovada.
    """
    today = datetime.datetime.utcnow().date()
    if today.month == 12:
        return datetime.date(today.year + 1, 1, 1)
    return datetime.date(today.year, today.month + 1, 1)
