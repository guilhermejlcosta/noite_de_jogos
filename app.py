from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core.lobby import router as lobby_router
from games.nao_pode.router import router as nao_pode_router
from games.quem_sou_eu.router import router as quem_sou_eu_router
from games.mimica.router import router as mimica_router
from games.quiz.router import router as quiz_router
from games.mais_provavel.router import router as mais_provavel_router
from games.stop.router import router as stop_router
from games.ito.router import router as ito_router
from games.coup.router import router as coup_router


BASE_DIR = Path(__file__).resolve().parent


app = FastAPI(title="Noite de Jogos")


# ============================================================
# ARQUIVOS ESTÁTICOS
# ============================================================

# IMPORTANTE:
# o caminho mais específico vem primeiro.

app.mount(
    "/static/nao_pode",
    StaticFiles(directory=(BASE_DIR / "games" / "nao_pode" / "web")),
    name="nao_pode_static",
)


app.mount(
    "/static",
    StaticFiles(directory=(BASE_DIR / "web")),
    name="static",
)


# ============================================================
# ROTAS
# ============================================================

app.include_router(lobby_router)

app.include_router(nao_pode_router)

app.include_router(quem_sou_eu_router)

app.include_router(mimica_router)

app.include_router(quiz_router)

app.include_router(mais_provavel_router)

app.include_router(stop_router)

app.include_router(ito_router)

app.include_router(coup_router)


# ============================================================
# HOME
# ============================================================


@app.get("/")
async def home():

    return FileResponse(BASE_DIR / "web" / "index.html")
