# Fases Bloqueadas - Aguardam Ação Humana

Estas fases foram identificadas na pesquisa de mercado v2.1 (2026-04-20) como necessárias, mas dependem de cadastro em serviços externos ou decisão de produto. Não entram na execução autônoma.

## 1. Kiwi Tequila Integration (fonte complementar)

**Dependência humana**: Cadastro no portal https://tequila.kiwi.com/portal e geração de API key.
**Motivação**: Pesquisa de mercado mostrou que SerpAPI (Google Flights) espelha o preço final de forma mais honesta que Kiwi (que tem markup no checkout). Kiwi entra como fonte complementar para cobrir low-cost que o Google indexa mal, não como primária.
**Escopo**: Criar KiwiClient em app/services/, integrar no polling_service com circuit breaker (se Kiwi 429, pausa 1h e segue com SerpAPI), remover fast-flights (scraping frágil).
**Quando desbloquear**: Após você cadastrar e me passar TEQUILA_API_KEY.

## 2. Observability with Sentry

**Dependência humana**: Conta Sentry (free tier 5k events/mês) + DSN.
**Motivação**: Pesquisa mostrou que sem observabilidade é impossível escalar para 200 usuários às cegas.
**Escopo**: sentry-sdk[fastapi] no requirements, init em main.py, logs estruturados JSON via python-json-logger, teste de erro forçado.
**Quando desbloquear**: Após você criar conta em sentry.io e me passar SENTRY_DSN.

## 3. WhatsApp Alerts (gap de mercado identificado)

**Dependência humana**: Escolha de provider (Twilio vs Z-API vs Meta Cloud API) + conta + número BR + custo validado.
**Motivação**: Pesquisa mostrou que nenhum concorrente BR entrega alerta por WhatsApp. É gap explícito.
**Escopo**: Campo `whatsapp_number` em users, opt-in no perfil, serviço WhatsApp paralelo ao alert_service, template idêntico ao email.
**Quando desbloquear**: Após decidir provider e me passar credenciais.

---

Cada uma vira uma phase própria quando você desbloquear. Não conte essas fases no progresso do v2.1.
