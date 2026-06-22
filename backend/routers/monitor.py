"""
监测数据 - 对应老系统 sub_Realtimedata.html
API: BuildingEnergyConsumption.ashx M=18/M=19
"""
from fastapi import APIRouter, Depends, Query
from routers.auth import current_user
from database import db
from datetime import date
from utils.helpers import safe_float, service_table, get_year_months, parse_date, energy_table

router = APIRouter()

@router.get("/service/list")
async def service_list(sign: str = Query(...), user: dict = Depends(current_user)):
    rows = db.query("constr_ems", "SELECT * FROM v_service WHERE buildingSign=%s ORDER BY id", (sign,))
    return {"success": True, "data": rows}

@router.get("/service/tree")
async def service_tree(sign: str = Query(...), user: dict = Depends(current_user)):
    services = db.query("constr_ems", "SELECT * FROM v_service WHERE buildingSign=%s ORDER BY id", (sign,))
    if not services: return {"success": True, "data": []}
    svc_map, roots = {}, []
    for s in services:
        node = {"id": s["id"], "name": s["name"], "sign": s["sign"], "BuildingId": s["BuildingId"], "ParentServiceId": s.get("ParentServiceId"), "MeterId": s.get("MeterId"), "children": []}
        svc_map[s["id"]] = node
    for s in services:
        node = svc_map[s["id"]]
        pid = s.get("ParentServiceId")
        if pid and pid in svc_map: svc_map[pid]["children"].append(node)
        else: roots.append(node)
    return {"success": True, "data": roots}

@router.get("/service/energy")
async def service_energy(
    sign: str = Query(...), start_date: str = Query(...), end_date: str = Query(...),
    user: dict = Depends(current_user),
):
    sd = parse_date(start_date); ed = parse_date(end_date)
    yms = get_year_months(sd, ed)
    totals = {}
    for ym in yms:
        try:
            rows = db.query("constr_servicedata", f"SELECT sign, SUM(data) as t FROM `{service_table(ym, sign, 2)}` WHERE timefrom BETWEEN %s AND %s GROUP BY sign", (start_date, end_date + " 23:59:59"))
            for r in rows: totals[r["sign"]] = totals.get(r["sign"], 0) + safe_float(r["t"])
        except: pass
    svc_map = {}
    services = db.query("constr_ems", "SELECT sign, name FROM service WHERE BuildingId=(SELECT id FROM building WHERE sign=%s)", (sign,))
    for s in services: svc_map[s["sign"]] = s["name"]
    result = [{"sign": k, "name": svc_map.get(k, k), "total": round(v, 2)} for k, v in sorted(totals.items(), key=lambda x: x[1], reverse=True)]
    return {"success": True, "data": result}


@router.get("/service/report")
async def service_report(
    sign: str = Query(...), start_date: str = Query(...), end_date: str = Query(...),
    conversion_type: int = Query(3), user: dict = Depends(current_user),
):
    """服务/支路能耗报表 - 返回带层级结构的原始数据表格"""
    from utils.helpers import apply_conversion, get_conversion_info, safe_float, parse_date, get_year_months, service_table

    sd = parse_date(start_date)
    ed = parse_date(end_date)
    if not sd or not ed:
        return {"success": False, "message": "日期格式错误"}
    yms = get_year_months(sd, ed)
    gran = 2  # 以天表为基准

    bld = db.query_one("constr_ems", "SELECT id FROM building WHERE sign=%s", (sign,))
    if not bld:
        return {"success": True, "data": [], "total": 0}

    # 1. 获取服务列表
    services = db.query("constr_ems", "SELECT id, name, sign FROM service WHERE BuildingId=%s ORDER BY id", (bld["id"],))
    svc_map = {s["id"]: s for s in services}

    # 2. 获取级联关系
    cascades = db.query("constr_ems",
        "SELECT sc.*, m.sign as meter_sign FROM servicecascade sc "
        "LEFT JOIN meter m ON sc.MeterId = m.id "
        "WHERE sc.ServiceId IN (SELECT id FROM service WHERE BuildingId=%s)",
        (bld["id"],))
    svc_to_data_sign = {}
    for c in cascades:
        if c.get("meter_sign"):
            svc_to_data_sign[c["ServiceId"]] = c["meter_sign"]

    # 3. 查询能耗原始数据
    meter_totals = {}
    meter_first = {}  # sign -> (time, val)
    meter_last = {}   # sign -> (time, val)
    for ym in yms:
        try:
            tbl = f"bnse_originaldata.`{ym}_recorddata_{sign}`"
            try:
                rows = db.query("constr_ems",
                    f"SELECT sign, data, receivetime FROM {tbl} WHERE receivetime BETWEEN %s AND %s ORDER BY receivetime",
                    (start_date, end_date + " 23:59:59"))
                for r in rows:
                    msign = r["sign"]
                    val = safe_float(r["data"])
                    ts = str(r["receivetime"])[:19]
                    meter_totals[msign] = meter_totals.get(msign, 0) + val
                    if msign not in meter_first:
                        meter_first[msign] = (ts, val)
                    meter_last[msign] = (ts, val)
            except:
                pass
        except:
            pass

    # 4. 构建服务树
    # 标记哪些服务是子节点
    children_ids = set()
    parent_ids = set()
    for c in cascades:
        if c["ServiceId"] in svc_map and c.get("MeterId"):
            # 通过 cascade 查找 parentid
            pass
    # 直接用 servicecascade 中的 ServiceId 和 ParentServiceId 构建
    cascade_parents = {}
    for c in cascades:
        pid = c.get("ParentServiceId")
        if pid and pid in svc_map:
            cascade_parents[c["ServiceId"]] = pid
            children_ids.add(c["ServiceId"])
            parent_ids.add(pid)

    # 5. 递归计算每个节点的总值（叶子节点取 meter 数据，父节点累加子节点）
    all_nodes = {}

    def calc_node(sid):
        """统一计算节点总能耗 + 起止数据，结果缓存在 all_nodes 和 node_fl 中"""
        if sid in all_nodes:
            cached = all_nodes[sid]
            return cached["val"], cached["ft"], cached["fv"], cached["lt"], cached["lv"]
        s = svc_map.get(sid)
        if not s:
            return 0.0, None, None, None, None
        # 计算当前节点的能耗 = 截止数据 - 起始数据
        data_sign = svc_to_data_sign.get(sid, s.get("sign"))
        val = 0.0
        ft, fv, lt, lv = None, None, None, None
        if data_sign in meter_first and data_sign in meter_last:
            ft, fv = meter_first[data_sign]
            lt, lv = meter_last[data_sign]
            raw_val = lv - fv if lv is not None and fv is not None else 0
            val = apply_conversion(raw_val, conversion_type) if raw_val > 0 else 0.0
        # 递归子节点
        child_ids = [c for c, p in cascade_parents.items() if p == sid]
        has_own_meter = data_sign in meter_first and data_sign in meter_last
        if child_ids:
            child_sum = 0.0
            for cid in child_ids:
                c_val, c_ft, c_fv, c_lt, c_lv = calc_node(cid)
                child_sum += c_val
                # 父节点自己有电表数据时，子节点不覆盖起止值
                if not has_own_meter:
                    if c_ft and (ft is None or c_ft < ft):
                        ft, fv = c_ft, c_fv
                    if c_lt and (lt is None or c_lt > lt):
                        lt, lv = c_lt, c_lv
            val = val + child_sum if val > 0 else child_sum
        all_nodes[sid] = {"val": val, "ft": ft, "fv": fv, "lt": lt, "lv": lv}
        return val, ft, fv, lt, lv

    # 扁平化为表格行
    rows_result = []
    root_ids = [s["id"] for s in services if s["id"] not in children_ids]

    def flatten(pid, level):
        row = svc_map.get(pid)
        if not row:
            return
        total_val, ft, fv, lt, lv = calc_node(pid)
        total_val = round(total_val, 3)
        # 若没有结束数据但有开始数据，用开始值代替
        if lt is None and ft is not None:
            lt, lv = ft, fv
        rows_result.append({
            "id": row["id"],
            "name": row["name"],
            "level": level,
            "parent_id": cascade_parents.get(pid),
            "total": total_val,
            "has_data": ft is not None,
            "first_time": ft,
            "first_val": round(fv, 3) if fv is not None else None,
            "last_time": lt,
            "last_val": round(lv, 3) if lv is not None else None,
        })
        child_ids = sorted([c for c, p in cascade_parents.items() if p == pid])
        for cid in child_ids:
            flatten(cid, level + 1)
    for rid in sorted(root_ids):
        flatten(rid, 0)

    # 7. 计算占比
    grand_total = sum(r["total"] for r in rows_result)
    for r in rows_result:
        r["pct"] = round((r["total"] / grand_total * 100) if grand_total > 0 else 0, 1)

    # 8. 获取时间
    start_fmt = start_date[:10]
    end_fmt = end_date[:10]
    for r in rows_result:
        r["start_time"] = start_fmt
        r["end_time"] = end_fmt

    return {
        "success": True,
        "data": rows_result,
        "total": round(grand_total, 3),
        "conversion": get_conversion_info(conversion_type),
    }


@router.get("/alerts")
async def monitor_alerts(
    sign: str = Query(...), user: dict = Depends(current_user),
):
    """报警管理 - 检测长时间不上数、数据异常"""
    from datetime import datetime, timedelta
    from utils.helpers import safe_float

    bld = db.query_one("constr_ems", "SELECT id FROM building WHERE sign=%s", (sign,))
    if not bld:
        return {"success": True, "data": []}

    # 1. 获取所有支路及其电表映射
    services = db.query("constr_ems", "SELECT id, name, sign FROM service WHERE BuildingId=%s ORDER BY id", (bld["id"],))
    cascades = db.query("constr_ems",
        "SELECT sc.ServiceId, sc.MeterId, m.sign as meter_sign FROM servicecascade sc "
        "LEFT JOIN meter m ON sc.MeterId = m.id "
        "WHERE sc.ServiceId IN (SELECT id FROM service WHERE BuildingId=%s)",
        (bld["id"],))
    svc_meter = {c["ServiceId"]: {"id": c["MeterId"], "sign": c["meter_sign"]} for c in cascades if c.get("meter_sign")}

    # 2. 查询每个电表的最新一条数据
    today_ym = datetime.now().strftime("%Y%m")
    now = datetime.now()
    alerts = []

    for s in services:
        meter_info = svc_meter.get(s["id"])
        if not meter_info or not meter_info["sign"]:
            continue

        try:
            tbl = f"bnse_originaldata.`{today_ym}_recorddata_{sign}`"
            row = db.query_one("constr_ems",
                f"SELECT data, receivetime FROM {tbl} WHERE sign=%s ORDER BY receivetime DESC LIMIT 1",
                (meter_info["sign"],))
        except:
            continue

        if not row:
            # 完全无数据
            alerts.append({
                "id": s["id"], "name": s["name"], "type": "不上数",
                "last_time": None, "value": None,
                "duration_min": None, "level": "严重",
                "desc": "该设备至今无数据上报",
            })
            continue

        val = safe_float(row["data"])
        last_time = row["receivetime"]
        if isinstance(last_time, datetime):
            diff = now - last_time
            diff_min = int(diff.total_seconds() / 60)
        else:
            diff_min = None

        # 判断长时间不上数（> 60 分钟）
        if diff_min and diff_min > 60:
            hours = diff_min // 60
            mins = diff_min % 60
            alerts.append({
                "id": s["id"], "name": s["name"], "type": "不上数",
                "last_time": str(last_time)[:19] if last_time else None,
                "value": round(val, 2),
                "duration_min": diff_min,
                "level": "警告" if diff_min <= 180 else "严重",
                "desc": f"已 {hours}小时{mins}分钟 未上报数据",
            })

        # 判断数据异常（值为 0）
        if val == 0 and diff_min and diff_min > 10:
            alerts.append({
                "id": s["id"], "name": s["name"], "type": "数据异常",
                "last_time": str(last_time)[:19] if last_time else None,
                "value": round(val, 2),
                "duration_min": diff_min,
                "level": "警告",
                "desc": "当前读数为 0，可能异常",
            })

    # 按严重程度排序：严重 > 警告
    level_order = {"严重": 0, "警告": 1}
    alerts.sort(key=lambda a: (level_order.get(a["level"], 99), -(a.get("duration_min") or 0)))

    return {"success": True, "data": alerts}

@router.get("/meter/list")
async def meter_list(sign: str = Query(...), user: dict = Depends(current_user)):
    bld = db.query_one("constr_ems", "SELECT id FROM building WHERE sign=%s", (sign,))
    if not bld: return {"success": True, "data": []}
    rows = db.query("constr_ems", "SELECT id, sign, gatewaycode, rate, coilrate, meterClass, isComputer FROM meter WHERE BuildingId=%s ORDER BY id", (bld["id"],))
    return {"success": True, "data": rows}

@router.get("/meter/detail/{meter_id}")
async def meter_detail(meter_id: int, user: dict = Depends(current_user)):
    m = db.query_one("constr_ems", "SELECT * FROM meter WHERE id=%s", (meter_id,))
    if not m: return {"success": False}
    fns = db.query("constr_ems", "SELECT mf.*, ft.name as fnname FROM meterfunction mf LEFT JOIN functiontype ft ON mf.FunctionId=ft.id WHERE mf.MeterId=%s", (meter_id,))
    return {"success": True, "meter": m, "functions": fns}

@router.get("/meter/data")
async def meter_data(
    sign: str = Query(...), selectedids: str = Query(""),
    selectednames: str = Query(""), user: dict = Depends(current_user),
):
    """实时仪表数据 - 读取原始数据表的最新一条记录"""
    bld = db.query_one("constr_ems", "SELECT id FROM building WHERE sign=%s", (sign,))
    if not bld: return {"success": True, "data": []}
    ids = [int(x) for x in selectedids.split(",") if x.strip()] if selectedids else []
    if not ids: return {"success": True, "data": []}

    # 获取服务 → 电表映射
    cascades = db.query("constr_ems",
        "SELECT sc.*, m.sign as meter_sign FROM servicecascade sc "
        "LEFT JOIN meter m ON sc.MeterId = m.id "
        "WHERE sc.ServiceId IN (SELECT id FROM service WHERE BuildingId=%s)",
        (bld["id"],))
    svc_to_meter = {c["ServiceId"]: {"meter_id": c["MeterId"], "sign": c["meter_sign"]} for c in cascades if c.get("meter_sign")}
    svc_to_name = {}
    if ids:
        svcs = db.query("constr_ems", f"SELECT id, name FROM service WHERE id IN ({','.join(['%s']*len(ids))})", tuple(ids))
        svc_to_name = {s["id"]: s["name"] for s in svcs}

    today_ym = date.today().strftime("%Y%m")
    result = []
    for sid in ids:
        name = svc_to_name.get(sid, f"支路{sid}")
        meter_info = svc_to_meter.get(sid)
        if not meter_info or not meter_info["sign"]:
            result.append({"id": sid, "name": name, "sign": "", "value": None, "has_data": False})
            continue
        meter_sign = meter_info["sign"]
        val = None
        receivetime = None
        has_data = False
        # 从 originaldata 原始数据表读取最新一条记录
        try:
            ym = date.today().strftime("%Y%m")
            tbl = f"bnse_originaldata.`{ym}_recorddata_{sign}`"
            row = db.query_one("constr_ems",
                f"SELECT data, receivetime FROM {tbl} WHERE sign=%s ORDER BY receivetime DESC, data DESC LIMIT 1",
                (meter_sign,))
            if row:
                val = safe_float(row["data"])
                receivetime = str(row["receivetime"])[:19] if row.get("receivetime") else None
                has_data = True
        except:
            pass
        result.append({"id": sid, "name": name, "sign": meter_sign,
                       "value": round(val, 2) if val is not None else None,
                       "has_data": has_data, "update_time": receivetime})

    return {"success": True, "data": result}

@router.get("/meter/line")
async def meter_line(
    sign: str = Query(...), metersign: str = Query(...),
    user: dict = Depends(current_user),
):
    """实时仪表折线 - 对应 M=19"""
    from datetime import date
    ym = date.today().strftime("%Y%m")
    data = []
    try:
        rows = db.query("constr_energydata",
            f"SELECT timefrom, data FROM `{energy_table(ym, sign, 1, 0)}` WHERE energyid=%s ORDER BY timefrom",
            (metersign,))
        data = [{"timefrom": str(r["timefrom"]), "data": safe_float(r["data"])} for r in rows]
    except: pass
    if not data:
        try:
            rows = db.query("constr_energydata",
                f"SELECT timefrom, data FROM `{energy_table(ym, sign, 1, 1)}` WHERE energyid=%s ORDER BY timefrom",
                (metersign,))
            data = [{"timefrom": str(r["timefrom"]), "data": safe_float(r["data"])} for r in rows]
        except: pass
    return {"success": True, "data": data, "name": str(metersign)}
