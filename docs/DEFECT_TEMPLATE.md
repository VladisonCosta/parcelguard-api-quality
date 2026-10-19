# Modelo de Bug Report para portfólio

> Preencha com um defeito realmente observado. O texto abaixo é apenas **exemplo fictício**, não um bug descoberto neste repositório.

- **ID:** EXEMPLO-001
- **Título:** API aceita `DELIVERED` imediatamente após `CREATED`.
- **Severidade:** Alta — rastreio inconsistente.
- **Ambiente:** API local, versão de exemplo.
- **Pré-condição:** Operador autenticado; remessa em `CREATED`, versão 0.
- **Reprodução:** enviar `POST /v1/shipments/{id}/scans` com `new_status=DELIVERED`.
- **Esperado:** 409, `Invalid status transition`.
- **Obtido no cenário hipotético:** 201 (seria um defeito).
- **Teste de regressão:** `test_reject_illegal_transition`.
- **Evidência:** resposta HTTP anonimizada, log do CI e commit de correção, quando houver.
