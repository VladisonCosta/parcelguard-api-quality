# Evidências de validação local — 19/10/2026

- `python -m pytest -q --cov=app --cov-report=term-missing --cov-fail-under=80` → **28 passed**.
- Cobertura local de linhas: **99,43%** (resultado pode variar se houver mudanças de código/versão).
- Teste de concorrência: 6 requisições, exatamente 1 resposta 201 e 5 respostas 409.
- Contratos: JSON Schema Draft 2020-12 aplicados a objetos de remessa e eventos.
- `Docker` e `GitHub Actions`: arquivos fornecidos; execução dessas ferramentas não validada aqui. Consulte a aba Actions após o primeiro push.

Suíte usa `TestClient` e SQLite temporário, sem dependência de internet.
