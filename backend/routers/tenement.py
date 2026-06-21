"""
分户能耗 - 对应老系统 sub_HouseAnalyze.html, sub_HouseCompare.html
API: nengyuan_sub_fenhu_nenghao.ashx M=0/M=1
"""
from fastapi import APIRouter, Depends, Query
from routers.auth import current_user
from database import db
from datetime import date, timedelta
from utils.helpers import tenement_table, get_year_months, parse_date, safe_float, apply_conversion, get_conversion_info

router = APIRouter()

@router.get("/list")
async def tenement_list(sign: str = Query(...), energy_type: int = Query(1), user: dict = Depends(current_user)):
    """分户列表 - 对应 M=0"""
    bld = db.query_one("constr_ems", "SELECT id FROM building WHERE sign=%s", (sign,))
    if not bld: return {"success": True, "data": []}
    tenements = db.query("constr_ems", "SELECT id, name, sign FROM tenement WHERE BuildingId=%s ORDER BY id", (bld["id"],))
    # 根据能源类型过滤：只显示有该类型数据的分户
    if tenements:
        today_ym = date.today().strftime("%Y%m")
        tsigns = [t["sign"] for t in tenements]
        valid_signs = set()
        for gran in [0, 1, 2]:
            try:
                sql = f"SELECT DISTINCT sign FROM `{tenement_table(today_ym, sign, energy_type, gran)}` WHERE sign IN ({','.join(['%s']*len(tsigns))})"
                rows = db.query("constr_tenementdata", sql, tuple(tsigns))
                for r in rows: valid_signs.add(r["sign"])
                if valid_signs: break
            except: continue
        if valid_signs:
            tenements = [t for t in tenements if t["sign"] in valid_signs]
        else:
            tenements = []  # 该能源类型下无数据分户
    # 获取树形关系
    relations = db.query("constr_ems", "SELECT * FROM tenementrelation WHERE TenementId IN (SELECT id FROM tenement WHERE BuildingId=%s)", (bld["id"],))
    parent_map = {}
    for rel in relations: parent_map.setdefault(rel["ParentTenementId"], []).append(rel["TenementId"])
    t_map = {t["id"]: {**t, "children": []} for t in tenements}
    roots = []
    for t in tenements:
        node = t_map[t["id"]]
        is_root = True
        for pid, children in parent_map.items():
            if t["id"] in children:
                if pid is not None and pid in t_map:
                    t_map[pid]["children"].append(node)
                    is_root = False
                    break
        if is_root:
            roots.append(node)
    return {"success": True, "data": tenements, "tree": roots}

@router.get("/analysis")
async def tenement_analysis(
    sign: str = Query(...), item_ids: str = Query(""),
    start_date: str = Query(...), end_date: str = Query(...),
    xdate: str = Query("day"), conversion_type: int = Query(3), energy_type: int = Query(1), user: dict = Depends(current_user),
):
    """分户分析数据 - 对应 M=1 (时序图)"""
    sd = parse_date(start_date); ed = parse_date(end_date)
    yms = get_year_months(sd, ed)
    ids = [int(x) for x in item_ids.split(",") if x.strip()] if item_ids else []
    gran_map = {"day": 1, "month": 2, "year": 2, "range": 0, "日1": 1, "日2": 1, "日3": 1, "月": 2, "年": 2}
    gran = gran_map.get(xdate, 2)

    # 获取分户列表
    bld = db.query_one("constr_ems", "SELECT id FROM building WHERE sign=%s", (sign,))
    if not bld: return {"success": True, "data": [], "times": []}
    tenements = db.query("constr_ems", "SELECT id, name, sign FROM tenement WHERE BuildingId=%s ORDER BY id", (bld["id"],))

    # Filter by requested IDs
    if ids:
        tenements = [t for t in tenements if t["id"] in ids]

    # Build time-series data per tenement
    time_data = {}
    for ym in yms:
        try:
            rows = db.query("constr_tenementdata",
                f"SELECT sign, timefrom, data FROM `{tenement_table(ym, sign, energy_type, gran)}` WHERE timefrom BETWEEN %s AND %s ORDER BY timefrom",
                (start_date, end_date + " 23:59:59"))
            for r in rows:
                tsign = r["sign"]
                ts = str(r["timefrom"])[:16] if gran <= 1 else str(r["timefrom"])[:10]
                if ts not in time_data: time_data[ts] = {}
                # 同一时间点多条记录重复写入，用MAX去重后累加
                time_data[ts][tsign] = max(time_data[ts].get(tsign, 0), safe_float(r["data"]))
        except: pass

    times = sorted(time_data.keys())

    # 按视图类型聚合
    if xdate == "day":  # 小时表数据，直接使用
        # 10分钟粒度 → 聚合成小时
        hour_agg = {}
        for ts in times:
            hour_key = ts[:13]  # "2026-06-20 00"
            if hour_key not in hour_agg: hour_agg[hour_key] = {}
            for tsign, v in time_data[ts].items():
                hour_agg[hour_key][tsign] = hour_agg[hour_key].get(tsign, 0) + v
        time_data = {}
        for hour_key, vals in sorted(hour_agg.items()):
            label = hour_key[11:] + ":00"  # "HH:00"
            time_data[label] = vals
        times = sorted(time_data.keys())

    elif xdate == "month":
        # 小时级数据 → 聚合成天
        day_agg = {}
        for ts in times:
            day_key = ts[5:10]  # "MM-DD"
            if day_key not in day_agg: day_agg[day_key] = {}
            for tsign, v in time_data[ts].items():
                day_agg[day_key][tsign] = day_agg[day_key].get(tsign, 0) + v
        time_data = {}
        for day_key, vals in sorted(day_agg.items()):
            time_data[day_key] = vals
        times = sorted(time_data.keys())

    elif xdate == "year":
        # 天级数据 → 聚合成月
        month_agg = {}
        for ts in times:
            month_key = ts[:7]  # "YYYY-MM"
            if month_key not in month_agg: month_agg[month_key] = {}
            for tsign, v in time_data[ts].items():
                month_agg[month_key][tsign] = month_agg[month_key].get(tsign, 0) + v
        time_data = {}
        for month_key, vals in sorted(month_agg.items()):
            time_data[month_key] = vals
        times = sorted(time_data.keys())

    elif xdate == "range":
        # 先聚合成小时键
        hour_agg = {}
        for ts in times:
            hour_key = ts[:13]  # "2026-06-20 00"
            if hour_key not in hour_agg: hour_agg[hour_key] = {}
            for tsign, v in time_data[ts].items():
                hour_agg[hour_key][tsign] = hour_agg[hour_key].get(tsign, 0) + v
        time_data = {}
        for hk, vals in sorted(hour_agg.items()):
            label = hk[5:]  # "MM-DD HH"
            time_data[label] = vals
        times = sorted(time_data.keys())

        # 超过30个数据点时合并
        if len(times) > 30:
            n = len(times)
            gs = (n + 29) // 30
            new_data = {}
            for i in range(0, n, gs):
                chunk = times[i:i + gs]
                label = chunk[0] + "~" + chunk[-1] if len(chunk) > 1 else chunk[0]
                merged = {}
                for t in chunk:
                    for tsign, v in time_data[t].items():
                        merged[tsign] = merged.get(tsign, 0) + v
                new_data[label] = merged
            time_data = new_data
            times = sorted(time_data.keys())

    # 补全缺失的时间刻度，确保X轴始终显示完整刻度
    import calendar as _cal
    sd = parse_date(start_date)
    if xdate == "day":
        for h in range(24):
            ts = f"{h:02d}:00"
            if ts not in time_data:
                time_data[ts] = {}
    elif xdate == "month":
        _, days_in_month = _cal.monthrange(sd.year, sd.month)
        for d in range(1, days_in_month + 1):
            ts = f"{sd.month:02d}-{d:02d}"
            if ts not in time_data:
                time_data[ts] = {}
    elif xdate == "year":
        for m in range(1, 13):
            ts = f"{sd.year}-{m:02d}"
            if ts not in time_data:
                time_data[ts] = {}
    times = sorted(time_data.keys())
    if xdate == 'day' and len(times) > 24:
        times = times[:24]
        time_data = {ts: time_data[ts] for ts in times}

    # === 建筑面积 & 参考数据 ===
    _area = 0.0
    _price = 0.8
    try:
        area_row = db.query_one("constr_ems", "SELECT value FROM v_building WHERE sign=%s AND name='Area'", (sign,))
        if area_row and area_row["value"]:
            _area = float(area_row["value"])
        price_row = db.query_one("constr_ems", "SELECT value FROM v_building WHERE sign=%s AND name='BuildingJiageMoban'", (sign,))
        if price_row and price_row["value"]:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(price_row["value"])
            p = root.find('.//Price')
            if p is not None and p.text:
                _price = float(p.text)
    except:
        pass

    # Build per-tenement response
    result = []
    for t in tenements:
        item_data = [round(apply_conversion(time_data[ts].get(t["sign"], 0), conversion_type, _area), 3) for ts in times]
        total = round(sum(item_data), 3)
        result.append({"id": t["id"], "name": t["name"], "sign": t["sign"], "total": total, "data": item_data})

    # Sort by total descending
    result.sort(key=lambda x: x["total"], reverse=True)

    # === 数据概览 ===
    total_energy = round(sum(t["total"] for t in result), 3)
    per_area_energy = total_energy if conversion_type == 4 else (round(total_energy / _area, 3) if _area > 0 else 0)
    reference_value = round(total_energy * _price, 2)

    # 能耗趋势（环比）
    prev_total = 0.0
    trend = 0.0
    try:
        sd = parse_date(start_date)
        ed = parse_date(end_date)
        if xdate == "day":
            prev_sd = sd - timedelta(days=1)
            prev_ed = ed - timedelta(days=1)
        elif xdate == "month":
            import calendar as _cal
            if sd.month == 1:
                prev_sd = sd.replace(year=sd.year-1, month=12, day=1)
            else:
                prev_sd = sd.replace(month=sd.month-1, day=1)
            _, last_day = _cal.monthrange(prev_sd.year, prev_sd.month)
            prev_ed = prev_sd.replace(day=last_day)
        elif xdate == "year":
            prev_sd = sd.replace(year=sd.year-1)
            prev_ed = ed.replace(year=ed.year-1)
        else:
            period_days = (ed - sd).days + 1
            prev_sd = sd - timedelta(days=period_days)
            prev_ed = sd - timedelta(days=1)
        if prev_sd and prev_ed:
            prev_yms = get_year_months(prev_sd, prev_ed)
            prev_sum = 0.0
            for ym in prev_yms:
                try:
                    rows = db.query("constr_tenementdata",
                        f"SELECT data FROM {tenement_table(ym, sign, energy_type, gran)} WHERE timefrom BETWEEN %s AND %s",
                        (prev_sd.strftime('%Y-%m-%d'), prev_ed.strftime('%Y-%m-%d') + ' 23:59:59'))
                    for r in rows:
                        prev_sum += apply_conversion(safe_float(r["data"]), conversion_type)
                except:
                    pass
            prev_total = round(prev_sum, 2)
            if prev_total > 0:
                trend = round((total_energy - prev_total) / prev_total * 100, 1)
    except Exception as _trend_err:
        import logging
        logging.getLogger(__name__).warning("Trend error: %s", str(_trend_err)[:200])

    summary = {
        "total_energy": total_energy,
        "per_area_energy": per_area_energy,
        "reference_value": reference_value,
        "trend": trend,
    }

    return {"success": True, "data": result, "times": times, "conversion": get_conversion_info(conversion_type), "summary": summary}
