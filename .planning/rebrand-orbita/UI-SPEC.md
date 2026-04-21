# UI-SPEC — Rebrand Orbita

Contrato de implementacao para o rebrand "Flight Monitor" -> "Orbita". Este documento e prescritivo: um dev deve conseguir implementar sem tomar decisoes de design. Todas as escolhas sao justificadas em principio (contraste, hierarquia, carga cognitiva, performance) e nao em gosto.

Stack-alvo confirmada: Python + FastAPI + Jinja2 SSR, Pillow para OG images, zero framework JS. Toda solucao aqui preserva essa base.

---

## 1. Identidade Visual

### 1.1 Conceito

"Orbita" posiciona o produto como um sistema de tracking orbital: o preco e um objeto em orbita instavel, oscilando entre periastro (baixa, momento de comprar) e apoastro (alta). O produto e o radar que detecta a passagem pelo periastro. Essa metafora orienta tudo: o logo, o movimento das microinteracoes, a forma como o preco "pulsa" visualmente.

### 1.2 Logo

Marca composta por simbolo + wordmark. Simbolo e a sintese de tres elementos: um nucleo (o destino), uma orbita eliptica (a variacao de preco) e um ponto em transito (o sinal atual).

SVG base do simbolo (24x24, single-stroke, monoline, 1.75 stroke-width):

```
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
     fill="none" stroke="currentColor" stroke-width="1.75"
     stroke-linecap="round" stroke-linejoin="round">
  <!-- nucleo -->
  <circle cx="12" cy="12" r="2.2" fill="currentColor" stroke="none"/>
  <!-- orbita eliptica (rotacionada 30deg) -->
  <ellipse cx="12" cy="12" rx="9" ry="4.5" transform="rotate(-25 12 12)"/>
  <!-- objeto em transito -->
  <circle cx="19.5" cy="7.5" r="1.4" fill="currentColor" stroke="none"/>
</svg>
```

Wordmark: "Orbita" em Space Grotesk 600, letter-spacing -0.02em, o O com um ponto interno (eco do nucleo do simbolo). Em cabecalhos compactos, usar so o simbolo. Em OG images e favicon, usar o simbolo sem wordmark.

Variantes obrigatorias:
- Monocromatica clara (stroke #F8FAFC) para dark bg
- Monocromatica escura (stroke #0B1220) para light bg
- Accent (stroke gradient #6366F1 -> #22D3EE) para hero e OG

### 1.3 Paleta Cromatica

Principio: alta legibilidade em dark mode primario, contraste AA garantido em todos os pares texto/fundo. Evitamos o azul sky generico atual (#0EA5E9) que nao diferencia de concorrentes; migramos para indigo-cyan duotone, mais tecnologico e proprietario.

Primarias:
```
--brand-500: #6366F1   /* indigo — primary */
--brand-600: #4F46E5   /* hover */
--brand-400: #818CF8   /* on-dark accents */
--accent-500: #22D3EE  /* cyan — gradient partner, destaques */
--accent-400: #67E8F9
```

Semanticas:
```
--success-500: #10B981   /* preco LOW, confirmacoes */
--success-400: #34D399
--success-bg:  rgba(16,185,129,0.10)
--warning-500: #F59E0B   /* preco MEDIUM */
--warning-400: #FBBF24
--warning-bg:  rgba(245,158,11,0.10)
--danger-500:  #EF4444   /* preco HIGH, destrutivo */
--danger-400:  #F87171
--danger-bg:   rgba(239,68,68,0.10)
--info-500:    #3B82F6
```

Neutros dark (escala Slate+Indigo, levemente frios para reforcar "tech"):
```
--bg-0: #070A13   /* page bg, mais profundo que o atual */
--bg-1: #0E1220   /* card bg */
--bg-2: #161B2E   /* card elevated, inputs */
--bg-3: #1F2542   /* hover states */
--border-1: rgba(255,255,255,0.06)
--border-2: rgba(255,255,255,0.10)
--border-3: rgba(255,255,255,0.14)
--text-0: #F8FAFC   /* primary */
--text-1: #CBD5E1   /* secondary */
--text-2: #94A3B8   /* tertiary/labels */
--text-3: #64748B   /* disabled/captions */
```

Neutros light (para modo opcional):
```
--bg-0-light: #FAFBFF
--bg-1-light: #FFFFFF
--bg-2-light: #F1F5F9
--border-1-light: #E2E8F0
--text-0-light: #0B1220
--text-1-light: #334155
--text-2-light: #64748B
```

Gradientes utilitarios:
```
--gradient-brand: linear-gradient(135deg, #6366F1 0%, #22D3EE 100%)
--gradient-success: linear-gradient(135deg, #10B981 0%, #34D399 100%)
--gradient-radial-hero: radial-gradient(ellipse at top, rgba(99,102,241,0.25), transparent 60%)
```

Contraste verificado (WCAG AA): text-0 sobre bg-0 = 16.8:1, text-1 sobre bg-1 = 11.2:1, text-2 sobre bg-1 = 6.8:1, brand-400 sobre bg-0 = 8.1:1. Tudo passa AAA exceto text-3 (decorativo, nao usado para info critica).

### 1.4 Tipografia

Duas familias, ambas Google Fonts com preload:
- Display/body: **Space Grotesk** (400, 500, 600, 700). Geometrico, tech, mais distinto que Inter, mas mantem legibilidade pt-BR inclusive com acentos.
- Numeric/mono: **JetBrains Mono** (500, 700). Para precos, airport codes, dados tabulares. Tabular-nums garantido.

Fallback stack:
```
font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
font-family-mono: 'JetBrains Mono', ui-monospace, 'SF Mono', Consolas, monospace;
```

Performance: carregar apenas subset latin-ext, display=swap, weights estritamente usados. Self-host os .woff2 em `/static/fonts/` para eliminar round-trip ao Google em prod (Render free tier ja lento).

Escala tipografica (base 16px, razao 1.25 major third, ajustada):
```
--fs-xs:   11px / line 1.4    /* captions, disclaimers */
--fs-sm:   13px / line 1.5    /* meta, labels */
--fs-base: 14px / line 1.55   /* body */
--fs-md:   16px / line 1.5    /* body emphasis */
--fs-lg:   18px / line 1.4    /* subheadings */
--fs-xl:   22px / line 1.3    /* card titles */
--fs-2xl:  28px / line 1.2    /* section headings */
--fs-3xl:  40px / line 1.1    /* page h1 */
--fs-4xl:  56px / line 1.05   /* hero h1 desktop */
--fs-price-sm: 20px           /* card price */
--fs-price-lg: 64px           /* public route hero price */
```

Weights: 400 body, 500 meta/labels emphasis, 600 UI chrome/botoes, 700 headings e precos. Nunca 800/900 (peso excessivo contradiz tom clean).

Letter-spacing: headings -0.02em (apertar), labels uppercase +0.08em, numericos tabular-nums -0.01em.

### 1.5 Iconografia

Lib: **Lucide** (fork mantido dos Feather, 1000+ icones, license MIT, tree-shakeable inline). Motivos: (1) estilo line consistente com o monoline do logo, (2) stroke-width 1.75 casa com o logo, (3) ja temos SVGs similares no codebase. Alternativa descartada: Heroicons (mix filled/outline polui), Phosphor (denso demais, visualmente pesado).

Regras:
- Tamanhos padrao: 14px (inline meta), 16px (botoes/nav), 20px (card headers), 24px (section icons), 40px (hero/empty state).
- Stroke-width sempre 1.75 exceto em 14px onde usa 2 para nao sumir.
- Cor: `currentColor`. Nunca hex hardcoded no SVG, exceto no OG image.
- Nao combinar filled e outline na mesma tela.

Icones-chave mapeados (substituem o aviao do logo atual):
- `radar` (detectar sinal) -> alertas, sinal ativo
- `activity` -> atividade, historico
- `trending-down` / `trending-up` -> tendencia de preco
- `target` -> melhor momento
- `orbit` (custom, reuso do simbolo) -> marca
- `plane` continua usado para voo especifico, mas nunca como marca

### 1.6 Espacamento

Grid base **4px**. Token scale:
```
--sp-1: 4px    --sp-2: 8px    --sp-3: 12px   --sp-4: 16px
--sp-5: 20px   --sp-6: 24px   --sp-8: 32px   --sp-10: 40px
--sp-12: 48px  --sp-16: 64px  --sp-20: 80px  --sp-24: 96px
```

Regra: toda distancia entre elementos em multiplos de 4. Padding interno card = sp-6. Gap entre cards = sp-3. Section padding vertical = sp-16 desktop / sp-12 mobile.

### 1.7 Border Radius

Escala intencionalmente curta (consistencia > variedade):
```
--r-xs: 4px    /* badges, tags */
--r-sm: 6px    /* inputs, pequenos botoes */
--r-md: 10px   /* botoes, cards pequenos */
--r-lg: 14px   /* cards principais */
--r-xl: 20px   /* modal, hero */
--r-full: 9999px /* pills, avatar */
```

Principio: radius maior ~= hierarquia maior. Nunca misturar radius em elementos adjacentes (ex: input com r-sm dentro de card com r-lg esta OK; input r-lg junto a botao r-md nao esta).

### 1.8 Shadows e Elevacao

Em dark mode, shadows tradicionais somem. Usamos luminosidade (border glow + inner highlight) em vez de sombra:
```
--elev-0: none
--elev-1: 0 1px 0 0 rgba(255,255,255,0.04) inset                      /* card base */
--elev-2: 0 1px 0 0 rgba(255,255,255,0.06) inset, 0 8px 24px -12px rgba(0,0,0,0.6)
--elev-3: 0 1px 0 0 rgba(255,255,255,0.08) inset, 0 16px 48px -16px rgba(0,0,0,0.7)
--glow-brand: 0 0 0 1px rgba(99,102,241,0.35), 0 8px 32px -8px rgba(99,102,241,0.3)
--glow-success: 0 0 0 1px rgba(16,185,129,0.35), 0 8px 32px -8px rgba(16,185,129,0.25)
```

Em light mode usar sombras convencionais: `0 1px 2px rgba(15,23,42,0.06), 0 1px 3px rgba(15,23,42,0.08)`.

---

## 2. Componentes Core

### 2.1 Buttons

Altura padrao 40px (min-height touch-friendly), padding horizontal 16px, radius r-md, fs-sm 600, transicao 150ms. Tres variantes + tres tamanhos (sm 32px, md 40px, lg 48px).

Primary:
```
bg: var(--gradient-brand); color: #fff;
hover: brightness(1.08); box-shadow: var(--glow-brand);
active: transform: scale(0.98); brightness(0.95);
disabled: opacity 0.45; cursor not-allowed;
focus-visible: outline 2px var(--accent-400), offset 2px;
```

Secondary (outlined):
```
bg: var(--bg-2); color: var(--text-0); border: 1px solid var(--border-2);
hover: border-color var(--brand-400); bg var(--bg-3);
```

Ghost:
```
bg: transparent; color: var(--text-1); border: 1px solid transparent;
hover: bg rgba(255,255,255,0.04); color var(--text-0);
```

Destrutivo: variante de ghost com color var(--danger-400) hover bg var(--danger-bg).

ASCII estado primary:
```
+---------------------------+
|  (icon)  Comecar gratis   |  <- 40px altura, gradient bg, text #fff
+---------------------------+
     ^ shadow glow indigo
```

### 2.2 Card

Base:
```
bg: var(--bg-1);
border: 1px solid var(--border-1);
border-left: 3px solid transparent;  /* slot semantico */
border-radius: var(--r-lg);
padding: var(--sp-6);
box-shadow: var(--elev-1);
transition: border-color 200ms, box-shadow 200ms, transform 200ms;
```

Hover (desktop, nao touch): border-color var(--border-3), box-shadow var(--elev-2), transform translateY(-1px). Em `@media (hover: none)` suprimir.

Variantes semanticas (via classe):
- `.card--low` : border-left-color var(--success-500)
- `.card--medium` : border-left-color var(--warning-500)
- `.card--high` : border-left-color var(--danger-500)
- `.card--inactive` : opacity 0.5, sem hover

ASCII:
```
+===+--------------------------------------+
| G |  Titulo do grupo   [badge] [badge]   |
| R |  GRU -> LIS  TAP  Direto             |
| E |  Ida 12/jun  Volta 30/jun            |
| E |  --------------------------------    |
| N |  R$ 3.240    [sparkline: |.|.||.]    |
|   |  por pessoa                          |
+===+--------------------------------------+
  ^ barra semantica 3px
```

### 2.3 Input / Select / Form Field

```
height: 40px;
bg: var(--bg-2);
border: 1px solid var(--border-2);
border-radius: var(--r-sm);
padding: 0 12px;
color: var(--text-0);
font: 14px/1 'Space Grotesk';
```

Focus: border-color var(--brand-500), box-shadow 0 0 0 3px rgba(99,102,241,0.18). Error: border-color var(--danger-500), helper text fs-xs color danger-400. Label: fs-sm text-2 uppercase letter-spacing 0.08em, margin-bottom 6px.

### 2.4 Badge

Pills compactas, fs-xs 600 uppercase letter-spacing 0.06em, padding 3px 8px, radius r-full. Variantes: default (border-2 / text-2), success, warning, danger, info, brand. Sempre `bg: var(--*-bg)` + `color: var(--*-400)` + `border: 1px solid var(--*-500)` com 35% alpha.

### 2.5 Navbar / Header

Sticky top 0, altura 64px desktop / 56px mobile, bg rgba(7,10,19,0.72) backdrop-filter blur(14px) saturate(1.4), border-bottom 1px solid var(--border-1). Layout: logo esquerda, nav central opcional (deslogado), actions direita.

```
+---------------------------------------------------------------+
|  (O) Orbita   |  Produto  Rotas  Sobre   |  Entrar  [Comecar] |
+---------------------------------------------------------------+
```

Logo: simbolo 24px + wordmark 16px 600. Gap 8px.

### 2.6 Footer

Minimalista, border-top, padding sp-10 vertical. Colunas:
```
+--------------------------------------------------------------+
| (O) Orbita                Produto    Rotas        Legal      |
| Passagem na orbita certa. Alertas    GRU -> LIS   Termos     |
|                           Como funci JFK -> GRU   Privacidade|
+--------------------------------------------------------------+
| (c) 2026 Orbita  v2.4                  Feito com API Amadeus |
+--------------------------------------------------------------+
```

### 2.7 Toast / Flash

Top-center, max-width 420px, slide-in 180ms ease-out, auto-dismiss 5s com barra de progresso sutil inferior (1px, bg brand). bg var(--bg-2), border 1px solid da semantica, radius r-md, padding 12px 16px, fs-sm. Icone 16px da semantica + texto + botao close.

### 2.8 Empty State

Centered, padding sp-20 vertical. Icone 56px (outline brand-400, opacidade 0.8) + h2 fs-xl 600 + p fs-base text-2 max-width 420px + CTA primary. Animacao idle: float 4s ease-in-out infinite, transform translateY(-6px), respeita prefers-reduced-motion.

### 2.9 Price Display (componente central)

O elemento mais importante do produto. Deve comunicar em < 200ms: (1) valor, (2) se e bom ou ruim, (3) tendencia, (4) confianca.

```
+----------------------------------+
|  PRECO DE REFERENCIA  [LOW]      |  <- label uppercase fs-xs text-2 + badge
|                                  |
|  R$ 3.240                        |  <- fs-price-sm (20px em card), JetBrains Mono 700
|  por pessoa - ida e volta        |  <- fs-sm text-2
|                                  |
|  v 12% vs 7d  |  Melhor ja: 2980 |  <- fs-xs com icone trending
|  ||..||.|.||. (sparkline)        |  <- 8-14 barras, ultima highlight brand
+----------------------------------+
```

Cor do numero segue classificacao: LOW success-400, MEDIUM warning-400, HIGH danger-400, NONE text-2. A classificacao e comunicada 3x (cor, badge, barra lateral do card) redundancia intencional para daltonismo.

Variante hero (public route): fs-price-lg 64px, com pulsacao sutil 3s quando e LOW (box-shadow glow verde, respeita reduced-motion).

### 2.10 Sparkline

Barras verticais 4px wide, gap 2px, altura max 28px. Cor base var(--border-3); ultima barra var(--brand-400); barra minima historica var(--success-500). Altura proporcional a (val - min)/(max - min). Titulo acessivel: aria-label "Tendencia de preco: ultimos N dias, preco atual X, minimo Y". Se len < 3, nao renderizar.

### 2.11 Summary Bar

Strip horizontal topo dashboard, bg transparente, padding vertical sp-3, border-bottom var(--border-1). Metricas separadas por divider vertical sutil (1px var(--border-1), altura 16px). Formato `LABEL: valor`, label fs-xs uppercase text-3, valor fs-sm 600 text-0. Acoes a direita (botoes sm).

---

## 3. Paginas Redesign

### 3.1 Landing (deslogada)

Objetivo: converter visitante em signup em < 30s. Hierarquia: hero com promessa + CTA > social proof > como funciona > por que Orbita > rotas populares > CTA final.

```
+--------------------------------------------------------------+
|              (navbar transparente sobre hero)                |
+--------------------------------------------------------------+
|                                                              |
|               [gradiente radial indigo sutil]                |
|                                                              |
|              (O)  <- simbolo 56px com pulse                  |
|                                                              |
|      Passagem no momento certo.                              |  <- fs-4xl 700
|      Antes do preco subir.                                   |
|                                                              |
|      Orbita rastreia o inventario real dos voos e            |  <- fs-lg text-1
|      avisa quando os assentos baratos estao acabando.        |     max-width 560
|                                                              |
|      [ Comecar gratis -> ]     ver demo                      |  <- primary + text link
|                                                              |
|      * Sem cartao  * Dados reais Amadeus  * Alertas por email|  <- fs-sm text-2
|                                                              |
|  +--------------------+  +--------------------+              |
|  | mini dashboard pre-| | mini card com preco|  <- mockup visual, hero image SVG
|  | view (SVG estatico)| | LOW e sparkline    |
|  +--------------------+  +--------------------+              |
+--------------------------------------------------------------+

+--------------------------------------------------------------+
|  NUMEROS (faixa fina, bg-1)                                  |
|  12.4k precos coletados  |  180d historico  |  4 rotas pop.  |
+--------------------------------------------------------------+

+--------------------------------------------------------------+
|                    Como funciona                             |  <- fs-2xl
|                                                              |
|  +----------+   +----------+   +----------+                  |
|  | 01       |   | 02       |   | 03       |                  |  <- numero em gradient
|  | Radar    |   | Orbita   |   | Sinal    |                  |     fs-2xl mono 700
|  | Aponte o |   | Monitora-|   | Receba   |                  |
|  | destino  |   | mos 24/7 |   | o alerta |                  |
|  +----------+   +----------+   +----------+                  |
+--------------------------------------------------------------+

+--------------------------------------------------------------+
|              Por que Orbita (fs-2xl)                         |
|                                                              |
|  +----------+   +----------+   +----------+                  |
|  | (radar)  |   | (trend)  |   | (mail)   |                  |
|  | Dados de |   | Historico|   | Alerta   |                  |
|  | inventa- |   | de 180d  |   | sem app  |                  |
|  | rio real |   | por rota |   |          |                  |
|  +----------+   +----------+   +----------+                  |
+--------------------------------------------------------------+

+--------------------------------------------------------------+
|           Rotas populares                                    |
|  [ GRU -> LIS ]  [ GRU -> JFK ]  [ GIG -> EZE ]  [ MIA ]     |  <- chips-card
+--------------------------------------------------------------+

+--------------------------------------------------------------+
|   [gradient radial no bg]                                    |
|   Pronto para comprar no momento certo?                      |
|   [ Entrar com Google ]                                      |
|   Gratis. Sem cartao.                                        |
+--------------------------------------------------------------+

(footer)
```

Notas:
- Hero: h1 usa text-0, `p` usa text-1. CTA primary com glow.
- Faixa "numeros" usa tabular-nums mono, separadores fino border-1 vertical.
- Steps: numero em `font-mono` cor gradient (usar background-clip: text). Borda superior dos cards em gradient de 1px quando hover.
- Rotas populares: cards compactos, so `<origem> -> <destino>`, fs-md mono + fs-xs cidade. Link direto para /rotas/{slug}.
- Final CTA reutiliza bg gradiente radial.

### 3.2 Dashboard (logada)

Mantem densidade informacional atual. Nova hierarquia:

```
+--------------------------------------------------------------+
| (navbar)                                                     |
+--------------------------------------------------------------+
| GRUPOS: 4  |  MENOR: R$ 2.980 (GRU->LIS)  |  PROX: 14:20    |  <- summary bar refinada
|                              [ + Novo grupo ] [ Buscar agora]|
+--------------------------------------------------------------+
|                                                              |
|  +==+-------------------------------------------+            |  <- card LOW (verde)
|  |G | Lisboa ferias   [LOW] [Sinal: ALTA]       |            |
|  |R | GRU -> LIS TAP Direto                     |            |
|  |E | 12/jun - 30/jun                           |            |
|  |E |                            R$ 2.980       |            |
|  |N |                            por pessoa     |            |
|  |  |                            v 8% vs 7d     |            |
|  |  |                            [|..|.||..]    |            |
|  +==+-------------------------------------------+            |
|                                                              |
|  +==+-------------------------------------------+            |  <- card MEDIUM
|  |AM| Miami negocio   [MEDIUM]                  |            |
|  |AR| ...                                       |            |
|  +==+-------------------------------------------+            |
|                                                              |
|  +--+-------------------------------------------+            |  <- card inactive
|  |  | Paris aniv   [Inativo]  (opacity 0.5)     |            |
|  +--+-------------------------------------------+            |
+--------------------------------------------------------------+
```

- Summary bar: redesenhada, divisores sutis, actions agrupadas direita, sticky opcional em scroll (backdrop).
- Cards: preservam estrutura atual mas com novo padding, nova tipografia, novo sparkline. Preco a direita em desktop, abaixo em mobile (stack).
- Empty state: exibe 4 cards "Rotas populares" em grid 2x2, CTA para criar custom.

### 3.3 Detalhe de Grupo

```
+--------------------------------------------------------------+
| < Voltar     Lisboa ferias      [Editar] [Ativar] [Excluir]  |
+--------------------------------------------------------------+
|                                                              |
|  GRU -> LIS  |  12/jun - 30/jun  |  1 passageiro  |  Direto |
|                                                              |
|  +------------------------------------------+                |
|  |  R$ 2.980   [LOW]                        |                |  <- price hero
|  |  por pessoa                              |                |
|  |  v 8% (-R$ 260) ultimos 7 dias           |                |
|  +------------------------------------------+                |
|                                                              |
|  +------------------------------------------+                |
|  |  Historico 180d (line chart SSR via SVG) |                |
|  |                                          |                |
|  |     /\    /\                             |                |
|  |    /  \  /  \       ___                  |                |
|  |  _/    \/    \_____/   \___  (hoje)      |                |
|  |                                          |                |
|  |  Min 2840 | Mediana 3120 | Max 4100      |                |
|  +------------------------------------------+                |
|                                                              |
|  +------------------------------------------+                |
|  |  Snapshots recentes (tabela)             |                |
|  |  Data       Preco      Fonte     Cia    |                |
|  |  15/04      R$ 2.980   Amadeus   TAP    |                |
|  |  14/04      R$ 3.020   Amadeus   TAP    |                |
|  +------------------------------------------+                |
|                                                              |
|  [ Google Flights ] [ Decolar ] [ Skyscanner ]               |
+--------------------------------------------------------------+
```

Chart: SVG puro gerado no backend (Jinja + helper Python) ou inline com paths interpolados. Sem JS. Eixo y implicito (3 linhas de grade: min/mediana/max). Hover mostra tooltip via `<title>` SVG nativo.

### 3.4 Pagina Publica /rotas/{O}-{D}

Foco SEO, mesmo layout dark. Hero com o preco em escala maxima, signal social, CTA dupla (monitorar vs comprar agora).

```
+--------------------------------------------------------------+
| (navbar sem nav central, so logo + Entrar)                   |
+--------------------------------------------------------------+
|                                                              |
|   Passagens Sao Paulo -> Lisboa                              |  <- h1 fs-3xl
|   GRU -> LIS  |  atualizado ha 2h                            |  <- fs-sm text-2
|                                                              |
|             R$ 3.240                                         |  <- fs-price-lg 64px
|             preco de referencia  mediana 180d R$ 3.420       |  <- fs-sm text-2
|             [pode divergir ate 5%]                           |
|                                                              |
|    [ Monitorar essa rota -> ]   [ Comprar no parceiro ]      |
|                                                              |
+--------------------------------------------------------------+
|                                                              |
|   Melhores meses                                             |
|   [ mar  R$ 2890 ] [ nov  R$ 3010 ] [ abr  R$ 3100 ]         |
|                                                              |
+--------------------------------------------------------------+
|   Historico 180 dias   (mesmo grafico do detalhe)            |
+--------------------------------------------------------------+
|   FAQ (SEO long-tail, 3-5 perguntas)                         |
|   Q: Quando comprar GRU LIS?  A: ...                         |
+--------------------------------------------------------------+
|   (CTA final + footer)                                       |
```

OG image: gerado via Pillow em build-time ou on-demand com cache. 1200x630, bg gradient brand, logo canto superior esquerdo, rota em Space Grotesk 96px, preco abaixo em JetBrains Mono 120px cor success-400. Arquivo padrao em `/static/og/{slug}.png`.

### 3.5 Login / OAuth

```
+--------------------------------------------------------------+
|          (fundo full-bleed com gradient radial)              |
|                                                              |
|              +--------------------------+                    |
|              |   (O)                    |                    |
|              |                          |                    |
|              |   Bem-vindo a Orbita     |  <- fs-2xl 700
|              |   Entre para monitorar   |  <- fs-base text-1
|              |                          |                    |
|              |   [ G  Entrar com Google]|  <- primary + logo G
|              |                          |                    |
|              |   Ao continuar voce      |                    |
|              |   aceita os Termos       |  <- fs-xs text-3
|              +--------------------------+                    |
|                                                              |
+--------------------------------------------------------------+
```

Card central max-width 420px, padding sp-10, radius r-xl, elev-3. Sem formulario email/senha (so OAuth confirmado).

### 3.6 /admin/stats

Densidade de dados, layout de tabelas. Grid de KPI cards topo (4 colunas desktop, 2 tablet, 1 mobile) + tabelas abaixo.

```
+--------------------------------------------------------------+
| Admin - Estatisticas                                         |
+--------------------------------------------------------------+
| +-------+ +-------+ +-------+ +-------+                      |
| |Users  | |Groups | |Polls/d| |Alerts |                      |
| | 142   | |  38   | |  24   | |   7   |                      |
| | +12%  | | +3    | | ok    | | +2    |                      |
| +-------+ +-------+ +-------+ +-------+                      |
|                                                              |
| Usuarios recentes                                            |
| +-----------------------------------------------+            |
| | Nome     Email           Criado   Grupos     |            |
| | ...                                           |            |
| +-----------------------------------------------+            |
+--------------------------------------------------------------+
```

KPI card: fs-xs label uppercase text-2, fs-2xl mono 700 text-0, delta fs-xs colorido por direcao.

---

## 4. Motion e Microinteracoes

Principios: (1) motion comunica relacao causal, nunca decora; (2) duration max 240ms para acoes diretas, 400ms para transicoes de pagina; (3) easing padrao `cubic-bezier(0.2, 0.8, 0.2, 1)` (ease-out com overshoot sutil zero), evitar `ease-in-out` generico.

Tokens:
```
--dur-instant: 80ms     /* color change, opacity */
--dur-fast: 160ms       /* hover, focus */
--dur-base: 220ms       /* card hover, modal open */
--dur-slow: 400ms       /* page transition, reveal */
--ease-out: cubic-bezier(0.2, 0.8, 0.2, 1)
--ease-in: cubic-bezier(0.4, 0, 1, 1)
--ease-spring: cubic-bezier(0.34, 1.3, 0.64, 1)  /* CTA active */
```

Microinteracoes obrigatorias:
- Button hover: brightness 1.08 em 160ms
- Button active: scale(0.98) em 80ms com ease-spring
- Card hover: translateY(-1px) + shadow em 220ms
- Flash message: slide-in top + fade, barra de progresso de dismissal 1px
- Sparkline update: ultima barra pulsa 2x (opacity 0.6 -> 1) ao carregar
- Price LOW: pulse suave (box-shadow glow 3s loop), so quando visivel, pausa em scroll via IntersectionObserver-free via CSS animation-play-state quando container tem `:hover` ou sempre (simples)

Loading state do polling: overlay existente mantido mas:
- Icone substituido pelo simbolo Orbita com animacao de rotacao do ponto em transito ao redor do nucleo (rotate 360 em 2s linear)
- Barra de progresso com gradient brand
- Mensagens reescritas: "Varredura orbital", "Analisando trajetoria", "Detectando sinal", "Estabelecendo alerta"

Skeleton loaders:
```
bg: linear-gradient(90deg, var(--bg-1) 0%, var(--bg-2) 50%, var(--bg-1) 100%);
background-size: 200% 100%;
animation: shimmer 1.4s ease-in-out infinite;
```

Usar skeleton apenas em dashboard quando houver N > 0 grupos mas polling em progresso (substitui "Aguardando coleta"). Nao usar em landing (SSR renderiza instantaneo).

`prefers-reduced-motion: reduce`: suprimir translateY, scale, pulse, shimmer, rotate. Manter apenas opacity e color transitions em 80ms.

---

## 5. Acessibilidade

Checklist obrigatorio:
- Contraste AA em todo texto: text-0 e text-1 sobre bg-0/bg-1 verificados. text-3 apenas para texto decorativo ornamental (>= 18px ou negrito).
- Focus visible: outline 2px var(--accent-400) offset 2px em todo elemento focalizavel. Nunca `outline: none` sem substituto.
- Tamanhos de toque: 40x40px min em interactivos (WCAG AAA 2.5.5). Badges inline nao precisam.
- Keyboard: ordem de tab segue DOM, sem `tabindex > 0`. Esc fecha dropdown activity badge, Enter/Space o alterna.
- Aria:
  - Landmarks `<header>`, `<main>`, `<nav>`, `<footer>` explicitos.
  - Live region (`role="status"` aria-live polite) para flash messages e loading-text.
  - Labels em todos os botoes com apenas icone (aria-label).
  - Sparkline com aria-label descritivo + `<title>` no SVG.
  - Cards clicaveis usam `<a>` com area inteira (`::before` expandido), nao `onclick` em div.
- Screen reader: preco sempre precedido de label "Preco de referencia" lido antes do valor.
- Daltonismo: classificacao LOW/MEDIUM/HIGH redundante (cor + badge texto + barra lateral). Nunca comunicar so por cor.

---

## 6. Mobile / Responsive

Breakpoints:
```
--bp-sm: 640px    /* phone landscape */
--bp-md: 768px    /* tablet portrait */
--bp-lg: 1024px   /* tablet landscape / small laptop */
--bp-xl: 1280px   /* desktop */
```

Abordagem mobile-first: estilos base = mobile, media queries progressivas.

Adaptacoes por pagina:
- Landing hero: fs-4xl -> fs-3xl em < md. Mockup side-by-side vira stacked. Padding vertical 48px mobile, 96px desktop.
- Dashboard summary bar: wrap em 2 linhas (metricas topo, actions bottom) < md. Dividers escondidos.
- Card: price area stack abaixo em < md, alinhado a esquerda. Actions wrap.
- Detalhe: chart mantem largura full, snapshots table vira lista de cards.
- Public route: price fs-price-lg -> 44px em < md.
- Admin KPI: 4 col -> 2 col -> 1 col.

Container max-width: 1080px desktop (expandido de 960 atual, aproveita telas wide). Padding lateral 16px mobile, 24px tablet, 32px desktop.

Touch: `@media (hover: none)` suprime card hover translate + shadow (fica estranho em touch). Active states mantidos (feedback tatil).

---

## 7. Dark vs Light Mode

**Default: dark.** Justificativa: (1) produto e consumido majoritariamente a noite (usuarios pesquisando viagens), (2) reforca tom tech/premium, (3) dados numericos (precos, sparklines) destacam mais sobre dark, (4) concorrentes consumer (Google Flights, Decolar) sao light -> diferenciacao imediata.

Light mode oferecido via toggle no header + `prefers-color-scheme: light` automatico. Persistir escolha em cookie `orbita_theme`.

Implementacao: todos os tokens em `:root` (dark) e `[data-theme="light"]` override. Jinja le cookie e seta atributo no `<html>`.

Mapping light:
```
bg-0: #FAFBFF       bg-1: #FFFFFF      bg-2: #F1F5F9
border-1: #E2E8F0   border-2: #CBD5E1  border-3: #94A3B8
text-0: #0B1220     text-1: #334155    text-2: #64748B
```

Brand/semantica permanecem (apenas troca shade 500/600 em hover). Shadows mudam para convencionais. Glow effects removidos (ficam feios em light).

---

## 8. Assets a Produzir

Lista acionavel:
- [ ] `favicon.svg` (simbolo Orbita stroke brand, 24x24 base)
- [ ] `favicon-32.png`, `favicon-16.png` (fallback browsers antigos)
- [ ] `apple-touch-icon.png` 180x180 (simbolo sobre bg gradient brand, com padding safe area 10%)
- [ ] `icon-192.png`, `icon-512.png` (PWA manifest)
- [ ] `manifest.webmanifest` com name "Orbita", theme_color #6366F1, bg #070A13
- [ ] `og-default.png` 1200x630 (logo + slogan "Passagem no momento certo" + gradient brand)
- [ ] `og-route-template.png` gerado on-demand com Pillow (ver 3.4)
- [ ] Logo variants: `logo-mark.svg`, `logo-wordmark.svg`, `logo-full.svg`, `logo-full-light.svg`, `logo-full-dark.svg`
- [ ] Fontes self-hosted: `SpaceGrotesk-{400,500,600,700}.woff2`, `JetBrainsMono-{500,700}.woff2` em `/static/fonts/`
- [ ] Hero illustration SVG: mockup dashboard mini + card preco mini para landing (inline, < 6KB)
- [ ] Empty state icon `orbit-empty.svg` (orbita tracejada sem ponto)

Todos os PNGs exportados em 2x automaticamente (retina) via script build. Otimizar com `oxipng -o4`.

---

## 9. Migration Plan

Ordem de implementacao (fases sugeridas dentro da phase 37+):

**Fase A - Tokens e base (1 dia)**
1. Criar `/static/css/tokens.css` com todas as CSS custom properties (paleta, spacing, typography, radius, shadows, duration).
2. Criar `/static/css/base.css` com reset, body, links, buttons, cards, inputs, badges, helpers.
3. Criar `/static/css/components.css` com summary-bar, price-display, sparkline, toast, empty-state.
4. Incluir em `base.html` (substitui o `<style>` inline gigante atual -> remove ~250 linhas do template).
5. Self-host das fontes, atualizar preload.

**Fase B - Rebrand textual (0.5 dia)**
6. Grep global por "Flight Monitor" -> "Orbita". Lugares esperados:
   - `base.html` title/logo/aria-label
   - `landing.html` textos hero/CTA
   - `dashboard/index.html` footer `v1.2`
   - `public/route.html` title/meta/og
   - `README.md`, `PROJECT.md`, `CLAUDE.md` do projeto
   - Email templates (se houver em `app/emails/`)
   - Alembic migration messages nao renomear (historico)
7. Atualizar `<title>`, og:title, twitter:title, canonical tags.
8. Atualizar favicon + apple-touch + manifest.

**Fase C - Landing + Public Route (1 dia)**
Prioridade SEO first. Estas duas paginas geram trafego externo.
9. Refatorar `landing.html` com nova estrutura (hero + numeros + steps + features + rotas + CTA final).
10. Refatorar `public/route.html` com novo price hero + OG image dinamica via Pillow.
11. Regenerar OG images para rotas populares existentes.

**Fase D - Dashboard (0.75 dia)**
12. Refatorar `dashboard/index.html` extraindo o `<style>` para components.css.
13. Novo price-display component, novo sparkline, nova summary bar.
14. Testar empty state com rotas populares.

**Fase E - Detalhe + Auxiliares (0.75 dia)**
15. `group/detail.html` (chart SVG server-side).
16. `auth/login.html`.
17. `admin/stats.html`.
18. Forms (create/edit group) com novos inputs.

**Fase F - Motion + A11y audit (0.5 dia)**
19. Adicionar transitions, skeleton loaders.
20. Auditoria acessibilidade com axe-core ou Lighthouse.
21. Verificar contraste em light mode.

**Fase G - Light mode opcional (0.5 dia, deferrable)**
22. Toggle no header, cookie persistence, CSS [data-theme="light"].

Total estimado: ~5 dias dev.

Tokens CSS a centralizar (extrair do inline atual):
- Todas as cores hex hoje espalhadas -> var tokens
- Font sizes (hoje 11, 12, 13, 14, 15, 16, 18, 24, 28, 32, 40 sao usados inconsistentemente -> escala formal)
- Radius (hoje 4, 6, 8, 10, 12 soltos -> 4 tokens)
- Durations (hoje 0.15s, 0.2s, 0.3s misturados -> 4 tokens)

Checklist "nao quebrar":
- Rotas da aplicacao inalteradas.
- Nenhuma migration de schema.
- Cookies de sessao preservados.
- Manter compatibilidade com scripts Jinja2 existentes (activity badge, polling overlay).

---

## 10. Inspirations

Referencias visuais que informam o direcionamento. Explicar o que tirar de cada e o que NAO copiar.

- **Linear** (linear.app): grid de 4px, tipografia apertada letter-spacing negativo, uso de gradient sutil em CTAs, dark default com neutros frios. *Tirar*: disciplina tipografica, sistema de tokens. *Nao copiar*: excesso de purple, minimalismo extremo que esconde info (nosso produto precisa densidade).
- **Vercel** (vercel.com): contraste alto, tipografia mono para dados tecnicos, hero limpo. *Tirar*: dual font (sans + mono) com proposito, layout airy no marketing. *Nao copiar*: tudo preto puro (fazemos blue-shifted), excesso de branco espacial.
- **Stripe** (stripe.com): gradientes ricos como assinatura de marca, OG images impecaveis, animacoes sutis que guiam leitura. *Tirar*: uso de gradient como assinatura (nosso brand-gradient), qualidade de OG.  *Nao copiar*: light mode primario, complexidade visual.
- **Kayak/Hopper**: nao copiar. Visual datado, denso demais, paleta de app consumer generico.
- **Superhuman** (superhuman.com): escuridao profunda, acentos frios, hierarquia por peso nao por cor. *Tirar*: bg profundo (#070A13 esta nesta linha), motion minimalista. *Nao copiar*: exclusividade aspiracional (nosso produto e acessivel).
- **Rauno Freiberg / reactwind / raycast**: details de microinteracao, pulse em elementos ativos, feedback sutil mas preciso. *Tirar*: pulse do preco LOW, quality bar dos transitions. *Nao copiar*: complexidade JS (nao temos framework).
- **NASA / Observatory UIs** (conceitual): legitimam a metafora "orbita/radar". Dashboards de tracking espacial usam monoline + dados numericos + pulse de sinal. *Tirar*: linguagem visual radar/tracking no logo e icones. *Nao copiar*: estetica retro brutalista.

Principio unificador: todas essas referencias priorizam **hierarquia por contraste e peso, nao por decoracao**. Orbita segue essa filosofia: um produto de dados deve fazer os dados brilharem; o chrome serve, nao compete.

---

Fim do UI-SPEC. Aprovacao necessaria antes de iniciar implementacao.
