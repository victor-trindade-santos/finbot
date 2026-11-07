# app/main.py
"""Ponto de entrada da API.

Local:   uvicorn app.main:app --reload        -> http://127.0.0.1:8000/docs
Render:  uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""
from fastapi import FastAPI

from app.api.rotas import router

# Cria a aplicação. title e description aparecem no topo da página /docs.
# O uvicorn procura esta variável: "app.main:app" = arquivo app/main.py, variável app.
app = FastAPI(title="FinBot API", description="Chat educacional de investimentos — FATEC / PLN")
# Liga as rotas de app/api/rotas.py à aplicação.
app.include_router(router)