import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "engine_core"))
from bpm_v10.web.release1_adapter import calculate_release1

BASE = {
    "first_admission": "01/2021",
    "mileage_km": "88500",
    "fuel": "phev_diesel",
    "co2_gkm": "38",
    "co2_method": "auto",
}

def test_partial_date_is_accepted_without_inventing_a_day():
    out = calculate_release1(BASE)
    assert out["status"] == "ok"
    assert out["first_admission"] == "2021-01-01"  # tariff anchor only; no depreciation date is fabricated

def test_july_2020_automatic_uses_wltp_and_discloses_assumption():
    p = dict(BASE, first_admission="07/2020")
    out = calculate_release1(p)
    assert out["status"] == "ok"
    assert out["co2_method"] == "wltp"
    assert "WLTP" in out["method_assumption"]

def test_all_fuels_are_accepted():
    fuels = ["petrol", "diesel", "hybrid_petrol", "hybrid_diesel", "phev_petrol", "phev_diesel", "electric", "lpg"]
    for fuel in fuels:
        out = calculate_release1(dict(BASE, fuel=fuel, co2_gkm="130"))
        assert out["status"] == "ok", (fuel, out)

def test_used_vehicle_uses_lowest_verified_tariff_in_period():
    out = calculate_release1(dict(BASE, first_admission="2021-01-15", fuel="petrol", co2_gkm="130"))
    assert out["gross_bpm"] == 3674
    assert out["selected_tariff_start"] == "2020-07-01"

def test_hybrid_mapping():
    out = calculate_release1(dict(BASE, first_admission="2021-01-15", fuel="phev_diesel"))
    assert out["phev"] is True and out["hybrid"] is True and out["fuel"] == "phev"

def test_pre_wltp_automatic_assumes_nedc_and_discloses_it():
    out = calculate_release1(dict(BASE, first_admission="01/2019", fuel="petrol", co2_method="auto"))
    assert out["status"] == "ok"
    assert out["co2_method"] == "nedc"
    assert "NEDC" in out["method_assumption"]

def test_pre_wltp_co2_band_can_calculate_gross():
    out = calculate_release1(dict(BASE, first_admission="01/2019", fuel="petrol", co2_method="NEDC", co2_gkm="130"))
    assert out["status"] == "ok"

def test_legacy_catalogue_route_stays_controlled():
    out = calculate_release1(dict(BASE, first_admission="01/2010", fuel="petrol", co2_method="NEDC"))
    assert out["status"] == "control_required"


def test_diesel_hybrid_gets_diesel_surcharge():
    petrol = calculate_release1(dict(BASE, first_admission="2021-01-15", fuel="hybrid_petrol", co2_gkm="130"))
    diesel = calculate_release1(dict(BASE, first_admission="2021-01-15", fuel="hybrid_diesel", co2_gkm="130"))
    assert diesel["gross_bpm"] > petrol["gross_bpm"]


def test_2023_hybrid_selects_lower_historical_tariff_and_applies_depreciation():
    out = calculate_release1(dict(BASE, first_admission="01/2023", fuel="hybrid_petrol", co2_gkm="56"))
    assert out["gross_bpm"] == 432
    assert out["selected_tariff_start"] == "2022-01-01"
    assert (out["display_bpm_min"], out["display_bpm_max"]) == (180, 182)


def test_tariff_comparison_includes_depreciated_amounts_and_marks_best_gross():
    out = calculate_release1(dict(BASE, first_admission="08/2022", fuel="electric", co2_gkm="0"))
    assert out["status"] == "ok"
    assert out["gross_bpm"] == 0
    assert out["display_bpm_min"] == out["display_bpm_max"] == 0
    assert len(out["tariff_candidates"]) > 1
    assert out["tariff_candidates"][0]["estimated_bpm_min"] == 0
    assert any(option["start"] == "2026-current" and option["gross_bpm"] == 687 for option in out["tariff_candidates"])


def test_pre_july_2020_auto_warning_says_listings_may_show_wltp():
    out = calculate_release1(dict(BASE, first_admission="05/2019", fuel="petrol", co2_gkm="43"))
    assert "AANNAME" in out["method_assumption"]
    assert "advertenties kunnen" in out["method_assumption"].lower()
    assert "NEDC-waarde" in out["method_assumption"]
