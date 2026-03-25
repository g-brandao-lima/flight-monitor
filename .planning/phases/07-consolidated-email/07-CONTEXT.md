# Phase 7: Consolidated Email - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Substituir o sistema atual de 1 email por sinal por 1 email consolidado por grupo. O email deve conter a rota mais barata, as melhores datas, resumo de todas as rotas, e usar formato de data brasileiro. So envia quando ha sinais detectados.

Requisitos: EMAIL-01, EMAIL-02, EMAIL-03.

</domain>

<decisions>
## Implementation Decisions

### Email consolidado (EMAIL-01)
- **D-01:** 1 email por grupo por ciclo de polling (nao 1 por sinal). So envia se pelo menos 1 sinal foi detectado no ciclo.
- **D-02:** Estrutura do email: (1) Rota mais barata em destaque no topo com preco, companhia, datas. (2) Tabela com top 3 melhores datas/precos. (3) Resumo das demais rotas monitoradas com preco atual. (4) Link de silenciar no rodape.
- **D-03:** Refatorar polling_service para acumular sinais por grupo antes de enviar, ao inves de enviar por sinal individual.

### Melhores datas (EMAIL-02)
- **D-04:** "Melhores datas" = as 3 combinacoes data+rota com menor preco dentro dos snapshots do ciclo atual, ordenadas por preco crescente.
- **D-05:** Cada entrada mostra: origem->destino, data ida (dd/mm), data volta (dd/mm), preco, companhia.

### Formato de data (EMAIL-03)
- **D-06:** Todas as datas no email usam formato dd/mm/aaaa (brasileiro). Usar strftime("%d/%m/%Y") nos templates.

### Claude's Discretion
- Layout HTML do email (cores, fontes, espacamento)
- Texto do assunto do email
- Tratamento quando grupo nao tem snapshots no ciclo

</decisions>

<canonical_refs>
## Canonical References

### Email atual (a ser refatorado)
- `app/services/alert_service.py` - compose_alert_email, send_email, should_alert (refatorar compose)
- `app/services/polling_service.py` - _process_flight (atualmente envia por sinal individual, refatorar para acumular)

### Models e dados
- `app/models.py` - FlightSnapshot (price, departure_date, return_date, airline), DetectedSignal
- `app/services/snapshot_service.py` - save_flight_snapshot

### Requirements
- `.planning/REQUIREMENTS.md` - EMAIL-01, EMAIL-02, EMAIL-03

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/alert_service.py`: compose_alert_email ja monta MIMEMultipart com HTML - adaptar para consolidado
- `app/services/alert_service.py`: send_email funciona - reusar sem mudanca
- `app/services/alert_service.py`: should_alert verifica silenciamento - reusar
- `app/services/dashboard_service.py`: format_price_brl ja formata precos em BRL - reusar no email

### Established Patterns
- Email via SMTP_SSL porta 465 com timeout=30
- HMAC token para link de silenciar
- Polling acumula snapshots por grupo em _poll_group

### Integration Points
- `app/services/polling_service.py`: _poll_group precisa acumular sinais e snapshots, enviar email consolidado ao final do grupo
- `app/services/alert_service.py`: compose_alert_email precisa nova versao que recebe lista de sinais + snapshots

</code_context>

<specifics>
## Specific Ideas

- Rota mais barata GRANDE no topo do email (preco em destaque)
- Tabela com melhores datas: simples, facil de ler no celular
- Link de silenciar mantido no rodape (mesmo HMAC pattern)
- Assunto: "Flight Monitor: [nome do grupo] - R$X.XXX (melhor preco)"

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 07-consolidated-email*
*Context gathered: 2026-03-25 (auto mode)*
