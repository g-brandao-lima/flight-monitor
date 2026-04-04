# Research Summary: v2.1 Clareza de Preco e Robustez

**Domain:** Flight price monitoring (existing multi-user app, infrastructure hardening milestone)
**Researched:** 2026-04-03
**Overall confidence:** HIGH

## Executive Summary

O milestone v2.1 combina 7 features de naturezas distintas: 1 infraestrutura (CI), 1 refatoracao (JWT), 1 middleware (rate limiting), 2 melhorias de UX (rotulo de preco + fix passengers), 1 otimizacao (cache SerpAPI) e 1 limpeza (remocao BookingClassSnapshot). A boa noticia e que nenhuma feature tem dependencia forte de outra; a maioria pode ser implementada em paralelo. A ordem importa apenas para seguranca (CI primeiro) e correcao logica (fix passengers antes de cache).

A arquitetura existente e bem estruturada em camadas (routes -> services -> models -> database) e acomoda todas as features sem reestruturacao. As mudancas mais amplas sao JWT (toca 7 arquivos + 2 testes) e rate limiting (toca 4 routers). As demais sao cirurgicas: 1-2 arquivos cada.

O principal risco tecnico e a migracao JWT: substituir SessionMiddleware por JWT em cookie httponly e conceitualmente simples, mas afeta o conftest.py (base de 221 testes), o middleware de auth e o fluxo de login. CI ativo antes desta fase e obrigatorio.

Nenhuma nova dependencia externa pesada. Apenas PyJWT (~150KB) e slowapi (~30KB). O stack permanece enxuto.

## Key Findings

**Stack:** Adicionar PyJWT + slowapi. Remover itsdangerous. Manter todo o resto.
**Architecture:** 5 arquivos novos, ~16 modificados. Zero mudanca em modelos de dados (exceto remocao de BookingClassSnapshot).
**Critical pitfall:** Migracao JWT sem CI ativo pode quebrar 221 testes silenciosamente. CI e pre-requisito absoluto.

## Implications for Roadmap

Suggested phase structure:

1. **CI Pipeline** - Rede de seguranca para o milestone inteiro
   - Addresses: GitHub Actions com pytest
   - Avoids: Regressoes silenciosas em todas as fases seguintes
   - Complexidade: BAIXA (1 arquivo YAML)

2. **Fix passengers hardcoded** - Bug fix simples, desbloqueia cache correto
   - Addresses: fast-flights com Passengers(adults=1) hardcoded
   - Avoids: Cache com chave incorreta (sem passengers)
   - Complexidade: BAIXA (2 arquivos + 2 testes)

3. **Rotulo de preco + total passageiros** - Valor UX imediato
   - Addresses: "por pessoa, ida e volta" em 7 pontos de exibicao
   - Avoids: Nenhum pitfall tecnico
   - Complexidade: BAIXA (5 templates/services, zero backend)

4. **JWT Stateless Sessions** - Refatoracao mais ampla, CI protege
   - Addresses: Escalabilidade horizontal, remocao de SessionMiddleware
   - Avoids: Sessoes stateful que nao escalam
   - Complexidade: MEDIA (7 arquivos + 2 testes, mas escopo bem definido)

5. **Rate Limiting** - Protecao de endpoints
   - Addresses: Abuso de cota SerpAPI, polling manual excessivo
   - Avoids: Rate limiting uniforme sem considerar custo por endpoint
   - Complexidade: BAIXA (5 arquivos, decorator pattern)

6. **Cache SerpAPI** - Otimizacao de cota
   - Addresses: Chamadas SerpAPI duplicadas no mesmo ciclo
   - Avoids: Cache no PostgreSQL (overengineering)
   - Complexidade: BAIXA (2 arquivos, cache in-memory simples)

7. **Remocao BookingClassSnapshot** - Limpeza final
   - Addresses: Tabela e modelo legado nunca populados
   - Avoids: Remover sem migration Alembic
   - Complexidade: BAIXA (migration + 4 arquivos)

**Phase ordering rationale:**
- CI -> tudo: sem CI, qualquer regressao passa despercebida no deploy automatico do Render
- Passengers fix -> cache: chave de cache precisa incluir passengers
- Labels nao depende de nada: pode ser paralelo com fix, mas sequencial e mais seguro com SDD
- JWT antes de rate limiting: request.state.user_id (do JWT) melhora key_func do slowapi
- Limpeza por ultimo: nao bloqueia e nao e bloqueada por nada

**Research flags for phases:**
- Phase 4 (JWT): Requer atencao no conftest.py. Testar manualmente o fluxo Google OAuth apos mudanca.
- Phase 7 (Legacy): Verificar se snapshot_service.py ou testes referenciam booking_classes antes de remover.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | PyJWT e slowapi sao bibliotecas maduras, bem documentadas |
| Features | HIGH | Escopo claro, cada feature mapeada arquivo por arquivo |
| Architecture | HIGH | Codebase lido integralmente, fluxos de dados verificados |
| Pitfalls | HIGH | Baseado em inspecao direta do codigo (nao suposicoes) |

## Gaps to Address

- Refresh token para JWT: nao necessario agora (7 dias de expiracao e suficiente para uso pessoal), mas considerar em milestone futuro se base de usuarios crescer
- Rate limiting com Redis: desnecessario enquanto instancia unica, mas slowapi suporta quando necessario
- Testes de integracao para fluxo OAuth completo: dificeis de automatizar, validar manualmente apos JWT

## Sources

- [SlowAPI GitHub](https://github.com/laurentS/slowapi)
- [FastAPI JWT Official Docs](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [GitHub Actions CI for FastAPI](https://retz.dev/blog/continuous-integration-github-fastapi-and-pytest/)
- Codebase inspection: main.py, app/auth/*, app/services/*, app/routes/*, app/models.py, tests/conftest.py
