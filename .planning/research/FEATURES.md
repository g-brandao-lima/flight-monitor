# Feature Landscape: v2.1 Clareza de Preco e Robustez

**Domain:** Monitoramento de passagens aereas - clareza de preco, infraestrutura e otimizacao
**Researched:** 2026-04-03
**Focus:** Features novas para milestone v2.1

## Table Stakes (obrigatorias para este milestone)

| Feature | Por que obrigatoria | Complexidade | Arquivos impactados |
|---------|-------------------|-------------|-------------------|
| Rotulo "por pessoa, ida e volta" | Core value do milestone: clareza de preco. Sem isso, usuario nao sabe se R$ 1.200 e por pessoa ou total | LOW | 5 templates/services |
| Total para multiplos passageiros | Complemento direto do rotulo. Usuarios com 2+ pax precisam ver o custo real | LOW | Mesmos 5 arquivos |
| Fix passengers hardcoded | Bug: fast-flights busca sempre para 1 adulto independente do grupo. Precos retornados sao incorretos para pax > 1 | LOW | 2 services + 2 testes |
| CI (GitHub Actions) | Deploy automatico no Render sem CI = testes quebrados em producao. Risco inaceitavel com 221 testes | LOW | 1 YAML |

## Differentiators (valor adicional)

| Feature | Valor | Complexidade | Arquivos impactados |
|---------|-------|-------------|-------------------|
| JWT stateless | Remove dependencia de estado de sessao. Prepara para escala horizontal. Simplifica stack (remove SessionMiddleware) | MEDIUM | 8 arquivos |
| Rate limiting | Protege cota SerpAPI compartilhada entre usuarios. Previne abuso do polling manual | LOW | 5 arquivos |
| Cache SerpAPI | Reduz consumo de cota em ~50% quando fast-flights falha. Economia direta no free tier (250/mes) | LOW | 2 arquivos |

## Anti-Features (NAO implementar neste milestone)

| Anti-Feature | Por que evitar | O que fazer em vez disso |
|--------------|---------------|------------------------|
| Refresh token JWT | Overkill para uso pessoal com poucos usuarios. Token de 7 dias e suficiente | Expiry de 7 dias, re-login quando expira |
| Rate limiting com Redis | Instancia unica, sem necessidade de estado compartilhado | In-memory via slowapi default |
| Cache persistente (PostgreSQL) | Cache de voos e efemero por natureza (6h). Persistir adiciona I/O e limpeza | Dict in-memory com TTL |
| Pagina 429 customizada complexa | Poucos usuarios, rate limit so dispara em abuso | Mensagem simples "Muitas requisicoes. Aguarde 1 minuto." |
| Migration de dados BookingClassSnapshot | Tabela vazia, nunca populada | DROP TABLE direto |
| Polling adaptativo (variar frequencia por grupo) | Escopo grande demais para este milestone | Manter 2x/dia fixo, revisitar em v2.2 |

## Feature Dependencies

```
CI Pipeline (nenhuma dep)
  |
  +-> JWT Sessions (CI como rede)
  |     +-> Rate Limiting (request.state.user_id melhora key_func)
  |
  +-> Passengers Fix (nenhuma dep)
  |     +-> SerpAPI Cache (chave de cache inclui passengers)
  |
  +-> Price Labels (nenhuma dep)
  |
  +-> Legacy Removal (CI como rede)
```

## MVP Recommendation for v2.1

**Prioridade 1 (core do milestone):**
1. CI Pipeline - custo minimo, beneficio maximo
2. Price Labels + Total - razao de existir do milestone ("clareza de preco")
3. Passengers Fix - bug que invalida precos exibidos

**Prioridade 2 (robustez):**
4. JWT Sessions - melhoria arquitetural significativa
5. Rate Limiting - protecao necessaria

**Prioridade 3 (otimizacao):**
6. SerpAPI Cache - nice-to-have, economia incremental
7. Legacy Removal - housekeeping, zero urgencia

**Se o milestone precisar ser cortado:** Itens 1-5 sao o minimo. Cache e legacy removal podem ir para v2.2 sem impacto.
