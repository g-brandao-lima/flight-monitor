# Fly.io Migration Guide

Passo a passo pra migrar o Orbita (ex-Flight Monitor) do Render pro Fly.io.

**Estimativa:** 15min. Custo: ~US$4/mes.

## Pre-requisitos

- Cartao de credito internacional (Fly.io cobra PAYG desde o primeiro byte, sem free tier)
- Acesso ao .env local com todos os secrets em producao (ou API key do Render pra copiar)

## Passo 1: instalar flyctl

**Windows (PowerShell):**
```powershell
iwr https://fly.io/install.ps1 -useb | iex
```

Adicionar `$HOME\.fly\bin` ao PATH se o instalador nao fizer sozinho.

**Confirmar:**
```bash
fly version
```

## Passo 2: autenticar

```bash
fly auth signup   # se primeira vez
# ou
fly auth login    # se ja tem conta
```

Abre o browser. Aprovar e voltar.

## Passo 3: criar o app (sem deploy)

Do diretorio do projeto (onde estao `fly.toml` e `Dockerfile`):

```bash
fly launch --no-deploy --copy-config
```

Quando perguntar:
- **App name:** `orbita-flights` (ja definido no fly.toml)
- **Region:** `gru` (Sao Paulo) — ja definido
- **Postgres:** **No** (vamos continuar usando Neon)
- **Redis:** No
- **Deploy now:** No

## Passo 4: configurar secrets

Copiar cada env var do Render (voce viu todas no /admin/stats ou via dashboard Render). Comando:

**Obter valores do Render via API ou Dashboard:**

```bash
# Opcao 1: listar via API (cuidado: saida contem secrets em claro)
curl -H "Authorization: Bearer $RENDER_API_KEY" \
  "https://api.render.com/v1/services/srv-d73mcitactks7381bsh0/env-vars"

# Opcao 2: Dashboard Render -> Environment -> copiar manualmente
```

**Depois rodar (substituir cada placeholder pelo valor real):**

```bash
fly secrets set \
  DATABASE_URL="<do_render>" \
  SERPAPI_API_KEY="<do_render>" \
  TRAVELPAYOUTS_TOKEN="<do_render>" \
  TRAVELPAYOUTS_MARKER="<do_render>" \
  GMAIL_SENDER="<do_render>" \
  GMAIL_RECIPIENT="<do_render>" \
  GMAIL_APP_PASSWORD="<do_render>" \
  GOOGLE_CLIENT_ID="<do_render>" \
  GOOGLE_CLIENT_SECRET="<do_render>" \
  SESSION_SECRET_KEY="<do_render>" \
  APP_BASE_URL="https://orbita-flights.fly.dev" \
  ADMIN_EMAIL="<do_render>" \
  SENTRY_DSN="<do_render>" \
  SENTRY_ENVIRONMENT="production" \
  SENTRY_TRACES_SAMPLE_RATE="0.1"
```

> Alternativa: salvar valores num arquivo `.secrets.tmp` (gitignored) e rodar `fly secrets import < .secrets.tmp`. Nunca commitar esse arquivo.

## Passo 5: configurar Google OAuth pro novo dominio

IMPORTANTE: antes do deploy, adicionar `https://orbita-flights.fly.dev/auth/callback` na lista de redirect URIs do Google OAuth:

1. https://console.cloud.google.com/apis/credentials
2. Editar o OAuth 2.0 Client ID
3. Authorized redirect URIs: adicionar `https://orbita-flights.fly.dev/auth/callback`
4. Salvar

(Deixe a URL antiga do Render na lista tambem — daremos soft cutover depois.)

## Passo 6: primeiro deploy

```bash
fly deploy
```

O build demora ~2-3min. Ao final, saida tipo:

```
Visit your newly deployed app at https://orbita-flights.fly.dev/
```

## Passo 7: validar

1. Abrir `https://orbita-flights.fly.dev/` — landing deve carregar
2. Login com Google — fluxo OAuth deve funcionar
3. Dashboard — grupos devem aparecer (mesmo banco Neon)
4. `/admin/stats` — cache Travelpayouts, quota SerpAPI
5. `/rotas/GRU-LIS` — pagina publica
6. `fly logs` — observar logs live pelos primeiros 5min

## Passo 8: observar performance

```bash
fly status
fly logs
fly dashboard   # abre browser com metricas
```

Verificar:
- CPU < 80% em idle
- RAM < 400MB
- Nenhum crash restart

## Passo 9: soft cutover (quando confiar)

Enquanto ambos rodam em paralelo (Render + Fly), o cron vai rodar 2x — uma em cada. NAO e critico mas gera emails duplicados em producao.

Para cutover:
1. No Render dashboard, desativar "Auto-Deploy"
2. Suspender o servico Render (`flight-monitor-ly3p`)
3. Atualizar qualquer bookmark/link apontando pro Render
4. Google Search Console: atualizar propriedade de `flight-monitor-ly3p.onrender.com` pra `orbita-flights.fly.dev`
5. Resubmit sitemap

## Passo 10: dominio custom (quando comprar)

Quando tiver um dominio (orbita.travel, orbitaflights.com.br, etc):

```bash
fly certs add orbita.travel
fly certs add www.orbita.travel
```

Seguir as instrucoes DNS que o flyctl imprime (A record + AAAA record).

Atualizar `APP_BASE_URL`:
```bash
fly secrets set APP_BASE_URL="https://orbita.travel"
```

## Rollback (se der ruim)

```bash
fly releases list
fly releases rollback <VERSION>
```

Ou, cenario de desastre: Render continua rodando em paralelo ate voce desligar. Reativar DNS pro Render se precisar.

## Custos estimados

- Maquina always-on 512MB shared-cpu-1x: US$3.89/mes
- Egress generoso dentro de 160GB/mes (incluido)
- SSL gratis
- **Total:** US$4/mes aproximado

Billing em `fly.io/dashboard/{org}/billing`.
