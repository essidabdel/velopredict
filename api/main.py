"""Application FastAPI — API de consultation de la disponibilité Vélib'.

Documentation interactive : /docs (Swagger UI) et /redoc.
"""

from __future__ import annotations

from fastapi import FastAPI

from .routers import predictions, stations, stats

app = FastAPI(
    title="VéloPredict API",
    description=(
        "Consultation de la disponibilité des stations Vélib' "
        "(état temps réel, historique, statistiques réseau).\n\n"
        "**Sources des données** : flux GBFS officiel Vélib' Métropole "
        "(temps réel), complété par un historique de plusieurs semaines "
        "importé depuis l'archive communautaire "
        "[tibzsecondaire/velib-data](https://github.com/tibzsecondaire/velib-data), "
        "elle-même dérivée du même flux GBFS officiel et publiée sous "
        "licence [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) "
        "— la même licence que le jeu de données officiel de la Ville de "
        "Paris sur data.gouv.fr."
    ),
    version="0.1.0",
)

app.include_router(stations.router)
app.include_router(predictions.router)
app.include_router(stats.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
