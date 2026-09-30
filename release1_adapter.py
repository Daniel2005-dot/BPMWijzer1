"""Release 1 adapter: five user inputs only.

The frozen v36.11 engine remains the calculation authority. Release 1 returns a
BPM estimate (gross BPM) whenever those five fields are sufficient for a
verified CO2 tariff route. It never invents a day, catalogue price, or import
approval date. Cases that need information outside the five-field UI return
``control_required``.
"""
from datetime import date, datetime
import calendar
from decimal import Decimal, ROUND_FLOOR
from typing import Any

from dateutil.relativedelta import relativedelta
from ..bpm_engine import choose_gross_bpm
from ..depreciation import calculate_forfaitaire_depreciation

FUEL_MAP = {
    "petrol": ("petrol", None, False, False),
    "diesel": ("diesel", None, False, False),
    "hybrid_petrol": ("hybrid", "petrol", True, False),
    "hybrid_diesel": ("hybrid", "diesel", True, False),
    "phev_petrol": ("phev", "petrol", True, True),
    "phev_diesel": ("phev", "diesel", True, True),
    "electric": ("electric", None, False, False),
    "lpg": ("lpg", None, False, False),
    # Also accept UI labels for direct API use.
    "Benzine": ("petrol", None, False, False),
    "Diesel": ("diesel", None, False, False),
    "Benzine-hybride": ("hybrid", "petrol", True, False),
    "Diesel-hybride": ("hybrid", "diesel", True, False),
    "Benzine plug-in hybride": ("phev", "petrol", True, True),
    "Diesel plug-in hybride": ("phev", "diesel", True, True),
    "Elektrisch": ("electric", None, False, False),
    "LPG": ("lpg", None, False, False),
}

METHOD_MAP = {
    "auto": "auto",
    "Automatisch bepalen": "auto",
    "wltp": "wltp",
    "WLTP": "wltp",
    "nedc": "nedc",
    "NEDC": "nedc",
}


def _parse_date(raw: str):
    raw = str(raw or "").strip()
    for fmt in ("%m/%Y", "%m-%Y", "%Y-%m", "%Y/%m"):
        try:
            return datetime.strptime(raw, fmt).date(), "month"
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date(), "exact"
        except ValueError:
            pass
    raise ValueError("Eerste toelating moet MM/JJJJ zijn.")


def _number(raw, label):
    s = str(raw or "").strip().replace(".", "").replace(",", ".")
    try:
        value = float(s)
    except ValueError as exc:
        raise ValueError(f"{label} is ongeldig.") from exc
    if value < 0:
        raise ValueError(f"{label} mag niet negatief zijn.")
    return value


def _payable(gross, depreciation_pct):
    return int((Decimal(str(gross)) * (Decimal("100") - depreciation_pct) / Decimal("100")).quantize(Decimal("1"), rounding=ROUND_FLOOR))


def _result(gross, first, mileage, fuel, hybrid, phev, method, as_of, tariff, candidates):
    # The UI only asks for MM/YYYY. Calculate both ends of that month so the
    # estimate does not pretend we know the exact first-admission day.
    first_day = first.replace(day=1)
    last_day = min(
        first.replace(day=calendar.monthrange(first.year, first.month)[1]), as_of
    )
    if first_day > as_of:
        return {"status": "control_required", "reason": "De eerste toelating ligt na de peildatum; controleer de ingevoerde maand."}
    early_dep = min(Decimal("100"), calculate_forfaitaire_depreciation(first_day, as_of))
    late_dep = min(Decimal("100"), calculate_forfaitaire_depreciation(last_day, as_of))
    low_dep, high_dep = sorted((early_dep, late_dep))
    payable_low = _payable(gross, high_dep)
    payable_high = _payable(gross, low_dep)
    return {
        "status": "ok",
        "gross_bpm": int(gross),
        "selected_tariff_start": tariff[1],
        "selected_tariff_end": tariff[2],
        "tariff_candidates": [
            {
                "gross_bpm": int(amount),
                "start": start,
                "end": end,
                "estimated_bpm_min": _payable(amount, high_dep),
                "estimated_bpm_max": _payable(amount, low_dep),
            }
            for amount, start, end in candidates
        ],
        "display_bpm": payable_low if payable_low == payable_high else None,
        "display_bpm_min": payable_low,
        "display_bpm_max": payable_high,
        "depreciation_pct_min": float(low_dep),
        "depreciation_pct_max": float(high_dep),
        "depreciation_bpm_min": int(Decimal(str(gross)) * low_dep / Decimal("100")),
        "depreciation_bpm_max": int(Decimal(str(gross)) * high_dep / Decimal("100")),
        "bpm_type": "after_forfaitaire_depreciation_estimate",
        "estimated": True,
        "depreciation_method": "forfaitaire",
        "as_of_date": as_of.isoformat(),
        "mileage_km": mileage,
        "first_admission": first.isoformat(),
        "fuel": fuel,
        "hybrid": hybrid,
        "phev": phev,
        "co2_method": method,
    }


def calculate_release1(payload: dict[str, Any]) -> dict[str, Any]:
    required = ("first_admission", "mileage_km", "fuel", "co2_gkm", "co2_method")
    missing = [k for k in required if payload.get(k) in (None, "")]
    if missing:
        return {"status": "control_required", "reason": "Vul alle vijf gegevens in."}

    first, precision = _parse_date(payload["first_admission"])
    fuel_key = str(payload["fuel"]).strip()
    if fuel_key not in FUEL_MAP:
        raise ValueError("Ongeldige brandstofkeuze.")
    fuel, combustion_fuel, hybrid, phev = FUEL_MAP[fuel_key]
    mileage = _number(payload["mileage_km"], "Kilometerstand")
    co2 = _number(payload["co2_gkm"], "CO₂-uitstoot")
    method_label = str(payload["co2_method"]).strip()
    method = METHOD_MAP.get(method_label)
    if method is None:
        raise ValueError("Ongeldige CO₂-methode.")
    as_of = date.today()
    if first > as_of:
        return {"status": "control_required", "reason": "De eerste toelating ligt na de peildatum; controleer de ingevoerde maand."}

    # Release 1 keeps method selection simple. The user enters the CO2 figure
    # from the listing and may leave the selector on automatic. For older cars
    # we use NEDC as a clearly disclosed estimate; from July 2020 onward we use
    # WLTP. The exact CO2 value can still differ from the value on the CoC/RDW.
    method_assumption = None
    if method == "auto":
        if first < date(2020, 7, 1):
            method = "nedc"
            method_assumption = "AANNAME: er is gerekend met NEDC omdat de eerste toelating vóór juli 2020 ligt. Advertenties kunnen een WLTP-waarde tonen; deze uitkomst is alleen passend als de ingevoerde waarde de juiste NEDC-waarde is. Controleer de methode en CO₂-waarde op het CoC of bij de RDW."
        else:
            method = "wltp"
            method_assumption = "Automatisch aangenomen: WLTP (eerste toelating vanaf juli 2020). Controleer de CO₂-waarde op het CoC of bij de RDW."

    # Up to 2012 the verified historical routes require catalogue-price data,
    # which is intentionally outside the five-field Release 1 UI.
    if first < date(2013, 1, 1):
        return {
            "status": "control_required",
            "reason": "Voor deze historische BPM-route is aanvullende catalogusprijsinformatie nodig.",
        }

    # From 2013 onward the frozen engine has verified CO2-band tariffs. For
    # 2020-07 the exact day was handled above; other month/year inputs are safe
    # for selecting the tariff year because we do not use them for depreciation.
    if first >= date(2020, 7, 1):
        if method == "nedc":
            return {
                "status": "control_required",
                "reason": "Vanaf 1 juli 2020 gebruikt deze Release 1-route WLTP voor de huidige BPM-tarieven.",
            }
    # Historical tariff candidates start up to two months before first
    # admission. Before 2013 those routes require catalogue price data, which
    # the five-field Release-1 form does not collect.
    if first - relativedelta(months=2) < date(2013, 1, 1):
        return {
            "status": "control_required",
            "reason": "Voor deze historische BPM-route is aanvullende catalogusprijsinformatie nodig.",
        }
    tariff, candidates = choose_gross_bpm(
        net_catalog_price=0,
        co2_gkm=co2,
        fuel=fuel,
        first_admission=first.isoformat(),
        rdw_approval=as_of.isoformat(),
        co2_method=method,
        co2_nedc=co2 if method == "nedc" else None,
        co2_wltp=co2 if method == "wltp" else None,
        combustion_fuel=combustion_fuel,
    )
    gross = tariff[0]
    display_method = "wltp" if first >= date(2020, 7, 1) else method
    result = _result(gross, first, mileage, fuel, hybrid, phev, display_method, as_of, tariff, candidates)
    if method_assumption:
        result["method_assumption"] = method_assumption
    return result
