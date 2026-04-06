"""
Cliente para la API CMF Chile v3
Soporta: UF, Dólar Observado, IPC
"""

from __future__ import annotations

import requests
from typing import Union

from models import (
    Indicador,
    SerieIndicador,
    ValorIndicador,
    ConsultaHoy,
    ConsultaAnio,
    ConsultaMes,
    ConsultaPeriodoMeses,
    ConsultaPeriodoAnios,
)

# Tipo unión de todas las consultas posibles
TipoConsultaAny = Union[
    ConsultaHoy,
    ConsultaAnio,
    ConsultaMes,
    ConsultaPeriodoMeses,
    ConsultaPeriodoAnios,
]

CMF_BASE_URL = "https://api.cmfchile.cl/api-sbifv3/recursos_api"


class CMFError(Exception):
    """Error retornado por la API CMF."""
    pass


class CMFClient:
    """
    Cliente de la API CMF Chile.

    Ejemplo de uso:
        client = CMFClient(api_key="TU_API_KEY")
        serie = client.obtener(ConsultaHoy(Indicador.UF))
        print(serie.ultimo)
    """

    def __init__(self, api_key: str, timeout: int = 15) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    # ------------------------------------------------------------------
    # Método principal
    # ------------------------------------------------------------------

    def obtener(self, consulta: TipoConsultaAny) -> SerieIndicador:
        """
        Ejecuta una consulta a la API y devuelve una SerieIndicador.
        """
        url = f"{CMF_BASE_URL}/{consulta.url_path()}"
        params = {"apikey": self.api_key, "formato": "json"}

        try:
            resp = self._session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise CMFError(f"Error HTTP {resp.status_code}: {e}") from e
        except requests.exceptions.RequestException as e:
            raise CMFError(f"Error de red: {e}") from e

        data = resp.json()
        return self._parsear_respuesta(data, consulta.indicador)

    # ------------------------------------------------------------------
    # Métodos de conveniencia
    # ------------------------------------------------------------------

    def uf_hoy(self) -> SerieIndicador:
        return self.obtener(ConsultaHoy(Indicador.UF))

    def dolar_hoy(self) -> SerieIndicador:
        return self.obtener(ConsultaHoy(Indicador.DOLAR))

    def ipc_hoy(self) -> SerieIndicador:
        return self.obtener(ConsultaHoy(Indicador.IPC))

    def uf_anio(self, anio: int) -> SerieIndicador:
        return self.obtener(ConsultaAnio(Indicador.UF, anio))

    def dolar_anio(self, anio: int) -> SerieIndicador:
        return self.obtener(ConsultaAnio(Indicador.DOLAR, anio))

    def ipc_anio(self, anio: int) -> SerieIndicador:
        return self.obtener(ConsultaAnio(Indicador.IPC, anio))

    def uf_mes(self, anio: int, mes: int) -> SerieIndicador:
        return self.obtener(ConsultaMes(Indicador.UF, anio, mes))

    def dolar_mes(self, anio: int, mes: int) -> SerieIndicador:
        return self.obtener(ConsultaMes(Indicador.DOLAR, anio, mes))

    def ipc_mes(self, anio: int, mes: int) -> SerieIndicador:
        return self.obtener(ConsultaMes(Indicador.IPC, anio, mes))

    def periodo(
        self,
        indicador: Indicador,
        anio_inicio: int,
        mes_inicio: int,
        anio_fin: int,
        mes_fin: int,
    ) -> SerieIndicador:
        return self.obtener(
            ConsultaPeriodoMeses(indicador, anio_inicio, mes_inicio, anio_fin, mes_fin)
        )

    # ------------------------------------------------------------------
    # Parseo interno
    # ------------------------------------------------------------------

    def _parsear_respuesta(self, data: dict, indicador: Indicador) -> SerieIndicador:
        """
        Transforma el JSON de la CMF en una SerieIndicador.

        Estructura esperada:
          {"UFs": [{"Valor": "...", "Fecha": "..."}, ...]}
          {"Dolares": [...]}
          {"IPCs": [...]}
        """
        serie = SerieIndicador(indicador=indicador)

        items_root = data.get(indicador.json_key, [])
        if not isinstance(items_root, list):
            items_root = [items_root]

        for item in items_root:
            obj = item.get(indicador.json_item_key)
            if obj is None:
                continue
            # Puede venir como dict o como lista de dicts
            if isinstance(obj, list):
                for sub in obj:
                    serie.registros.append(
                        ValorIndicador.from_cmf_dict(sub, indicador)
                    )
            elif isinstance(obj, dict):
                serie.registros.append(
                    ValorIndicador.from_cmf_dict(obj, indicador)
                )

        # Ordenar por fecha ascendente
        serie.registros.sort(key=lambda r: r.fecha)
        return serie
