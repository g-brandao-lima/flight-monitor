# Phase 36: Multi-Leg Trip Builder - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 36-multi-leg
**Areas discussed:** Passageiros por trecho, Janela auto-calculada na UI, Fallback sem cache, Max trechos, Comparadores externos em multi

---

## Selecao de areas pra discutir

Oferecidas: Passageiros por trecho, Janela auto-calculada na UI, Fallback sem cache, Top roteiros no detalhe.

**Selecao do usuario:** Passageiros + Janela UI + Fallback cache.
**Nao selecionados:** Top roteiros no detalhe (assumido: so a mais barata, classificado como Claude's discretion no CONTEXT).

---

## Maximo de trechos

| Opcao | Descricao | Selecionada |
|---|---|---|
| 5 trechos | Sugestao do SPEC, cobre eurotrips sem abuso | ✓ |
| 3 trechos | Mais conservador, forca blocos simples | |
| 7 trechos | Mais liberal, busca fica cara | |

**Escolha:** 5 trechos.

---

## Comparadores externos em grupos multi

| Opcao | Descricao | Selecionada |
|---|---|---|
| Link por trecho individual | Cada trecho com seu cluster de 4 providers | ✓ |
| URL multi-city consolidada | 1 botao por provider com multi-city query, research por provider | |
| So Google Flights multi-city + per-trecho nos outros | Hibrido | |

**Escolha:** Link por trecho individual. URL multi-city consolidada fica deferida.

---

## Passageiros por trecho

| Opcao | Descricao | Selecionada |
|---|---|---|
| Um valor global | Campo `passengers` unico no grupo, todos os trechos herdam | ✓ |
| Variar por trecho | Cada leg com seu proprio `passengers` | |

**Escolha:** Valor global. Variacao por trecho vira deferred idea.

---

## Janela auto-calculada na UI

| Opcao | Descricao | Selecionada |
|---|---|---|
| Auto com override | Janela do N+1 vem preenchida mas editavel | ✓ |
| Sugerir placeholder mas exigir preenchimento | User precisa confirmar | |
| So manual | User preenche cada janela do zero | |

**Escolha:** Auto com override. Zero friccao, flexibilidade preservada.

---

## Fallback sem cache Travelpayouts

| Opcao | Descricao | Selecionada |
|---|---|---|
| SerpAPI on-demand | Cai pra SerpAPI, popula cache, registra uso em quota | ✓ |
| Mostrar "sem dado" ate proximo cron | Zero custo mas UX ruim | |
| Bloquear criacao do grupo | Muito restritivo | |

**Escolha:** SerpAPI on-demand com logging em `cache_lookup_log`.

---

## Claude's Discretion

Areas onde o usuario nao foi consultado explicitamente — planner decide:
- UI exata do construtor de trechos (separadores, animacoes, cores dentro dos tokens Orbita)
- Algoritmo exato de produto cartesiano de datas (performance vs qualidade)
- Schemas Pydantic detalhados
- Texto exato de mensagens de erro de validacao

---

## Deferred Ideas

- Passageiros variaveis por trecho
- URL multi-city consolidada nos botoes de comparador
- Top 3 combinacoes de datas no detail
- Stopover pago intencional
- Open-jaw destacado na UI
- Otimizacao automatica de hub/rota
- Affiliate multi-city (Plan 4 do SPEC original)
- Combinar milhas + dinheiro
