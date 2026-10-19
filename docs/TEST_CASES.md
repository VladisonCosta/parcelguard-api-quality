# Matriz rastreável de casos de teste

| ID | Feature | Dado / Ação | Resultado esperado | Automação |
|---|---|---|---|---|
| AUTH-01 | Login | Credenciais válidas | 200 + token bearer | fixture `tokens` |
| AUTH-02 | Login | Senha incorreta | 401 | `test_bad_password` |
| AUTH-03 | Sessão | Logout e reutilização do token | 401 | `test_logout_revokes_token` |
| SEC-01 | RBAC | Customer tenta criar entrega | 403 | `test_customer_cannot_create_shipment` |
| SEC-02 | RBAC | Customer tenta registrar scan | 403 | `test_customer_cannot_scan` |
| SEC-03 | Isolamento | Cliente B consulta remessa de A | 404 | `test_other_customer_cannot_see_shipment` |
| CON-01 | API contract | Resposta `shipment` | JSON Schema v1 | `test_shipment_contract_on_create` |
| CON-02 | API contract | Resposta `scan` | JSON Schema v1 | `test_scan_contract` |
| CON-03 | API contract | Campo inesperado | 422 | `test_strict_request_rejects_extra_fields` |
| SHP-01 | Criação | Customer válido + endereço | 201, CREATED, versão 0 | fixture `shipment` |
| SHP-02 | Criação | Customer desconhecido | 422 | `test_invalid_shipment_rejected` |
| SHP-03 | Listagem | status + limit + offset | 200, total e página correta | `test_list_filter_and_pagination` |
| EVT-01 | Fluxo | CREATED→…→DELIVERED | 4 eventos, versão 4 | `test_full_happy_path` |
| EVT-02 | Negativo | Pular estados | 409 | `test_reject_illegal_transition` |
| EVT-03 | Negativo | Versão antiga | 409 | `test_reject_stale_version` |
| EVT-04 | Idempotência | Repetir o mesmo evento | replay true, versão inalterada | `test_idempotent_replay` |
| EVT-05 | Idempotência | ID igual, corpo distinto | 409 | `test_duplicate_event_different_payload_conflict` |
| EVT-06 | Temporal | timestamp sem timezone/futuro/antigo | 422/409 | `test_invalid_timestamp`, `test_future_timestamp`, `test_out_of_order_timestamp` |
| RACE-01 | Concorrência | 6 gravações na mesma versão | 1 HTTP 201, 5 HTTP 409 | `test_parallel_scans_only_one_wins` |

**Priorização:** segurança de dados, integridade do estado e concorrência são riscos de maior impacto. Testes são repetíveis, mas não pretendem cobrir todos os caminhos de uma plataforma logística real.
