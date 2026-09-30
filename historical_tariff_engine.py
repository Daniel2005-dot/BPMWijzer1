from decimal import Decimal, ROUND_FLOOR
import json

DATA=json.load(open(__file__.replace("historical_tariff_engine.py","historical_tariffs.json")))

def calculate_catalog_price_bpm(net_catalog_price, fuel, record, energy_label=None, particulate_mg_km=None, hybrid=False):
    if record["status"] != "verified" or record["method"] != "net_catalog_price":
        raise ValueError("Historical tariff is not fully verified for calculation")
    if fuel == "electric" and record.get("end") and record["end"] < "2025-01-01":
        return 0
    amount=Decimal(str(net_catalog_price))*Decimal(str(record["rate"]))
    if fuel == "petrol":
        amount += Decimal(str(record.get("petrol_adjustment",0)))
    elif fuel == "diesel":
        amount += Decimal(str(record.get("diesel_adjustment",0)))
    elif fuel in ("hybrid", "lpg", "other"):
        amount += Decimal(str(record.get("petrol_adjustment",0)))
    else:
        raise ValueError("Fuel not supported by this historical formula")

    # Historical CO2 surcharge introduced from 1 February 2008.
    if record.get("co2_surcharge_per_gram") is not None and fuel != "electric":
        threshold = record.get("co2_surcharge_threshold_diesel") if fuel == "diesel" else record.get("co2_surcharge_threshold_petrol")
        first_use = record.get("_first_use_date")
        first_use_date = __import__("datetime").date.fromisoformat(first_use) if first_use else None
        # The February 2008 CO2 surcharge only applies to cars first used
        # from 1 February 2008 onward, even when the February tariff is
        # otherwise an eligible historical candidate.
        surcharge_start = record.get("co2_surcharge_start")
        surcharge_allowed = True if not surcharge_start else (first_use_date is not None and first_use_date >= __import__("datetime").date.fromisoformat(surcharge_start))
        if threshold is not None and surcharge_allowed:
            co2_value = record.get("_co2_gkm")
            if co2_value is not None and Decimal(str(co2_value)) > Decimal(str(threshold)):
                amount += (Decimal(str(co2_value)) - Decimal(str(threshold))) * Decimal(str(record["co2_surcharge_per_gram"]))

    first_use = record.get("_first_use_date")
    first_use_date = __import__("datetime").date.fromisoformat(first_use) if first_use else None
    if fuel == "diesel" and particulate_mg_km is not None and first_use_date is not None and first_use_date >= __import__("datetime").date(2005,6,1):
        pd = record.get("particulate_differentiation")
        if pd is not None:
            mg = Decimal(str(particulate_mg_km))
            amount += Decimal(str(pd["base_discount"])) + mg * Decimal(str(pd["per_mg"]))
        elif Decimal(str(particulate_mg_km)) <= Decimal("5"):
            if record["start"] >= "2005-06-01" and record["start"] < "2008-04-01": amount -= Decimal("600")
    if first_use_date is not None and first_use_date > __import__("datetime").date(2006,6,30):
        adj=None
        if record["start"] >= "2006-07-01" and record["start"] < "2008-02-01": adj={"A":-1000,"B":-500,"C":0,"D":135,"E":270,"F":405,"G":540}
        elif record["start"] >= "2008-02-01" and record["start"] < "2009-01-01": adj={"A":-1400,"B":-700,"C":0,"D":400,"E":800,"F":1200,"G":1600}
        # The historical tariff changes with the energy label. Never silently
        # calculate a definitive amount without it for periods where the label
        # affects BPM. Missing label must be surfaced as an input requirement.
        if adj:
            if energy_label not in adj:
                raise ValueError("energy_label is required for the verified historical tariff in this period")
            amount += Decimal(str(adj[energy_label]))
    if hybrid and fuel == "hybrid" and first_use_date is not None:
        if first_use_date >= __import__("datetime").date(2006,1,1) and first_use_date < __import__("datetime").date(2006,7,1):
            if energy_label == "A": amount -= Decimal(str(record.get("hybrid_a_discount", 6000)))
            elif energy_label == "B": amount -= Decimal("3000")
        elif first_use_date >= __import__("datetime").date(2006,7,1) and first_use_date < __import__("datetime").date(2010,7,1):
            if energy_label == "A": amount -= Decimal("5000")
            elif energy_label == "B": amount -= Decimal("2500")
    return max(0,int(amount.quantize(Decimal("1"), rounding=ROUND_FLOOR)))


def calculate_co2_bpm(co2_gkm, fuel, record, euro6=False, particulate_mg_km=None, combustion_fuel=None):
    if record["status"] != "verified" or record["method"] != "co2_bands":
        raise ValueError("Historical tariff is not fully verified for CO2 calculation")
    if fuel == "electric":
        # Zero-emission passenger cars had a BPM exemption through 31 December 2024.
        if record.get("end") and record["end"] < "2025-01-01":
            return 0
        fuel = "petrol"
    if fuel == "diesel":
        bands = record.get("diesel_bands") or record.get("petrol_lpg_bands")
    elif fuel == "phev":
        bands = record.get("phev_bands") or record.get("petrol_lpg_bands")
    else:
        bands = record.get("petrol_lpg_bands")
    if not bands:
        raise ValueError("No CO2 tariff bands for this fuel")
    co2=Decimal(str(co2_gkm))
    for lower, upper, fixed, per_gram in bands:
        if ((co2 >= Decimal(str(lower))) if lower == 0 else (co2 > Decimal(str(lower)))) and (upper is None or co2 <= Decimal(str(upper))):
            amount=Decimal(str(fixed)) + (co2-Decimal(str(lower)))*Decimal(str(per_gram))
            break
    else:
        raise ValueError("CO2 value outside tariff bands")
    surcharge_fuel = combustion_fuel if fuel in ("phev", "hybrid") and combustion_fuel else fuel
    if surcharge_fuel == "diesel" and record.get("diesel_surcharge_per_gram") is not None:
        threshold=Decimal(str(record["diesel_surcharge_threshold"]))
        if co2 > threshold:
            amount += (co2-threshold)*Decimal(str(record["diesel_surcharge_per_gram"]))
    # Historical diesel exceptions that also applied to CO2-band tariffs.
    if euro6 and fuel == "diesel" and record.get("euro6_discount"):
        amount -= Decimal(str(record["euro6_discount"]))
    if fuel == "diesel" and record.get("particulate_discount_amount") is not None and record.get("particulate_discount_max_mg_km") is not None:
        if particulate_mg_km is not None and Decimal(str(particulate_mg_km)) <= Decimal(str(record["particulate_discount_max_mg_km"])):
            amount -= Decimal(str(record["particulate_discount_amount"]))
    return int(amount.quantize(Decimal("1"), rounding=ROUND_FLOOR))


def calculate_mixed_bpm(net_catalog_price, co2_gkm, fuel, record, euro6=False, energy_label=None, particulate_mg_km=None, hybrid=False, combustion_fuel=None):
    if record.get("status") != "verified" or record.get("method") != "mixed_co2_catalog_price":
        raise ValueError("Historical tariff is not fully verified for mixed calculation")
    if fuel == "electric" and record.get("end") and record["end"] < "2025-01-01":
        return 0
    bands = record.get("diesel_bands") if fuel == "diesel" else (record.get("phev_bands") if fuel == "phev" else record.get("petrol_lpg_bands"))
    co2=Decimal(str(co2_gkm))
    first_use = record.get("_first_use_date")
    first_use_date = __import__("datetime").date.fromisoformat(first_use) if first_use else None
    zr=record.get("zero_rate")
    if zr:
        threshold = zr.get("diesel_max_co2") if fuel == "diesel" else zr.get("petrol_max_co2")
        requires = zr.get("requires_first_use_after")
        condition_ok = True if not requires else (first_use_date is not None and first_use_date > __import__("datetime").date.fromisoformat(requires))
        if threshold is not None and co2 <= Decimal(str(threshold)) and condition_ok:
            if fuel == "diesel" and record.get("diesel_surcharge_per_gram") is not None:
                surcharge=max(Decimal(0), co2-Decimal(str(record["diesel_surcharge_threshold"]))) * Decimal(str(record["diesel_surcharge_per_gram"]))
                return int(surcharge.quantize(Decimal("1"),rounding=ROUND_FLOOR))
            return 0
    amount=None
    for lower, upper, fixed, per_gram in bands:
        if (co2 >= Decimal(str(lower)) if lower == 0 else co2 > Decimal(str(lower))) and (upper is None or co2 <= Decimal(str(upper))):
            amount=Decimal(str(fixed))+(co2-Decimal(str(lower)))*Decimal(str(per_gram)); break
    if amount is None: raise ValueError("CO2 value outside tariff bands")
    amount += Decimal(str(net_catalog_price))*Decimal(str(record["catalog_rate"]))
    if fuel in ("petrol","lpg"):
        amount += Decimal(str(record.get("petrol_adjustment",0)))
    else:
        fixed = record.get("diesel_adjustment",0)
        if record.get("diesel_surcharge_fixed"):
            fixed = fixed if co2 > Decimal(str(record["diesel_surcharge_fixed"]["min_co2_exclusive"])) else 0
        amount += Decimal(str(fixed))
    surcharge_fuel = combustion_fuel if fuel in ("phev", "hybrid") and combustion_fuel else fuel
    if surcharge_fuel == "diesel" and record.get("diesel_surcharge_per_gram") is not None:
        amount += max(Decimal(0), co2-Decimal(str(record["diesel_surcharge_threshold"]))) * Decimal(str(record["diesel_surcharge_per_gram"]))
    if surcharge_fuel == "diesel" and record.get("diesel_surcharge_fixed") and co2 > Decimal(str(record["diesel_surcharge_fixed"]["min_co2_exclusive"])):
        # Fixed surcharge is already represented by diesel_adjustment in these periods.
        pass
    disc=record.get("efficiency_discount")
    if disc and co2 <= Decimal(str(disc["max_co2"])) and ("min_co2_exclusive" not in disc or co2 > Decimal(str(disc["min_co2_exclusive"]))): amount += Decimal(str(disc["amount"]))
    # Historical diesel Euro-6 discount: only apply when the vehicle actually qualifies.
    if euro6 and fuel == "diesel" and record.get("euro6_discount"):
        amount -= Decimal(str(record["euro6_discount"]))

    # Historical fine-particulate discount. This is a BPM rule, not the MRB fine-dust surcharge.
    if fuel == "diesel" and particulate_mg_km is not None and first_use_date is not None and first_use_date >= __import__("datetime").date(2005,6,1):
        pd = record.get("particulate_differentiation")
        if pd is not None:
            mg = Decimal(str(particulate_mg_km))
            amount += Decimal(str(pd["base_discount"])) + mg * Decimal(str(pd["per_mg"]))
        elif Decimal(str(particulate_mg_km)) <= Decimal("5"):
            if record["start"] >= "2005-06-01" and record["start"] < "2010-01-01":
                amount -= Decimal("600")
            elif record["start"] >= "2010-01-01" and record["start"] < "2011-01-01":
                amount -= Decimal("300")

    # Historical energy-label differentiation for vehicles first used after 30 June 2006.
    if energy_label and first_use_date is not None and first_use_date > __import__("datetime").date(2006,6,30):
        label_adjustments = None
        if record["start"] >= "2006-07-01" and record["start"] < "2008-02-01":
            label_adjustments = {"A":-1000,"B":-500,"C":0,"D":135,"E":270,"F":405,"G":540}
        elif record["start"] >= "2008-02-01" and record["start"] < "2009-01-01":
            label_adjustments = {"A":-1400,"B":-700,"C":0,"D":400,"E":800,"F":1200,"G":1600}
        elif record["start"] >= "2009-01-01" and record["start"] < "2010-01-01" and co2 > Decimal("110"):
            label_adjustments = {"A":-1400,"B":-700,"C":0,"D":400,"E":800,"F":1200,"G":1600}
        if label_adjustments and energy_label in label_adjustments:
            amount += Decimal(str(label_adjustments[energy_label]))

    # Historical conventional-hybrid discount. PHEV uses its own historical tariff bands.
    if hybrid and fuel == "hybrid" and first_use_date is not None:
        if first_use_date >= __import__("datetime").date(2006,1,1) and first_use_date < __import__("datetime").date(2006,7,1):
            if energy_label == "A":
                amount -= Decimal(str(record.get("hybrid_a_discount", 6000)))
            elif energy_label == "B":
                amount -= Decimal("3000")
        elif first_use_date >= __import__("datetime").date(2006,7,1) and first_use_date < __import__("datetime").date(2010,7,1):
            if energy_label == "A": amount -= Decimal("5000")
            elif energy_label == "B": amount -= Decimal("2500")

    return max(0,int(amount.quantize(Decimal("1"),rounding=ROUND_FLOOR)))
