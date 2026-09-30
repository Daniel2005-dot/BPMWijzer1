from dataclasses import dataclass, asdict
from typing import Any, Optional

@dataclass(frozen=True)
class TariffCandidate:
    gross_bpm: int
    start: str
    end: str
    selected: bool = False

@dataclass(frozen=True)
class CalculationResult:
    gross_bpm: int
    depreciation_pct: float
    depreciation_amount: int
    payable_bpm: int
    selected_tariff: str
    co2_gkm: float
    co2_method: str
    tariff_candidates: tuple[TariffCandidate, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data['tariff_candidates'] = [asdict(x) for x in self.tariff_candidates]
        return data
