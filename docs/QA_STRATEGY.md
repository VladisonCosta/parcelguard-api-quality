# Test Strategy — ParcelGuard QA

## Objeto sob teste

API REST fictícia de rastreio de entregas (`/v1`), com sessão autenticada, isolamento por cliente, papéis (`OPERATOR`, `CUSTOMER`), histórico de eventos e controle otimista de versão.

## Riscos priorizados

| Risco | Severidade | Abordagem | Casos |
|---|---|---|---|
| Vazamento entre clientes | Crítica | autenticação + autorização + tentativa cross-tenant | `test_02_auth_security.py` |
| Dupla gravação de evento | Alta | idempotência + reenvio divergente | `test_03_business_rules.py` |
| Corrida de atualização | Alta | 6 requisições em paralelo | `test_04_concurrency.py` |
| Violação de contrato | Alta | JSON Schema Draft 2020-12; rejeitar campos extras | `test_01_contracts.py` |
| Status inválido | Alta | fluxo de estados e negativos | `test_03_business_rules.py` |
| Eventos fora de ordem | Média | timestamps UTC e comparação | `test_03_business_rules.py` |
| Paginação com limites | Média | boundary tests | `test_03_business_rules.py` |

## Critérios de saída

- Suite verde no CI (pytest).
- Coverage **mínima 80%**, aferida automaticamente no job (a ferramenta mede linhas e não substitui qualidade do teste).
- Relatórios `test-results.xml` e `coverage.xml` publicados como artefatos do GitHub Actions.
- Nenhum dado de cliente real ou segredo de produção.

## Modelo de transição

```mermaid
flowchart LR
  A[CREATED] --> B[PICKED_UP]
  B --> C[IN_TRANSIT]
  C --> D[OUT_FOR_DELIVERY]
  D --> E[DELIVERED]
```

Transição fora da sequência → HTTP 409. `expected_version` desatualizada → HTTP 409. Token inválido → HTTP 401. Papel errado → HTTP 403. Identificador não encontrado ou pertencente a outro cliente → HTTP 404 (reduz enumeração). Entrada inválida → HTTP 422.

## Boas práticas ilustradas

- Fixtures pytest isolam cada execução em banco SQLite temporário; execução não depende de estado externo.
- `BEGIN IMMEDIATE` protege a gravação de eventos contra escritas concorrentes; somente uma atualização por versão é aceita.
- `event_id` impede duplicação: repetir o mesmo conteúdo retorna `replayed:true`; repetir ID com conteúdo diferente falha com 409.
- Contrato JSON Schema é versionado em `contracts/`; refatorações incompatíveis ficam explícitas.
- Distinção **teste funcional**, **contrato**, **segurança de autorização** e **concorrência**, sem confundir com uma auditoria de segurança completa.

## Limitações conhecidas

API demonstrativa; não existe transportadora externa, filas, broker, cloud, rate limiting ou armazenamento de credenciais de produção. A suite não substitui testes de carga distribuída nem pentest. Carga sintética do `scripts/perf_smoke.py` mede latência local apenas (sem SLA). Para um serviço real, PostgreSQL, filas e observabilidade seriam avanços naturais.
