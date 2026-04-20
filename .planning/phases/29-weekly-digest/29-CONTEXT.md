# Phase 29: Weekly Digest - Context

**Gathered:** 2026-04-20
**Status:** Implemented

<domain>
Email resumo semanal enviado as tercas 18:00 BRT (21:00 UTC) para cada usuario com grupos ativos. Mostra preco atual de cada grupo e delta percentual vs 7 dias atras.
</domain>

<decisions>
- Terca 18:00 BRT: proxima tarde de feriado eh raro + usuario ainda trabalha mas olha pessoal
- Um email por usuario, nao por grupo (consolida tudo)
- Comparativo: preco atual (ultimos 2 dias) vs preco 7-9 dias atras
- Direction 'down' se delta <= -3%, 'up' se >= 3%, 'stable' caso contrario
- Sem dados historicos suficientes = item mostra "sem comparativo", nao bloqueia envio
- Subject: "Flight Monitor: seu resumo semanal (N grupos ativos)"
</decisions>

<code_context>
### Arquivos novos
- app/services/weekly_digest_service.py (build_user_digest, compose_digest_email, run_weekly_digest)
- tests/test_weekly_digest.py (5 testes)

### Arquivos alterados
- app/scheduler.py: job weekly_digest adicionado
</code_context>

<specifics>
- Reusa send_email do alert_service
- CTA principal do email: botao azul "Abrir dashboard"
- HTML usa inline styles (compatibilidade de email)
</specifics>

<deferred>
- Destino em alta: curadoria manual ou algoritmo futuro
- Opt-out individual: aceitavel pois usuario pode desativar grupo
- Personalizacao por fuso horario: BRT hardcoded (publico e BR)
</deferred>
