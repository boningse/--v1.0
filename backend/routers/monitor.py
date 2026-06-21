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
        "SELECT sc.ServiceId, sc.MeterId, m.sign as meter_sign FROM servicecascade sc "
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
