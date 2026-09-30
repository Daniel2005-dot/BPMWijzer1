from decimal import Decimal, ROUND_FLOOR
from datetime import date
from dateutil.relativedelta import relativedelta
import json
from .historical_tariff_engine import calculate_catalog_price_bpm, calculate_co2_bpm, calculate_mixed_bpm
from .depreciation import calculate_forfaitaire_depreciation
from .result import CalculationResult, TariffCandidate

DATA=json.load(open(__file__.replace('bpm_engine.py','historical_tariffs.json')))
CURRENT_2026={
 'status':'verified','method':'co2_bands',
 'petrol_lpg_bands':[[0,77,687,2],[77,100,841,82],[100,139,2727,181],[139,155,9786,297],[155,None,14538,594]],
 'diesel_surcharge_threshold':69,'diesel_surcharge_per_gram':114.83,
 'diesel_bands':[[0,77,687,2],[77,100,841,82],[100,139,2727,181],[139,155,9786,297],[155,None,14538,594]]
}

def floor_euro(x): return int(Decimal(str(x)).quantize(Decimal('1'),rounding=ROUND_FLOOR))

def current_2026_bpm(co2_gkm,fuel,combustion_fuel=None): return calculate_co2_bpm(co2_gkm,fuel,CURRENT_2026,combustion_fuel=combustion_fuel)

def record_for_date(d):
 d=date.fromisoformat(d) if isinstance(d,str) else d
 for r in DATA['records']:
  if date.fromisoformat(r['start'])<=d<=date.fromisoformat(r['end']): return r
 return None

def historical_bpm(net_catalog_price,co2_gkm,fuel,first_admission,euro6=False,energy_label=None,particulate_mg_km=None,hybrid=False,combustion_fuel=None):
 r=record_for_date(first_admission)
 if not r or r['status']!='verified': raise ValueError('No verified historical tariff')
 if r['method']=='net_catalog_price': return calculate_catalog_price_bpm(net_catalog_price,fuel,dict(r,_first_use_date=first_admission,_co2_gkm=co2_gkm),energy_label=energy_label,particulate_mg_km=particulate_mg_km,hybrid=hybrid)
 if r['method']=='mixed_co2_catalog_price':
  rr=dict(r); rr['_first_use_date']=first_admission; return calculate_mixed_bpm(net_catalog_price,co2_gkm,fuel,rr,euro6=euro6,energy_label=energy_label,particulate_mg_km=particulate_mg_km,hybrid=hybrid,combustion_fuel=combustion_fuel)
 return calculate_co2_bpm(co2_gkm,fuel,r,combustion_fuel=combustion_fuel)

def eligible_historical_records(first_admission,rdw_approval):
 first=date.fromisoformat(first_admission)
 approval=date.fromisoformat(rdw_approval)
 if approval < first:
  raise ValueError('rdw_approval cannot be before first_admission')
 start=first-relativedelta(months=2)
 end=date.fromisoformat(rdw_approval)
 out=[]
 for r in DATA['records']:
  rs,re=date.fromisoformat(r['start']),date.fromisoformat(r['end'])
  if r['status']=='verified' and rs<=end and re>=start: out.append(r)
 return out

def choose_gross_bpm(net_catalog_price,co2_gkm,fuel,first_admission,rdw_approval,euro6=False,allow_current=True,co2_nedc=None,co2_wltp=None,co2_method='auto',energy_label=None,particulate_mg_km=None,hybrid=False,combustion_fuel=None):
 first=date.fromisoformat(first_admission)
 approval=date.fromisoformat(rdw_approval)
 if approval < first:
  raise ValueError('rdw_approval cannot be before first_admission')
 if co2_method not in ('auto','nedc','wltp'):
  raise ValueError('co2_method must be auto, nedc or wltp')
 if first < date(2020,7,1) and co2_method == 'wltp' and co2_wltp is None:
  raise ValueError('co2_wltp is required for co2_method=wltp')
 if first < date(2020,7,1) and co2_method == 'nedc' and co2_nedc is None:
  raise ValueError('co2_nedc is required for co2_method=nedc')
 candidates=[]
 # For first admission before 1 July 2020, the Belastingdienst permits either the
 # NEDC value or, when a CO2MPAS-converted WLTP value exists, the WLTP value
 # with the pre-WLTP historical tariff. For later first admissions the current
 # tariff is WLTP-only.
 def _co2_for_historical():
  if first < date(2020,7,1) and co2_method in ('wltp','nedc'):
   chosen = co2_wltp if co2_method == 'wltp' else co2_nedc
   if chosen is None:
    raise ValueError(f'co2_{co2_method} is required for co2_method={co2_method}')
   return chosen
  if co2_method == 'wltp': return co2_wltp if co2_wltp is not None else co2_gkm
  if co2_method == 'nedc': return co2_nedc if co2_nedc is not None else co2_gkm
  return co2_gkm
 # For vehicles first admitted before 1 July 2020, when both a NEDC value
 # and a permitted WLTP/CO2MPAS-converted value are available, the filer may
 # choose the method that produces the lower applicable gross BPM. Therefore
 # auto must evaluate both values rather than silently using co2_gkm.
 if first < date(2020,7,1) and co2_method == 'auto':
  historical_co2_options = []
  if co2_nedc is not None:
   historical_co2_options.append(('nedc', co2_nedc))
  if co2_wltp is not None:
   historical_co2_options.append(('wltp', co2_wltp))
  if not historical_co2_options:
   historical_co2_options = [('auto', co2_gkm)]
 else:
  historical_co2_options = [(co2_method, _co2_for_historical())]
 for r in eligible_historical_records(first_admission,rdw_approval):
  # A first admission before 1 July 2020 cannot use the post-WLTP
  # 1 July 2020 tariff as its historical NEDC tariff.
  if first < date(2020,7,1) and date.fromisoformat(r['start']) >= date(2020,7,1):
   continue
  for _, historical_co2 in historical_co2_options:
   if r['method']=='net_catalog_price':
    g=calculate_catalog_price_bpm(net_catalog_price,fuel,dict(r,_first_use_date=first_admission,_co2_gkm=co2_gkm),energy_label=energy_label,particulate_mg_km=particulate_mg_km,hybrid=hybrid)
   elif r['method']=='mixed_co2_catalog_price':
    rr=dict(r); rr['_first_use_date']=first_admission; g=calculate_mixed_bpm(net_catalog_price,historical_co2,fuel,rr,euro6=euro6,energy_label=energy_label,particulate_mg_km=particulate_mg_km,hybrid=hybrid,combustion_fuel=combustion_fuel)
   else:
    g=calculate_co2_bpm(historical_co2,fuel,r,euro6=euro6,particulate_mg_km=particulate_mg_km,combustion_fuel=combustion_fuel)
   candidates.append((g,r['start'],r['end']))
 # Current tariff is only valid for cars whose first admission is on/after 2020-07-01 when using current WLTP tariff.
 if allow_current and first>=date(2020,7,1):
  current_co2 = co2_wltp if co2_wltp is not None else co2_gkm
  if co2_method == 'nedc':
   raise ValueError('The current 2026 tariff requires WLTP CO2; use co2_method="wltp" or auto with a WLTP value')
  candidates.append((current_2026_bpm(current_co2,fuel,combustion_fuel=combustion_fuel),'2026-current','2026-current'))
 if not candidates: raise ValueError('No eligible verified tariff candidates')
 return min(candidates,key=lambda x:x[0]), sorted(candidates,key=lambda x:x[0])

def calculate_used_import(net_catalog_price,co2_gkm,fuel,first_admission,rdw_approval,method='forfaitaire',euro6=False,allow_current=True,co2_nedc=None,co2_wltp=None,co2_method='auto',energy_label=None,particulate_mg_km=None,hybrid=False,combustion_fuel=None):
 (gross,start,end),ranking=choose_gross_bpm(net_catalog_price,co2_gkm,fuel,first_admission,rdw_approval,euro6,allow_current,co2_nedc,co2_wltp,co2_method,energy_label,particulate_mg_km,hybrid,combustion_fuel=combustion_fuel)
 dep=calculate_forfaitaire_depreciation(first_admission,rdw_approval) if method=='forfaitaire' else Decimal(str(method))
 payable=max(0,floor_euro(Decimal(gross)*(Decimal(1)-Decimal(dep)/Decimal(100))))
 return {'gross_bpm':gross,'depreciation_pct':float(dep),'payable_bpm':payable,'selected_tariff':start,'tariff_candidates':ranking}


def calculate_vehicle(vehicle, method='forfaitaire', allow_current=True):
    """Return a backwards-compatible dict with an auditable BPM breakdown."""
    from .vehicle import Vehicle
    if not isinstance(vehicle, Vehicle):
        raise TypeError('vehicle must be a Vehicle instance')
    raw = calculate_used_import(
        net_catalog_price=vehicle.net_catalog_price,
        co2_gkm=vehicle.co2_gkm,
        fuel=vehicle.fuel,
        first_admission=vehicle.first_admission.isoformat(),
        rdw_approval=vehicle.rdw_approval.isoformat(),
        method=method,
        euro6=vehicle.euro6,
        allow_current=allow_current,
        co2_nedc=vehicle.co2_nedc,
        co2_wltp=vehicle.co2_wltp,
        co2_method=vehicle.co2_method,
        energy_label=vehicle.energy_label,
        particulate_mg_km=vehicle.particulate_mg_km,
        hybrid=vehicle.hybrid,
        combustion_fuel=vehicle.combustion_fuel,
    )
    gross = Decimal(str(raw['gross_bpm']))
    dep = Decimal(str(raw['depreciation_pct']))
    depreciation_amount = floor_euro(gross * dep / Decimal('100'))
    candidates = tuple(
        TariffCandidate(int(g), start, end, selected=(start == raw['selected_tariff'] and int(g) == raw['gross_bpm']))
        for g, start, end in raw['tariff_candidates']
    )
    result = CalculationResult(
        gross_bpm=raw['gross_bpm'],
        depreciation_pct=raw['depreciation_pct'],
        depreciation_amount=depreciation_amount,
        payable_bpm=raw['payable_bpm'],
        selected_tariff=raw['selected_tariff'],
        co2_gkm=vehicle.co2_gkm if vehicle.co2_method == 'auto' else (vehicle.co2_nedc if vehicle.co2_method == 'nedc' else vehicle.co2_wltp),
        co2_method=vehicle.co2_method,
        tariff_candidates=candidates,
    )
    out = result.to_dict()
    out['vehicle'] = vehicle.to_dict()
    return out
