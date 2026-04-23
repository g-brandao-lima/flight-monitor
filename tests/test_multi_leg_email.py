"""Testes RED de render email multi (D-19, D-20).

Email consolidado multi mostra cadeia, total e breakdown por trecho.
"""
import pytest


def test_consolidated_multi_has_chain_and_total(
    db, multi_leg_group_factory, multi_leg_snapshot_factory
):
    """D-19: email multi contem cadeia ASCII, label total e subject no formato D-20."""
    try:
        from app.services import alert_service
    except ImportError:
        pytest.fail("alert_service nao disponivel")

    group = multi_leg_group_factory(num_legs=2, name="Eurotrip")
    snapshot = multi_leg_snapshot_factory(group, total_price=6000.0)

    # Tenta chamar compose_consolidated_email (ou equivalente) — se nao existir
    # branch multi, fica RED
    compose = getattr(alert_service, "compose_consolidated_email", None)
    if compose is None:
        pytest.fail(
            "alert_service.compose_consolidated_email nao implementado (Plan 04)"
        )

    result = compose(db, group, [snapshot], [])
    # result esperado: (subject, html, plain) ou dict
    if isinstance(result, tuple):
        subject, html, _ = result
    elif isinstance(result, dict):
        subject = result.get("subject", "")
        html = result.get("html", "")
    else:
        pytest.fail(f"formato de retorno inesperado: {type(result)}")

    assert "Orbita multi" in subject, f"subject fora do padrao D-20: {subject}"
    assert "Eurotrip" in subject
    assert "2 trechos" in subject or "(2 trechos)" in subject
    assert "GRU" in html and "FCO" in html
    assert "->" in html, "cadeia deve usar seta ASCII ->"
    assert "Preco total do roteiro" in html
