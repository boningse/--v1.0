from datetime import date, datetime
from typing import List, Optional
 
def resolve_granularity(start_date: str, end_date: str) -> int:
    """根据查询日期范围确定数据读取粒度。
    原则：≤1小时 → t0(10分钟粒度), >1小时且≤24小时 → t1(小时粒度), >1天 → t2(天粒度)
    """
    try:
        st = datetime.strptime(start_date[:19], "%Y-%m-%d %H:%M:%S") if " " in start_date else datetime.strptime(start_date[:10], "%Y-%m-%d")
        et = datetime.strptime(end_date[:19], "%Y-%m-%d %H:%M:%S") if " " in end_date else datetime.strptime(end_date[:10] + " 23:59:59", "%Y-%m-%d %H:%M:%S")
        diff_seconds = (et - st).total_seconds()
        if diff_seconds <= 3600:
            return 0  # t0 - 10分钟表
        elif diff_seconds <= 86400:
            return 1  # t1 - 小时表
        else:
            return 2  # t2 - 天表
    except:
        return 1  # 默认小时粒度

CONVERSION_FACTORS = {
    1: {"name": "标准煤", "unit": "kgce", "factor": 0.1229},
    2: {"name": "碳排放", "unit": "kgCO₂", "factor": 0.997},
    3: {"name": "分项能耗", "unit": "kWh", "factor": 1.0},
    4: {"name": "单位面积能耗", "unit": "kWh/m²", "factor": None},
}

def apply_conversion(data_value: float, conversion_type: int = 3, area: float = None) -> float:
    info = CONVERSION_FACTORS.get(conversion_type, CONVERSION_FACTORS[3])
    if conversion_type == 4 and area and area > 0:
        factor = 1.0 / area
    else:
        factor = info["factor"]
    return round(data_value * factor, 4)

def get_conversion_info(conversion_type: int = 3, area: float = None) -> dict:
    info = CONVERSION_FACTORS.get(conversion_type, CONVERSION_FACTORS[3])
    if conversion_type == 4:
        unit = "kWh/m²"
        factor = round(1.0 / area, 4) if area and area > 0 else 1.0
        return {"name": info["name"], "unit": unit, "factor": factor}
    return dict(info)

def get_year_months(sd: date, ed: date) -> List[str]:
    result, cur = [], date(sd.year, sd.month, 1)
    end = date(ed.year, ed.month, 1)
    while cur <= end:
        result.append(cur.strftime("%Y%m"))
        cur = date(cur.year + 1, 1, 1) if cur.month == 12 else date(cur.year, cur.month + 1, 1)
    return result

def energy_table(ym: str, sign: str, et: int = 1, gran: int = 0) -> str:
    return f"{ym}_energydata_{sign}_e{et}_t{gran}"

def service_table(ym: str, sign: str, gran: int = 0) -> str:
    return f"{ym}_servicedata_{sign}_t{gran}"

def tenement_table(ym: str, sign: str, et: int = 1, gran: int = 0) -> str:
    return f"{ym}_tenementdata_{sign}_e{et}_t{gran}"

def safe_float(v, default=0.0) -> float:
    try: return float(v) if v is not None else default
    except: return default

def parse_date(s: str) -> Optional[date]:
    for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]:
        try: return datetime.strptime(s, fmt).date()
        except: continue
    return None
