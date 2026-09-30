from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_FLOOR
import calendar

TABLE = (
    (0, 1, Decimal('0'), Decimal('12')),
    (1, 3, Decimal('12'), Decimal('4')),
    (3, 5, Decimal('20'), Decimal('3.5')),
    (5, 9, Decimal('27'), Decimal('1.5')),
    (9, 18, Decimal('33'), Decimal('1')),
    (18, 30, Decimal('42'), Decimal('0.75')),
    (30, 42, Decimal('51'), Decimal('0.5')),
    (42, 54, Decimal('57'), Decimal('0.42')),
    (54, 66, Decimal('62'), Decimal('0.42')),
    (66, 78, Decimal('67'), Decimal('0.42')),
    (78, 90, Decimal('72'), Decimal('0.25')),
    (90, 102, Decimal('75'), Decimal('0.25')),
    (102, 114, Decimal('78'), Decimal('0.25')),
)

def full_months_between(start: date, end: date) -> int:
    if end < start: raise ValueError('end date precedes start date')
    months=(end.year-start.year)*12+(end.month-start.month)
    if end.day < start.day:
        if not (start.day==calendar.monthrange(start.year,start.month)[1] and end.day==calendar.monthrange(end.year,end.month)[1]): months-=1
    return max(months,0)

def has_partial_month(start: date, end: date) -> bool:
    if end <= start: return False
    months=full_months_between(start,end)
    y=start.year+(start.month-1+months)//12; mo=(start.month-1+months)%12+1
    day=min(start.day,calendar.monthrange(y,mo)[1]); anchor=date(y,mo,day)
    return end>anchor and not (start.day==calendar.monthrange(start.year,start.month)[1] and end.day==calendar.monthrange(end.year,end.month)[1])

def forfaitaire_percentage(full_months, partial_months=0):
    m=int(full_months); p=1 if partial_months else 0
    if m>=114: return Decimal('81')+Decimal(max(0,m-114+p))*Decimal('0.19')
    for lo,hi,base,inc in TABLE:
        if lo<=m<hi: return base+Decimal(max(0,m-lo)+p)*inc
    raise ValueError('invalid month period')

def calculate_forfaitaire_depreciation(first_admission, rdw_approval):
    s=date.fromisoformat(first_admission) if isinstance(first_admission,str) else first_admission
    e=date.fromisoformat(rdw_approval) if isinstance(rdw_approval,str) else rdw_approval
    return forfaitaire_percentage(full_months_between(s,e),has_partial_month(s,e))
