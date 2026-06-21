"""
报表打印 - 对应老系统 sub_proReport.html, sub_equipReport.html, sub_madeReport.html
"""
from fastapi import APIRouter, Depends, Query
from routers.auth import current_user
from database import db
from utils.helpers import energy_table, service_table, tenement_table, get_year_months, parse_date, safe_float

router = APIRouter()

@router.get("/general")
async def general_report(
    sign: str = Query(...), year_month: str = Query(...),
    user: dict = Depends(current_user),
):
    """通用报表"""
    try:
        daily = db.query("constr_energydata", f"SELECT energyid, timefrom, data FROM `{energy_table(year_month, sign, 1, 1)}` ORDER BY timefrom")
    except: daily = []
    monthly_total = 0.0
    try:
        r = db.query_one("constr_energydata", f"SELECT SUM(data) as t FROM `{energy_table(year_month, sign, 1, 2)}`")
        if r and r["t"]: monthly_total = safe_float(r["t"])
    except: pass
    try:
        svc = db.query("constr_servicedata", f"SELECT sign, SUM(data) as t FROM `{service_table(year_month, sign, 2)}` GROUP BY sign")
    except: svc = []
    try:
        ten = db.query("constr_tenementdata", f"SELECT sign, SUM(max_data) as t FROM (SELECT sign, timefrom, MAX(data) as max_data FROM `{tenement_table(year_month, sign, 1, 2)}` GROUP BY sign, timefrom) sub GROUP BY sign")
    except: ten = []
    return {"success": True, "data": {"year_month": year_month, "monthly_total": round(monthly_total, 2), "daily": daily, "service_summary": svc, "tenement_summary": ten}}

@router.get("/branch")
async def branch_report(
    sign: str = Query(...), start_date: str = Query(...), end_date: str = Query(...),
    user: dict = Depends(current_user),
):
    """支路报表 - 对应 M=14/35"""
    sd = parse_date(start_date); ed = parse_date(end_date)
    yms = get_year_months(sd, ed)
    svc_totals = {}
    for ym in yms:
        try:
            rows = db.query("constr_servicedata", f"SELECT sign, timefrom, data FROM `{service_table(ym, sign, 1)}` WHERE timefrom BETWEEN %s AND %s ORDER BY timefrom", (start_date, end_date + " 23:59:59"))
            for r in rows:
                key = (r["sign"], str(r["timefrom"])[:10])
                svc_totals[key] = svc_totals.get(key, 0) + safe_float(r["data"])
        except: pass
    services = db.query("constr_ems", "SELECT id, name, sign FROM service WHERE BuildingId=(SELECT id FROM building WHERE sign=%s)", (sign,))
    svc_map = {s["sign"]: s["name"] for s in services}
    days = sorted(set(k[1] for k in svc_totals.keys()))
    result = []
    for svc in services:
        row = {"name": svc["name"], "sign": svc["sign"]}
        for d in days: row[d] = round(svc_totals.get((svc["sign"], d), 0), 2)
        result.append(row)
    return {"success": True, "data": {"days": days, "services": result}}

@router.get("/custom")
async def custom_report(
    sign: str = Query(...), start_date: str = Query(...), end_date: str = Query(...),
    report_type: str = Query("energy"), user: dict = Depends(current_user),
):
    """定制报表"""
    sd = parse_date(start_date); ed = parse_date(end_date)
    yms = get_year_months(sd, ed)
    all_rows = []
    for ym in yms:
        try:
            if report_type == "energy":
                tbl = energy_table(ym, sign, 1, 1)
                rows = db.query("constr_energydata", f"SELECT timefrom, energyid, data FROM `{tbl}` WHERE timefrom BETWEEN %s AND %s ORDER BY timefrom", (start_date, end_date + " 23:59:59"))
            elif report_type == "service":
                tbl = service_table(ym, sign, 1)
                rows = db.query("constr_servicedata", f"SELECT sign, timefrom, data FROM `{tbl}` WHERE timefrom BETWEEN %s AND %s ORDER BY timefrom", (start_date, end_date + " 23:59:59"))
            elif report_type == "tenement":
                tbl = tenement_table(ym, sign, 1, 1)
                rows = db.query("constr_tenementdata", f"SELECT sign, timefrom, MAX(data) as data FROM `{tbl}` WHERE timefrom BETWEEN %s AND %s GROUP BY sign, timefrom ORDER BY timefrom", (start_date, end_date + " 23:59:59"))
            else:
                continue
            all_rows.extend(rows)
        except: pass
    return {"success": True, "data": all_rows, "count": len(all_rows)}
