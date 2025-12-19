# Contract Tests - API Schema Validation with Pydantic
"""
Este módulo contém testes de contrato que validam que as respostas
da API mantêm a estrutura esperada (schemas).

Filosofia:
- APIs são contratos. Se mudarmos a estrutura, clientes quebram.
- Contract tests garantem que nunca quebramos sem saber.
- Usamos Pydantic para validação automática de tipos.
"""
