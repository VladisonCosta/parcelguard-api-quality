# 📦 ParcelGuard — API Quality Engineering | Contract + Reliability

![Python](https://img.shields.io/badge/Python-3.12-3776AB) ![pytest](https://img.shields.io/badge/Tests-pytest-0A9EDC) ![Contract](https://img.shields.io/badge/Contract-JSON%20Schema-6D4AA3) ![API](https://img.shields.io/badge/API-FastAPI-009688)

**Testes de API que vão além de verificar status 200.**

Projeto de automação de qualidade para API fictícia de logística. Inclui **API REST executável**, SQLite, autenticação, papéis, remessas, eventos de rastreio, regras de transição, **idempotência**, **concorrência**, contrato JSON Schema versionado, testes de fronteira, Postman e pipeline de cobertura.

## Diferenciais

- **28 casos automatizados** em testes de contrato, autenticação/autorização, negócios, temporais, paginação e concorrência.
- **JSON Schema Draft 2020-12** com validação de formato de timestamp e rejeição de campos extras.
- **Race condition realista:** 6 requisições simultâneas disputam a mesma versão; apenas uma pode ser aceita.
- **Idempotência:** reprocessar o mesmo evento retorna `replayed: true` sem duplicação nem alteração de versão.
- **Qualidade mensurável:** pytest-cov e quality gate de **80% mínimo** no GitHub Actions, com XML de resultados.
- **Ambiente demonstrável:** API FastAPI com Swagger em `/docs`, Docker e coleção Postman.

## Tecnologias

Python 3.11+ · FastAPI · Pydantic v2 · SQLite · pytest · httpx/TestClient · jsonschema · pytest-cov · Docker · GitHub Actions · Postman

## Estrutura profissional

```
app/main.py                     # API completa e persistência
contracts/                      # contratos imutáveis v1
  shipment.v1.schema.json
  scan-result.v1.schema.json
tests/
  conftest.py                   # fixtures isoladas + dados sintéticos
  test_01_contracts.py          # JSON schemas, OpenAPI
  test_02_auth_security.py      # tokens, RBAC, isolamento
  test_03_business_rules.py     # fluxo, idempotência, limites, temporal
  test_04_concurrency.py        # 6 escritas concorrentes
postman/ParcelGuard.postman_collection.json
scripts/perf_smoke.py          # amostra simples de latência local
docs/QA_STRATEGY.md             # riscos, critérios, mitigação
docs/TEST_CASES.md              # matriz de rastreabilidade
docs/DEFECT_TEMPLATE.md         # bug report de exemplo
.github/workflows/quality-gate.yml
```

## Rodar no Windows/PowerShell

Pré-requisitos: Python 3.11+ e Git; Docker é opcional.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest -q --cov=app --cov-report=term-missing --cov-fail-under=80
```

O teste usa banco temporário por execução, sem precisar iniciar servidor. Iniciar API em outro terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8001
```

- **Swagger UI:** http://localhost:8001/docs
- **Health:** http://localhost:8001/health
- **Endpoints:** `/v1/auth/login`, `/v1/shipments`, `/v1/shipments/{tracking_id}`, `/v1/shipments/{tracking_id}/scans`.
- **Docker alternativo:** `docker compose up --build` (porta 8001).
- **Postman:** importe `postman/ParcelGuard.postman_collection.json` e execute requests na ordem.

**Usuários apenas para demonstração:** `operator@parcelguard.local` (operador), `ana@parcelguard.local` e `bruno@parcelguard.local` (clientes), senha `demo1234` para todos. Nunca reutilize em produção.

### Exemplo de operação

```
POST /v1/auth/login              → bearer token
POST /v1/shipments               → PG-000001, CREATED, versão 0
POST /v1/shipments/PG-000001/scans {PICKED_UP, expected_version:0}
                                  → 201, versão 1
POST /v1/shipments/PG-000001/scans (mesmo evento)
                                  → 201, replayed:true, versão 1
POST /v1/shipments/PG-000001/scans (outra ação com versão 0)
                                  → 409 Stale shipment version
```

Eventos são datados em ISO 8601 **com timezone**. Apenas operador cria remessas/registra scans; cada cliente vê apenas suas remessas.

## Evidências e qualidade

- [Estratégia de testes e riscos](docs/QA_STRATEGY.md)
- [Matriz de casos rastreáveis](docs/TEST_CASES.md)
- [Modelo profissional de defeito](docs/DEFECT_TEMPLATE.md)
- Test reports `test-results.xml` e cobertura `coverage.xml` nos artefatos do GitHub Actions.
- Para uma amostra **não científica** de latência local: rode `python scripts/perf_smoke.py` com o servidor iniciado. Não representa teste de carga nem SLA.

## Publicar no GitHub

```powershell
git init
git add .
git commit -m "feat: add parcelguard API quality engineering lab"
git branch -M main
gh repo create parcelguard-api-quality --public --source=. --remote=origin --push
```

Sem `gh`: crie um repositório vazio no GitHub e use `git remote add origin https://github.com/SEU_USUARIO/parcelguard-api-quality.git` e `git push -u origin main`.

## Melhorias futuras

- Testes consumer-driven contract com Pact e ambientes efêmeros.
- Testcontainers com PostgreSQL, matriz multi-versão e chaos experiments controlados.
- Teste de carga com k6 e budgets de latência baseados em infraestrutura conhecida.
- Análise estática, revisão de ameaças e política de lockfile/dependabot.

## Texto curto para currículo/LinkedIn

> **ParcelGuard — API Quality Engineering (Python, pytest, JSON Schema, CI/CD)**: construí uma suíte de testes de contrato, autenticação, autorização, regras de negócio, idempotência e concorrência para uma API REST de logística, com fixtures isoladas, matriz de rastreabilidade e gate de cobertura no GitHub Actions.

**Não é um serviço logístico real.** API e usuários são sintéticos. Licença MIT.
