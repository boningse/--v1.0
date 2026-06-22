"""
设备能耗 - 对应老系统 sub_equipmentAnalyze.html, sub_equipmentCompare.html
API: nengyuan_sub_shebei_nenghao.ashx
"""
from fastapi import APIRouter, Depends, Query
from routers.auth import current_user
from database import db
from datetime import date, timedelta
from utils.helpers import safe_float, parse_date, get_year_months, service_table, apply_conversion, get_conversion_info

router = APIRouter()

@router.get("/tree")
async def equipment_tree(sign: str = Query(...), user: dict = Depends(current_user)):
    """设备/支路树 - 使用 service + servicecascade + meter 表"""
    bld = db.query_one("constr_ems", "SELECT id FROM building WHERE sign=%s", (sign,))
    if not bld: return {"success": True, "data": [], "tree": []}

    # 获取所有支路/设备
    services = db.query("constr_ems", "SELECT id, name, sign FROM service WHERE BuildingId=%s ORDER BY id", (bld["id"],))
    s_map = {s["id"]: {**s, "children": []} for s in services}

    # 获取级联关系
    cascades = db.query("constr_ems",
        "SELECT * FROM servicecascade WHERE ServiceId IN (SELECT id FROM service WHERE BuildingId=%s)",
        (bld["id"],))

    # 构建父子关系
    marked_children = set()
    for c in cascades:
        sid = c["ServiceId"]
        pid = c.get("ParentServiceId")
        if sid in s_map:
            # 该服务有父节点且在s_map中 → 作为子节点
            if pid is not None and pid in s_map:
                s_map[pid]["children"].append(s_map[sid])
                marked_children.add(sid)
            # 该服务关联的电表信息
            if c.get("MeterId"):
                try:
                    meter = db.query_one("constr_ems", "SELECT id, sign, ip FROM meter WHERE id=%s", (c["MeterId"],))
                    if meter:
                        s_map[sid]["meter"] = {"id": meter["id"], "sign": meter["sign"], "ip": meter.get("ip", "")}
                except: pass

    # 根节点 = 没有被标记为子节点的服务
    roots = [s_map[sid] for sid in s_map if sid not in marked_children]

    return {"success": True, "data": services, "tree": roots}


@router.get("/analysis")
async def equipment_analysis(
    sign: str = Query(...), item_ids: str = Query(""),
    start_date: str = Query(...), end_date: str = Query(...),
    xdate: str = Query("day"), conversion_type: int = Query(3), user: dict = Depends(current_user),
):
    """设备能耗分析 - 按时序返回"""
    sd = parse_date(start_date); ed = parse_date(end_date)
    if not sd or not ed: return {"success": False, "message": "日期格式错误"}
    yms = get_year_months(sd, ed)
    ids = [int(x) for x in item_ids.split(",") if x.strip()] if item_ids else []

    gran_map = {"day": 1, "month": 2, "year": 2, "range": 0}
    gran = gran_map.get(xdate, 0)

    # 获取该建筑下所有支路
    bld = db.query_one("constr_ems", "SELECT id FROM building WHERE sign=%s", (sign,))
    if not bld: return {"success": True, "data": [], "times": []}
    services = db.query("constr_ems", "SELECT id, name, sign FROM service WHERE BuildingId=%s ORDER BY id", (bld["id"],))

    if ids:
        services = [s for s in services if s["id"] in ids]

    # 获取级联关系（service → meter 映射）
    all_cascades = db.query("constr_ems",
        "SELECT * FROM servicecascade WHERE ServiceId IN (SELECT id FROM service WHERE BuildingId=%s)",
        (bld["id"],))
    meter_ids = list(set(c["MeterId"] for c in all_cascades if c.get("MeterId")))
    all_meters = {}
    if meter_ids:
        mrows = db.query("constr_ems",
            f"SELECT id, sign FROM meter WHERE id IN ({','.join(['%s']*len(meter_ids))})",
            tuple(meter_ids))
        all_meters = {m["id"]: m["sign"] for m in mrows}
    # 建立 service_id → meter_sign 映射
    svc_to_data_sign = {}
    for c in all_cascades:
        mid = c.get("MeterId")
        if mid and mid in all_meters:
            svc_to_data_sign[c["ServiceId"]] = all_meters[mid]

    # 查询数据（按电表 sign）
    time_data = {}
    for ym in yms:
        try:
            rows = db.query("constr_servicedata",
                f"SELECT sign, timefrom, data FROM `{service_table(ym, sign, gran)}` WHERE timefrom BETWEEN %s AND %s ORDER BY timefrom",
                (start_date, end_date + " 23:59:59"))
            for r in rows:
                meter_sign = r["sign"]
                ts = str(r["timefrom"])[:16] if gran <= 1 else str(r["timefrom"])[:10]
                if ts not in time_data: time_data[ts] = {}
                time_data[ts][meter_sign] = time_data[ts].get(meter_sign, 0) + safe_float(r["data"])
        except: pass

    times = sorted(time_data.keys())

    # 按视图类型聚合
    if xdate == "day":  # 小时表数据，直接使用
        hour_agg = {}
        for ts in times:
            hour_key = ts[:13]
            if hour_key not in hour_agg: hour_agg[hour_key] = {}
            for svc_sign, v in time_data[ts].items():
                hour_agg[hour_key][svc_sign] = hour_agg[hour_key].get(svc_sign, 0) + v
        time_data = {}
        for hk, vals in sorted(hour_agg.items()):
            time_data[hk[11:] + ":00"] = vals
        times = sorted(time_data.keys())
    elif xdate == "month":
        day_agg = {}
        for ts in times:
            day_key = ts[5:10]
            if day_key not in day_agg: day_agg[day_key] = {}
            for svc_sign, v in time_data[ts].items():
                day_agg[day_key][svc_sign] = day_agg[day_key].get(svc_sign, 0) + v
        time_data = day_agg
        times = sorted(time_data.keys())
    elif xdate == "year":
        month_agg = {}
        for ts in times:
            month_key = ts[:7]
            if month_key not in month_agg: month_agg[month_key] = {}
            for svc_sign, v in time_data[ts].items():
                month_agg[month_key][svc_sign] = month_agg[month_key].get(svc_sign, 0) + v
        time_data = month_agg
        times = sorted(time_data.keys())
    elif xdate == "range":
        hour_agg = {}
        for ts in times:
            hour_key = ts[:13]
            if hour_key not in hour_agg: hour_agg[hour_key] = {}
            for svc_sign, v in time_data[ts].items():
                hour_agg[hour_key][svc_sign] = hour_agg[hour_key].get(svc_sign, 0) + v
        time_data = {}
        for hk, vals in sorted(hour_agg.items()):
            time_data[hk[5:]] = vals
        times = sorted(time_data.keys())
        if len(times) > 30:
            n = len(times)
            gs = (n + 29) // 30
            new_data = {}
            for i in range(0, n, gs):
                chunk = times[i:i + gs]
                label = chunk[0] + "~" + chunk[-1] if len(chunk) > 1 else chunk[0]
                merged = {}
                for t in chunk:
                    for svc_sign, v in time_data[t].items():
                        merged[svc_sign] = merged.get(svc_sign, 0) + v
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

    # 按支路组装响应（用 meter_sign 查数据）
    result = []
    for s in services:
        data_sign = svc_to_data_sign.get(s["id"], s["sign"])
        item_data = [round(apply_conversion(time_data[ts].get(data_sign, 0), conversion_type, _area), 3) for ts in times]
        total = round(sum(item_data), 3)
        result.append({"id": s["id"], "name": s["name"], "sign": s["sign"], "total": total, "data": item_data})

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
                    rows = db.query("constr_servicedata",
                        f"SELECT data FROM {service_table(ym, sign, gran)} WHERE timefrom BETWEEN %s AND %s",
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
