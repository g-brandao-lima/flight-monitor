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


def test_consolidated_multi_has_recommendation_before_legs(
    db, multi_leg_group_factory, multi_leg_snapshot_factory
):
    """D-19: bloco de recomendacao mandatorio no TOPO, antes da cadeia e da tabela de legs."""
    from app.services import alert_service

    group = multi_leg_group_factory(num_legs=3, name="Asia Multi")
    snapshot = multi_leg_snapshot_factory(group, total_price=4800.0)

    payload = alert_service.compose_consolidated_email(db, group, [snapshot], [])
    html = payload["html"] if isinstance(payload, dict) else payload[1]
    text = payload["text"] if isinstance(payload, dict) else payload[2]

    # HTML: bloco de recomendacao deve vir antes da cadeia e antes do primeiro "Trecho 1"
    rec_pos = html.find("recommendation-block")
    chain_pos = html.find("GRU -&gt;") if "GRU -&gt;" in html else html.find("GRU -&gt")
    if chain_pos == -1:
        chain_pos = html.find('class="chain"')
    first_leg_pos = html.find("Trecho 1")

    assert rec_pos >= 0, "bloco recommendation-block ausente no HTML"
    assert chain_pos > 0, "cadeia ausente no HTML"
    assert first_leg_pos > 0, "primeiro trecho ausente no HTML"
    assert rec_pos < chain_pos, f"recomendacao ({rec_pos}) deve vir antes da cadeia ({chain_pos})"
    assert rec_pos < first_leg_pos, f"recomendacao ({rec_pos}) deve vir antes da tabela de legs ({first_leg_pos})"

    # Plain text idem
    assert "Recomendacao:" in text
    rec_text_pos = text.find("Recomendacao:")
    trecho_text_pos = text.find("Trecho 1")
    preco_text_pos = text.find("Preco total do roteiro")
    assert rec_text_pos >= 0
    assert trecho_text_pos > rec_text_pos
    assert preco_text_pos > rec_text_pos
