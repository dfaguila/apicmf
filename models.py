"""
Modelos de datos para la API CMF Chile (v3)
Indicadores: UF, Dólar Observado, IPC
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums de apoyo
# ---------------------------------------------------------------------------

class Indicador(str, Enum):
    UF = "uf"
    DOLAR = "dolar"
    IPC = "ipc"

    @property
    def label(self) -> str:
        return {"uf": "UF", "dolar": "Dólar Observado", "ipc": "IPC"}[self.value]

    @property
    def unidad(self) -> str:
        return {"uf": "CLP", "dolar": "CLP", "ipc": "%"}[self.value]

    @property
    # Clave del array en el JSON de la CMF
    def json_key(self) -> str:
        return {"uf": "UFs", "dolar": "Dolares", "ipc": "IPCs"}[self.value]

    @property
    # Clave del objeto dentro del array
    def json_item_key(self) -> str:
        return {"uf": "UF", "dolar": "Dolar", "ipc": "IPC"}[self.value]


class TipoConsulta(str, Enum):
    HOY = "hoy"
    ANIO = "año"
    MES = "mes"
    FECHA = "fecha"
    PERIODO_MESES = "periodo_meses"
    PERIODO_ANIOS = "periodo_años"


# ---------------------------------------------------------------------------
# Modelos de valor
# ---------------------------------------------------------------------------

@dataclass
class ValorIndicador:
    """Un registro de valor + fecha tal como devuelve la API CMF."""
    fecha: date
    valor: Decimal
    indicador: Indicador

    @classmethod
    def from_cmf_dict(cls, data: dict, indicador: Indicador) -> "ValorIndicador":
        """
        Parsea un dict crudo de la API:
          {"Valor": "37.000,12", "Fecha": "2024-01-15"}
        """
        raw_valor: str = data.get("Valor", "0")
        # La CMF usa coma decimal y punto de miles: "37.000,12" → Decimal("37000.12")
        normalizado = raw_valor.replace(".", "").replace(",", ".")
        try:
            valor = Decimal(normalizado)
        except Exception:
            valor = Decimal("0")

        raw_fecha: str = data.get("Fecha", "")
        try:
            fecha = datetime.strptime(raw_fecha, "%Y-%m-%d").date()
        except ValueError:
            fecha = date.today()

        return cls(fecha=fecha, valor=valor, indicador=indicador)

    def __repr__(self) -> str:
        return (
            f"ValorIndicador("
            f"indicador={self.indicador.label}, "
            f"fecha={self.fecha}, "
            f"valor={self.valor} {self.indicador.unidad})"
        )


@dataclass
class SerieIndicador:
    """Colección de valores de un mismo indicador en un rango temporal."""
    indicador: Indicador
    registros: list[ValorIndicador] = field(default_factory=list)

    # ---- Propiedades de resumen ----------------------------------------

    @property
    def ultimo(self) -> Optional[ValorIndicador]:
        return self.registros[-1] if self.registros else None

    @property
    def primero(self) -> Optional[ValorIndicador]:
        return self.registros[0] if self.registros else None

    @property
    def maximo(self) -> Optional[ValorIndicador]:
        return max(self.registros, key=lambda r: r.valor, default=None)

    @property
    def minimo(self) -> Optional[ValorIndicador]:
        return min(self.registros, key=lambda r: r.valor, default=None)

    @property
    def promedio(self) -> Optional[Decimal]:
        if not self.registros:
            return None
        total = sum(r.valor for r in self.registros)
        return round(total / len(self.registros), 4)

    @property
    def variacion_porcentual(self) -> Optional[Decimal]:
        """Variación % entre el primer y último registro de la serie."""
        if not self.registros or len(self.registros) < 2:
            return None
        inicio = self.primero.valor
        fin = self.ultimo.valor
        if inicio == 0:
            return None
        return round((fin - inicio) / inicio * 100, 2)

    def to_records(self) -> list[dict]:
        """Lista de dicts lista para convertir a DataFrame de pandas."""
        return [
            {
                "fecha": r.fecha,
                "valor": float(r.valor),
                "indicador": r.indicador.label,
            }
            for r in self.registros
        ]

    def __len__(self) -> int:
        return len(self.registros)

    def __repr__(self) -> str:
        return (
            f"SerieIndicador("
            f"indicador={self.indicador.label}, "
            f"registros={len(self.registros)}, "
            f"desde={self.primero.fecha if self.primero else 'N/A'}, "
            f"hasta={self.ultimo.fecha if self.ultimo else 'N/A'})"
        )


# ---------------------------------------------------------------------------
# Modelos de consulta (parámetros de entrada)
# ---------------------------------------------------------------------------

@dataclass
class ConsultaHoy:
    indicador: Indicador
    tipo: TipoConsulta = TipoConsulta.HOY

    def url_path(self) -> str:
        return self.indicador.value


@dataclass
class ConsultaAnio:
    indicador: Indicador
    anio: int
    tipo: TipoConsulta = TipoConsulta.ANIO

    def url_path(self) -> str:
        return f"{self.indicador.value}/{self.anio}"


@dataclass
class ConsultaMes:
    indicador: Indicador
    anio: int
    mes: int  # 1-12
    tipo: TipoConsulta = TipoConsulta.MES

    def url_path(self) -> str:
        return f"{self.indicador.value}/{self.anio}/{self.mes:02d}"


@dataclass
class ConsultaPeriodoMeses:
    """Rango entre dos meses (inclusive), p.ej. 2023/01 → 2024/03."""
    indicador: Indicador
    anio_inicio: int
    mes_inicio: int
    anio_fin: int
    mes_fin: int
    tipo: TipoConsulta = TipoConsulta.PERIODO_MESES

    def url_path(self) -> str:
        return (
            f"{self.indicador.value}/periodo"
            f"/{self.anio_inicio}/{self.mes_inicio:02d}"
            f"/{self.anio_fin}/{self.mes_fin:02d}"
        )


@dataclass
class ConsultaPeriodoAnios:
    """Rango entre dos años (inclusive), p.ej. 2020 → 2024."""
    indicador: Indicador
    anio_inicio: int
    anio_fin: int
    tipo: TipoConsulta = TipoConsulta.PERIODO_ANIOS

    def url_path(self) -> str:
        return (
            f"{self.indicador.value}/periodo"
            f"/{self.anio_inicio}/{self.anio_fin}"
        )
