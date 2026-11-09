"""Appels HTTP robustes : retry + backoff exponentiel, jamais d'exception
qui remonte au-delà du nombre de tentatives demandé."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

DEFAULT_TIMEOUT = 10.0


def fetch_json_with_retry(
    url: str,
    *,
    logger: logging.Logger,
    label: str = "ressource",
    params: dict[str, Any] | None = None,
    max_attempts: int | None = None,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    timeout: float = DEFAULT_TIMEOUT,
) -> Any:
    """Récupère un JSON en HTTP avec retry + backoff exponentiel (capé à
    `max_delay`). `max_attempts=None` retente indéfiniment (ne renvoie donc
    jamais d'exception) ; un entier borne le nombre de tentatives et lève la
    dernière exception rencontrée une fois épuisé.
    """
    attempt = 0
    delay = base_delay
    while True:
        attempt += 1
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            if max_attempts is not None and attempt >= max_attempts:
                logger.error(
                    "Échec définitif après %d tentative(s) pour %s (%s) : %s",
                    attempt,
                    label,
                    url,
                    exc,
                )
                raise
            logger.warning(
                "Échec tentative %d pour %s (%s) : %s — nouvelle tentative dans %.0fs",
                attempt,
                label,
                url,
                exc,
                delay,
            )
            time.sleep(delay)
            delay = min(delay * 2, max_delay)
