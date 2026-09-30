from dataclasses import dataclass, asdict
from datetime import date
from typing import Optional

VALID_FUELS = {"petrol", "diesel", "phev", "hybrid", "lpg", "electric", "other"}
VALID_CO2_METHODS = {"auto", "nedc", "wltp"}


def _iso(value, name):
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except Exception as exc:
        raise ValueError(f"{name} must be an ISO date (YYYY-MM-DD)") from exc


@dataclass(frozen=True)
class Vehicle:
    """Canonical vehicle input model for the BPM calculation layer."""
    make: str
    model: str
    fuel: str
    first_admission: date
    rdw_approval: date
    net_catalog_price: float
    co2_gkm: float
    co2_nedc: Optional[float] = None
    co2_wltp: Optional[float] = None
    co2_method: str = "auto"
    euro6: bool = False
    phev: bool = False
    hybrid: bool = False
    combustion_fuel: Optional[str] = None
    energy_label: Optional[str] = None
    particulate_mg_km: Optional[float] = None
    euro_norm: Optional[str] = None
    mileage_km: Optional[int] = None
    import_date: Optional[date] = None
    variant: Optional[str] = None

    def __post_init__(self):
        object.__setattr__(self, "first_admission", _iso(self.first_admission, "first_admission"))
        object.__setattr__(self, "rdw_approval", _iso(self.rdw_approval, "rdw_approval"))
        if self.import_date is not None:
            object.__setattr__(self, "import_date", _iso(self.import_date, "import_date"))
        if not self.make or not self.model:
            raise ValueError("make and model are required")
        if self.fuel not in VALID_FUELS:
            raise ValueError(f"fuel must be one of {sorted(VALID_FUELS)}")
        if self.combustion_fuel is not None and self.combustion_fuel not in {"petrol", "diesel", "lpg"}:
            raise ValueError("combustion_fuel must be petrol, diesel or lpg")
        if self.co2_method not in VALID_CO2_METHODS:
            raise ValueError(f"co2_method must be one of {sorted(VALID_CO2_METHODS)}")
        if self.rdw_approval < self.first_admission:
            raise ValueError("rdw_approval cannot be before first_admission")
        if self.net_catalog_price < 0:
            raise ValueError("net_catalog_price cannot be negative")
        if self.co2_gkm < 0:
            raise ValueError("co2_gkm cannot be negative")
        for name, value in (("co2_nedc", self.co2_nedc), ("co2_wltp", self.co2_wltp), ("particulate_mg_km", self.particulate_mg_km)):
            if value is not None and value < 0:
                raise ValueError(f"{name} cannot be negative")
        if self.mileage_km is not None and self.mileage_km < 0:
            raise ValueError("mileage_km cannot be negative")
        if self.first_admission < date(2020, 7, 1):
            if self.co2_method == "nedc" and self.co2_nedc is None:
                raise ValueError("co2_nedc is required when co2_method='nedc'")
            if self.co2_method == "wltp" and self.co2_wltp is None:
                raise ValueError("co2_wltp is required when co2_method='wltp'")
        if self.first_admission >= date(2020, 7, 1) and self.co2_method == "nedc":
            raise ValueError("cars first admitted from 2020-07-01 cannot use co2_method='nedc' for the current WLTP tariff")
        if self.import_date is not None and self.import_date < self.rdw_approval:
            raise ValueError("import_date cannot be before rdw_approval")

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

    def to_dict(self):
        data = asdict(self)
        for key in ("first_admission", "rdw_approval", "import_date"):
            if data[key] is not None:
                data[key] = data[key].isoformat()
        return data
