"""
分项能耗 - 对应老系统 sub_proAnalyze.html, sub_Proportion.html, sub_proCompare.html
API: BuildingHandler M=6/M=7/M=9
"""
from fastapi import APIRouter, Depends, Query
from routers.auth import current_user
from database import db
from utils.helpers import energy_table, get_year_months, parse_date, safe_float, resolve_granularity, apply_conversion, get_conversion_info
from datetime import date, timedelta

router = APIRouter()

@router.get("/items")
async def get_energy_items(sign: str = Query(...), user: dict = Depends(current_user)):
    """获取分项列表 - 从 energyitem 表动态构建完整分项树"""
    items = db.query("constr_ems", "SELECT id, ParentId, name FROM energyitem ORDER BY id")

    def build_tree(parent_id: int):
        children = []
        for item in items:
            if item.get("ParentId") == parent_id:
                subs = build_tree(item["id"])
                node = {"id": item["id"], "name": item["name"]}
                if subs:
                    node["children"] = subs
                children.append(node)
        return children

    result = {}
    four_cats = {11, 12, 13, 14}
    total_children = []
    for item in items:
        if item.get("ParentId") == 1 and item["id"] in four_cats:
            tree = build_tree(item["id"])
            node = {"id": item["id"], "name": item["name"]}
            if tree:
                node["children"] = tree
            total_children.append(node)
    result["总用电"] = total_children

    ym = date.today().strftime("%Y%m")
    data_ids = set()
    for gran in [0, 1, 2]:
        try:
            rows = db.query("constr_energydata", f"SELECT DISTINCT energyid FROM `{energy_table(ym, sign, 1, gran)}`")
            for r in rows:
                data_ids.add(r["energyid"])
        except:
            pass

    def mark_disabled(nodes):
        for node in nodes:
            if isinstance(node.get("id"), int):
                node["disabled"] = node["id"] not in data_ids
            if "children" in node:
                mark_disabled(node["children"])

    for group in result.values():
        mark_disabled(group)

    return {"success": True, **result}


@router.get("/analysis")
async def energy_analysis(
    sign: str = Query(...), item_ids: str = Query(""),
    start_date: str = Query(...), end_date: str = Query(...),
    xdate: str = Query("day"), conversion_type: int = Query(3),
    user: dict = Depends(current_user),
):
    """分项分析数据 - 按日期范围和读取原则自动选择粒度。"""
    sd = parse_date(start_date); ed = parse_date(end_date)
    if not sd or not ed: return {"success": False, "message": "日期格式错误"}
    yms = get_year_months(sd, ed)
    # 查询建筑面积（用于单位面积能耗换算）
    _area = 0.0
    try:
        ar = db.query_one("constr_ems", "SELECT value FROM v_building WHERE sign=%s AND name='Area'", (sign,))
        if ar and ar["value"]: _area = float(ar["value"])
    except: pass
    conv_info = get_conversion_info(conversion_type, _area)

    raw_ids = [x.strip() for x in item_ids.split(",") if x.strip()] if item_ids else []
    has_total = "total" in raw_ids
    user_ids = [int(x) for x in raw_ids if x != "total"]
    ids = list(user_ids)
    if has_total:
        for eid in (1, 11, 12, 13, 14):
            if eid not in ids:
                ids.append(eid)

    # 按读取原则确定数据查询粒度
    gran = resolve_granularity(start_date, end_date)

    time_data = {}
    for ym in yms:
        try:
            rows = db.query("constr_energydata",
                f"SELECT energyid, timefrom, data FROM `{energy_table(ym, sign, 1, gran)}` WHERE timefrom BETWEEN %s AND %s ORDER BY timefrom",
                (start_date, end_date + " 23:59:59"))
            for r in rows:
                eid = r["energyid"]
                if ids and eid not in ids: continue
                ts = str(r["timefrom"])[:16] if gran <= 1 else str(r["timefrom"])[:10]
                if ts not in time_data: time_data[ts] = {}
                time_data[ts][eid] = time_data[ts].get(eid, 0) + apply_conversion(safe_float(r["data"]), conversion_type, _area)
        except: pass

    if has_total and 1 not in user_ids:
        user_ids.append(1)

    # 查询分项名称
    if user_ids:
        items = db.query("constr_ems", f"SELECT id, name FROM energyitem WHERE id IN ({','.join(['%s']*len(user_ids))}) ORDER BY id", tuple(user_ids))
    else:
        items = []

    # 将总用电改名为"总用电合计"
    for i, item in enumerate(items):
        if item["id"] == 1:
            items[i]["name"] = "总用电合计"
            break

    times = sorted(time_data.keys())

    # ========== 按视图类型(xdate)聚合展示 ==========
    import calendar as _cal
    if xdate == "day":
        # 日视图：聚合为 HH:00 格式
        if gran < 2:
            hour_agg = {}
            for ts in times:
                hour_key = ts[:13]
                if hour_key not in hour_agg: hour_agg[hour_key] = {}
                for eid, v in time_data[ts].items():
                    hour_agg[hour_key][eid] = hour_agg[hour_key].get(eid, 0) + v
            time_data = {}
            for hk, vals in sorted(hour_agg.items()):
                time_data[hk[11:] + ":00"] = vals
            times = sorted(time_data.keys())
        # 补全缺失小时
        for h in range(24):
            ts = f"{h:02d}:00"
            if ts not in time_data: time_data[ts] = {}
        times = sorted(time_data.keys())
        if len(times) > 24:
            times = times[-24:]
            time_data = {ts: time_data[ts] for ts in times}

    elif xdate == "month":
        # 月视图：聚合为 MM-DD 格式
        day_agg = {}
        for ts in times:
            day_key = ts[5:10] if len(ts) >= 10 else ts
            if day_key not in day_agg: day_agg[day_key] = {}
            for eid, v in time_data[ts].items():
                day_agg[day_key][eid] = day_agg[day_key].get(eid, 0) + v
        time_data = day_agg
        # 补全缺失日期
        _, days_in_month = _cal.monthrange(sd.year, sd.month)
        for d in range(1, days_in_month + 1):
            ts = f"{sd.month:02d}-{d:02d}"
            if ts not in time_data: time_data[ts] = {}
        times = sorted(time_data.keys())

    elif xdate == "year":
        # 年视图：聚合为 YYYY-MM 格式
        month_agg = {}
        for ts in times:
            month_key = ts[:7]
            if month_key not in month_agg: month_agg[month_key] = {}
            for eid, v in time_data[ts].items():
                month_agg[month_key][eid] = month_agg[month_key].get(eid, 0) + v
        time_data = month_agg
        for m in range(1, 13):
            ts = f"{sd.year}-{m:02d}"
            if ts not in time_data: time_data[ts] = {}
        times = sorted(time_data.keys())

    else:
        # range 模式：数据点多于24条时合并
        if len(times) > 24:
            n = len(times)
            gs = max(1, (n + 23) // 24)
            new_times = []
            new_data = []
            for i in range(0, n, gs):
                chunk = times[i:i + gs]
                label = chunk[0][-5:] + ("~" + chunk[-1][-5:] if len(chunk) > 1 else "")
                new_times.append(label)
                merged = {}
                for t in chunk:
                    for eid, v in time_data[t].items():
                        merged[eid] = merged.get(eid, 0) + v
                new_data.append(merged)
            times = new_times
            time_data = {label: d for label, d in zip(new_times, new_data)}

    # 查询所有分项用于递归聚合
    all_items = db.query("constr_ems", "SELECT id, ParentId, name FROM energyitem ORDER BY id")

    def _agg_data(item_id, exclude_ids=None):
        """递归获取分项数据：自身有数据用自身，否则加总子项"""
        vals = [round(time_data.get(t, {}).get(item_id, 0), 2) for t in times]
        if any(v != 0 for v in vals):
            return vals
        subs = [node for node in all_items if node.get("ParentId") == item_id]
        if exclude_ids:
            subs = [s for s in subs if s["id"] not in exclude_ids]
        if not subs:
            return [0.0] * len(times)
        result = [0.0] * len(times)
        for sub in subs:
            cd = _agg_data(sub["id"])
            for j in range(len(times)):
                result[j] += cd[j]
        return result

    # 构建系列（递归聚合）
    series = []
    for item in items:
        exclude = {16, 17, 18} if item["id"] == 1 else None
        data_vals = [round(v, 2) for v in _agg_data(item["id"], exclude)]
        series.append({"name": item["name"], "data": data_vals})

    # 合计
    totals = []
    for i, t in enumerate(times):
        total = 0
        for item in items:
            total += series[items.index(item)]["data"][i] if items else 0
        totals.append(round(total, 2))
    series.append({"name": "合计", "data": totals})

    # 汇总
    total_energy = round(sum(totals), 2)
    item_totals = {}
    for item in items:
        item_totals[item["id"]] = round(sum(time_data[t].get(item["id"], 0) for t in times), 2)

    # === 建筑面积 & 参考数据 ===
    area = 0.0
    price = 0.8  # 默认电价 元/度
    try:
        area_row = db.query_one("constr_ems", "SELECT value FROM v_building WHERE sign=%s AND name='Area'", (sign,))
        if area_row and area_row["value"]:
            area = float(area_row["value"])
        # 从价格模板解析电价
        price_row = db.query_one("constr_ems", "SELECT value FROM v_building WHERE sign=%s AND name='BuildingJiageMoban'", (sign,))
        if price_row and price_row["value"]:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(price_row["value"])
            p = root.find('.//Price')
            if p is not None and p.text:
                price = float(p.text)
    except Exception as _trend_err:
        import logging
        logging.getLogger(__name__).warning("Trend error: %s", str(_trend_err)[:200])

    per_area_energy = round(total_energy / area, 2) if area > 0 else 0
    reference_value = round(total_energy * price, 2)

    # === 能耗趋势（环比）：按视图类型对比前一周期 ===
    prev_total = 0.0
    trend = 0.0
    try:
        if xdate == "day":
            # 日视图：对比昨天
            prev_sd = sd - timedelta(days=1)
            prev_ed = ed - timedelta(days=1)
        elif xdate == "month":
            # 月视图：对比上月同期
            import calendar as _cal
            if sd.month == 1:
                prev_sd = sd.replace(year=sd.year-1, month=12, day=1)
            else:
                prev_sd = sd.replace(month=sd.month-1, day=1)
            _, last_day = _cal.monthrange(prev_sd.year, prev_sd.month)
            prev_ed = prev_sd.replace(day=last_day)
        elif xdate == "year":
            # 年视图：对比上年同期
            prev_sd = sd.replace(year=sd.year-1)
            prev_ed = ed.replace(year=ed.year-1)
        else:
            # range 视图：对比前一个同样长度的时段
            period_days = (ed - sd).days + 1
            prev_sd = sd - timedelta(days=period_days)
            prev_ed = sd - timedelta(days=1)

        if prev_sd and prev_ed:
            prev_yms = get_year_months(prev_sd, prev_ed)
            prev_sum = 0.0
            for ym in prev_yms:
                try:
                    rows = db.query("constr_energydata",
                        f"SELECT data FROM {energy_table(ym, sign, 1, gran)} WHERE timefrom BETWEEN %s AND %s",
                        (prev_sd.strftime('%Y-%m-%d'), prev_ed.strftime('%Y-%m-%d') + ' 23:59:59'))
                    for r in rows:
                        prev_sum += apply_conversion(safe_float(r["data"]), conversion_type, _area)
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
        "item_totals": item_totals,
        "area": area,
        "per_area_energy": per_area_energy,
        "reference_value": reference_value,
        "trend": trend,
        "prev_total": prev_total,
    }

    return {"success": True, "times": times, "series": series,
            "items": [{"id": i["id"], "name": i["name"]} for i in items],
            "summary": summary, "conversion": conv_info}


@router.get("/ratio")
async def energy_ratio(
    sign: str = Query(...), start_date: str = Query(...), end_date: str = Query(...),
    item_ids: str = Query(""), xdate: str = Query("day"), conversion_type: int = Query(3),
    user: dict = Depends(current_user),
):
    """分项比例 - 按日期范围和读取原则自动选择粒度"""
    sd = parse_date(start_date); ed = parse_date(end_date)
    if not sd or not ed:
        return {"success": False, "message": "日期格式错误"}
    yms = get_year_months(sd, ed)
    _area = 0.0
    try:
        ar = db.query_one("constr_ems", "SELECT value FROM v_building WHERE sign=%s AND name='Area'", (sign,))
        if ar and ar["value"]: _area = float(ar["value"])
    except: pass
    conv_info = get_conversion_info(conversion_type, _area)

    gran = resolve_granularity(start_date, end_date)

    totals = {}
    for ym in yms:
        try:
            rows = db.query("constr_energydata",
                f"SELECT energyid, SUM(data) as t FROM `{energy_table(ym, sign, 1, gran)}` "
                f"WHERE timefrom BETWEEN %s AND %s GROUP BY energyid",
                (start_date, end_date + " 23:59:59"))
            for r in rows:
                totals[r["energyid"]] = totals.get(r["energyid"], 0) + safe_float(r["t"])
        except:
            pass

    # Optional item_ids filtering
    raw_ids = [x.strip() for x in item_ids.split(",") if x.strip()] if item_ids else []
    has_total = "total" in raw_ids
    user_ids = [int(x) for x in raw_ids if x != "total"]
    ids = list(user_ids)
    if has_total:
        pass

    all_items = db.query("constr_ems", "SELECT id, ParentId, name FROM energyitem ORDER BY id")

    def _agg_value(item_id, visited=None):
        if visited is None:
            visited = set()
        if item_id in visited:
            return 0.0
        visited.add(item_id)
        val = totals.get(item_id, 0)
        if val > 0:
            return val
        subs = [n for n in all_items if n.get("ParentId") == item_id]
        if not subs:
            return 0.0
        return round(sum(_agg_value(n["id"], visited) for n in subs), 2)

    result_totals = {}
    if has_total:
        for eid in (11, 12, 13, 14):
            val = _agg_value(eid)
            if val > 0:
                result_totals[eid] = round(val, 2)
    elif ids:
        for eid in ids:
            children = [n for n in all_items if n.get("ParentId") == eid]
            if children:
                for child in children:
                    val = _agg_value(child["id"])
                    if val > 0:
                        result_totals[child["id"]] = round(val, 2)
            else:
                val = _agg_value(eid)
                if val > 0:
                    result_totals[eid] = round(val, 2)
    else:
        result_totals = {eid: round(v, 2) for eid, v in totals.items() if v > 0}
    totals = result_totals

    # 查询分项名称
    if totals:
        eids = list(totals.keys())
        items = db.query("constr_ems", f"SELECT id, name FROM energyitem WHERE id IN ({','.join(['%s']*len(eids))}) ORDER BY id", eids)
        item_map = {i["id"]: i["name"] for i in items}
    else:
        item_map = {}

    data = [{"name": item_map.get(eid, f"分项{eid}"), "value": round(v, 2)} for eid, v in sorted(totals.items(), key=lambda x: x[1], reverse=True)]
    total = sum(d["value"] for d in data)
    return {"success": True, "data": data, "total": round(total, 2), "conversion": conv_info}
