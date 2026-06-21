"""
首页仪表盘 - 对应老系统 sub_home.html
数据源: servicedata (支路能耗), 递归聚合支路层级
规则: servicedata中有此sign(包含0) -> 电表存在 -> 用自己数据
      servicedata中无此sign -> 无此电表/虚拟表 -> 聚合子支路
"""
from fastapi import APIRouter, Depends, Query
from datetime import date, timedelta, datetime
from collections import defaultdict
from routers.auth import current_user
from database import db
from utils.helpers import energy_table, service_table, safe_float

router = APIRouter()

TYPE_MAP = {
    1: {"name": "电", "unit": "kWh", "unit_area": "kWh/㎡", "title": "【电】今日能耗", "ylabel": "用电量（kWh）"},
    2: {"name": "冷量", "unit": "GJ", "unit_area": "GJ/㎡", "title": "【冷量】今日能耗", "ylabel": "用冷量（GJ）"},
    3: {"name": "热量", "unit": "GJ", "unit_area": "GJ/㎡", "title": "【热量】今日能耗", "ylabel": "用热量（GJ）"},
    11: {"name": "水", "unit": "t", "unit_area": "t/㎡", "title": "【水】今日能耗", "ylabel": "用水量（t）"},
    13: {"name": "燃气", "unit": "m³", "unit_area": "m³/㎡", "title": "【燃气】今日能耗", "ylabel": "用气量（m³）"},
    6: {"name": "蒸汽", "unit": "t", "unit_area": "t/㎡", "title": "【蒸汽】今日能耗", "ylabel": "用蒸汽量（t）"},
}


def _resolve_funcid(energy_type: int):
    """根据能源类型查询 functiontype 表，确定 servicedata 中对应的 funcid。
    查不到则返回 None（无此能源类型的功能码）。
    """
    try:
        et_name = TYPE_MAP.get(energy_type, {}).get("name", "")
        if energy_type == 1:
            rows = db.query("constr_ems",
                "SELECT id, name FROM functiontype WHERE name LIKE '%有功%' AND physicalType=1 ORDER BY id")
        elif energy_type == 2:
            rows = db.query("constr_ems",
                "SELECT id, name FROM functiontype WHERE (name='冷量' OR name='冷') AND physicalType=2 ORDER BY id")
        elif energy_type == 3:
            rows = db.query("constr_ems",
                "SELECT id, name FROM functiontype WHERE (name='热量' OR name='热') AND physicalType=2 ORDER BY id")
        elif energy_type == 11:
            rows = db.query("constr_ems",
                "SELECT id, name FROM functiontype WHERE name='水' AND physicalType=2 ORDER BY id")
        else:
            rows = db.query("constr_ems",
                "SELECT id, name FROM functiontype WHERE name LIKE %s AND physicalType=2 ORDER BY id LIMIT 5",
                (f'%{et_name}%',))
        if not rows:
            return None
        for kw in ["总有功", "有功", "正向有功", "正向", "总"]:
            for r in rows:
                name = (r.get("name") or "")
                if kw in name:
                    return r["id"]
        return rows[0]["id"]
    except Exception:
        return None


def load_service_hierarchy(sign: str):
    vsvcs = db.query("constr_ems",
        "SELECT id, name, sign, ParentServiceId, MeterId, serviceType FROM v_service WHERE buildingSign=%s ORDER BY id",
        (sign,))
    svc_info = {}
    tree = {}
    roots = []
    for v in vsvcs:
        svc_info[v["id"]] = v
        pid = v.get("ParentServiceId") or 0
        tree.setdefault(pid, []).append(v)
        if not v.get("ParentServiceId"):
            roots.append(v)
    return svc_info, tree, roots


def load_sign_data(sign: str, today_val: str, today_ym: str, funcid: int = None):
    sign_data = defaultdict(lambda: defaultdict(float))
    for gran in [0]:
        try:
            table = service_table(today_ym, sign, gran)
            if funcid is not None:
                rows = db.query("constr_servicedata",
                    f"SELECT sign, timefrom, data FROM `{table}` WHERE timefrom BETWEEN %s AND %s AND funcid=%s ORDER BY timefrom",
                    (today_val, today_val + " 23:59:59", funcid))
            else:
                rows = db.query("constr_servicedata",
                    f"SELECT sign, timefrom, data FROM `{table}` WHERE timefrom BETWEEN %s AND %s ORDER BY timefrom",
                    (today_val, today_val + " 23:59:59"))
            if rows:
                break
        except:
            continue
    for r in rows:
        ts = str(r["timefrom"])[:16]
        sign_data[str(r["sign"])][ts] += float(r["data"] or 0)
    return sign_data


def get_service_energy(service_id: int, svc_info: dict, tree: dict, sign_data: dict, ts: str) -> float:
    """servicedata中有此sign(包含0)->电表存在->用自己。无此sign->聚合子支路"""
    svc = svc_info.get(service_id)
    if not svc:
        return 0.0
    meter_sign = str(svc["sign"])
    if meter_sign in sign_data:
        return sign_data.get(meter_sign, {}).get(ts, 0)
    # 有 MeterId 说明绑定了物理电表，不应聚合子支路
    if svc.get("MeterId"):
        return 0.0
    children = tree.get(service_id, [])
    if children:
        total = 0.0
        for child in children:
            total += get_service_energy(child["id"], svc_info, tree, sign_data, ts)
        return total
    return 0.0


def _fallback_energydata(sign, today_val, today_ym, building, building_area, tp, building_people=0):
    total_energy = 0.0
    max_power = 0.0
    chart_data = []
    current_time = ""
    for gran in [0]:
        try:
            rows = db.query("constr_energydata",
                f"SELECT energyid, timefrom, data FROM `{energy_table(today_ym, sign, 1, gran)}` WHERE timefrom BETWEEN %s AND %s AND energyid=1 ORDER BY timefrom",
                (today_val, today_val + " 23:59:59"))
            if not rows:
                continue
            for r in rows:
                val = safe_float(r["data"])
                tf = str(r["timefrom"])[:16]
                chart_data.append({"time": tf, "value": round(val, 4)})
                total_energy += val
                if val > max_power:
                    max_power = val
                    current_time = tf
            break
        except:
            continue
    energy_by_area = round(total_energy / building_area, 6) if building_area > 0 else 0
    total_price = round(total_energy * 0.8, 2)
    status = "异常"
    try:
        ym = date.today().strftime("%Y%m")
        tbl = f"bnse_originaldata.`{ym}_recorddata_{sign}`"
        thirty_min_ago = (datetime.now() - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
        row = db.query_one("constr_ems",
            f"SELECT COUNT(*) as cnt FROM {tbl} WHERE receivetime >= %s",
            (thirty_min_ago,))
        if row and row["cnt"] > 0:
            status = "正常"
    except:
        pass
    return {"success": True, "data": {
        "building": {"name": building["name"], "sign": building["sign"], "introduction": building.get("introduction") or "", "type": building.get("type") or "", "area": building_area, "people": building.get("people", 0)},
        "stats": {"energy_total": round(total_energy, 2), "energy_by_area": energy_by_area, "total_price": total_price, "power_max": round(max_power, 4), "current_time": current_time, "date": current_time[:10] if current_time else "", "time": current_time[11:] if len(current_time) > 11 else "", "status": status, "unit": tp["unit"], "unit_area": tp["unit_area"]},
        "chart": {"title": f"【{tp['name']}】今日能耗", "label": tp["ylabel"], "unit": tp["unit"], "data": chart_data},
        "energy_types": [{"id": k, "name": v["name"], "unit": v["unit"], "unit_area": v["unit_area"], "title": v["title"], "ylabel": v["ylabel"]} for k, v in TYPE_MAP.items()],
    }}



def load_service_meter_data(sign, today_val, today_ym, gran=0):
    """
    从 constr_servicedata 读取电表数据
    gran: 0=10分钟, 1=小时, 2=天
    查询原则：≤1小时用10分钟表，>1小时≤1天用小时表，>1天用天表
    """
    sd = {}
    try:
        tbl = service_table(today_ym, sign, gran)
        rows = db.query("constr_servicedata",
            "SELECT sign as meter_sign, timefrom, data FROM " + "`" + tbl + "`" +
            " WHERE timefrom BETWEEN %s AND %s ORDER BY timefrom",
            (today_val, today_val + " 23:59:59"))
        for r in rows:
            ms = r["meter_sign"]
            ts = str(r["timefrom"])[:16]
            if ms not in sd:
                sd[ms] = {}
            sd[ms][ts] = sd[ms].get(ts, 0) + safe_float(r["data"])
    except:
        pass
    return sd

def compute_node_energy(node_id, svc_info, tree, svc_to_meter, meter_data, ts, real_meters=None):
    """递归计算节点能耗：
       电表在 originaldata 中有数据则为实表，直接使用 servicedata 数据；
       无电表或电表无数据则为虚表，汇总子节点数据"""
    if real_meters is None:
        real_meters = set()
    meter_sign = svc_to_meter.get(node_id)
    # 实表 → 直接取 servicedata 数据（即使为0也不汇总子节点）
    if meter_sign and meter_sign in real_meters:
        return meter_data.get(meter_sign, {}).get(ts, 0.0)
    # 虚表 → 由下级子节点汇总
    children = tree.get(node_id, [])
    if not children:
        return 0.0
    total = 0.0
    for child in children:
        total += compute_node_energy(child["id"], svc_info, tree, svc_to_meter, meter_data, ts, real_meters)
    return total

@router.get("/homepage")
async def homepage(
    sign: str = Query(""),
    energy_type: int = Query(1),
    user: dict = Depends(current_user),
):
    if not sign:
        signroles = user.get("signroles", "")
        signs = [s.strip() for s in signroles.split(",") if s.strip()]
        if signs: sign = signs[0]
    if not sign:
        return {"success": False, "message": "无建筑权限"}

    tp = TYPE_MAP.get(energy_type, TYPE_MAP[1])

    building = db.query_one("constr_ems",
        "SELECT id, name, sign, introduction, type FROM building WHERE sign=%s", (sign,))
    if not building:
        return {"success": False, "message": "建筑不存在"}

    area_row = db.query_one("constr_ems",
        "SELECT SUM(value+0.0) as total FROM v_building WHERE sign=%s AND name='Area'", (sign,))
    building_area = safe_float(area_row["total"]) if area_row else 0
    people_row = db.query_one("constr_ems",
        "SELECT SUM(value+0.0) as total FROM v_building WHERE sign=%s AND name='People'", (sign,))
    building_people = safe_float(people_row["total"]) if people_row else 0
    building["people"] = building_people

    today_val = date.today().strftime("%Y-%m-%d")
    today_ym = date.today().strftime("%Y%m")

    svc_info, tree, roots = load_service_hierarchy(sign)
    if not roots:
        return _fallback_energydata(sign, today_val, today_ym, building, building_area, tp, building_people)

    # 构建电表 sign → service id 映射
    cascades = db.query("constr_ems",
        "SELECT sc.ServiceId, sc.MeterId, m.sign as meter_sign FROM servicecascade sc "
        "LEFT JOIN meter m ON sc.MeterId = m.id "
        "WHERE sc.ServiceId IN (SELECT id FROM service WHERE BuildingId=%s)",
        (building["id"],))
    svc_to_meter = {}
    for c in cascades:
        if c.get("meter_sign"):
            svc_to_meter[c["ServiceId"]] = c["meter_sign"]

    # 按能源类型分流：电用 servicedata，其他类型用 energydata
    all_times = set()
    time_values = {}
    today_start = datetime.strptime(today_val + " 00:00", "%Y-%m-%d %H:%M")

    if energy_type == 1:
        # 电：从 constr_servicedata 读取，按电表 sign 递归聚合
        # 查询 originaldata 确定实表
        real_meters = set()
        try:
            ym = date.today().strftime("%Y%m")
            tbl = f"bnse_originaldata.`{ym}_recorddata_{sign}`"
            rows = db.query("constr_ems", f"SELECT DISTINCT sign FROM {tbl}")
            for r in rows:
                real_meters.add(str(r["sign"]))
        except:
            pass
        meter_data = load_service_meter_data(sign, today_val, today_ym, gran=0)  # 首页只用 t0 表
        for md in meter_data.values():
            all_times.update(md.keys())
        sorted_times = sorted(all_times)
        for ts in sorted_times:
            v = 0.0
            for root in roots:
                v += compute_node_energy(root["id"], svc_info, tree, svc_to_meter, meter_data, ts, real_meters)
            time_values[ts] = round(v, 4)
    else:
        # 非电类型(水/冷量/热量/燃气/蒸汽)：使用 energydata
        funcid = _resolve_funcid(energy_type)
        sign_data = load_sign_data(sign, today_val, today_ym, funcid=funcid) if funcid else {}
        for sd in sign_data.values():
            all_times.update(sd.keys())
        sorted_times = sorted(all_times)
        for ts in sorted_times:
            v = 0.0
            for root in roots:
                v += get_service_energy(root["id"], svc_info, tree, sign_data, ts)
            time_values[ts] = round(v, 4)

    # 统计指标
    total_energy = 0.0
    max_power = 0.0
    current_time = ""
    for ts in sorted_times:
        v = time_values[ts]
        total_energy += v
        if v > max_power:
            max_power = v
            current_time = ts

    # 构建图表数据：按小时汇总（柱状图）
    chart_data = []
    for h in range(24):
        hour_label = f"{h:02d}:00"
        hour_total = 0.0
        for m in range(0, 60, 10):
            ts = (today_start + timedelta(hours=h, minutes=m)).strftime("%Y-%m-%d %H:%M")
            hour_total += time_values.get(ts, 0.0)
        chart_data.append({"time": hour_label, "value": round(hour_total, 4)})

    energy_by_area = round(total_energy / building_area, 6) if building_area > 0 else 0
    price_rate = {1: 0.8, 2: 10, 3: 10, 11: 4.5, 13: 3.5, 6: 5}
    total_price = round(total_energy * price_rate.get(energy_type, 0.8), 2)

    status = "异常"
    try:
        ym = date.today().strftime("%Y%m")
        tbl = f"bnse_originaldata.`{ym}_recorddata_{sign}`"
        thirty_min_ago = (datetime.now() - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
        row = db.query_one("constr_ems",
            f"SELECT COUNT(*) as cnt FROM {tbl} WHERE receivetime >= %s",
            (thirty_min_ago,))
        if row and row["cnt"] > 0:
            status = "正常"
    except:
        pass

        # 获取分项占比数据（仅限电类型有分项概念）
    cat_data = {}
    if energy_type == 1:
        try:
            cat_map = {11: "照明", 12: "动力", 13: "空调", 14: "其他"}
            for eid, ename in cat_map.items():
                total = 0.0
                for g in [0, 1, 2]:
                    try:
                        etbl = energy_table(today_ym, sign, 1, g)
                        row = db.query_one("constr_energydata",
                            f"SELECT SUM(data) as t FROM " + "`" + etbl + "`" + " WHERE energyid=%s AND timefrom BETWEEN %s AND %s",
                            (eid, today_val, today_val + " 23:59:59"))
                        if row and row.get("t") and float(row["t"]) > 0:
                            total = safe_float(row["t"])
                            break
                    except:
                        pass
                if total > 0:
                    cat_data[ename] = round(total, 2)
        except:
            pass
    return {
        "success": True,
        "data": {
            "building": {"name": building["name"], "sign": building["sign"], "introduction": building.get("introduction") or "", "type": building.get("type") or "", "area": building_area, "people": building.get("people", 0)},
            "stats": {"energy_total": round(total_energy, 2), "energy_by_area": energy_by_area, "total_price": total_price, "power_max": round(max_power, 4), "current_time": current_time, "date": current_time[:10] if current_time else "", "time": current_time[11:] if len(current_time) > 11 else "", "status": status, "unit": tp["unit"], "unit_area": tp["unit_area"]},
            "chart": {"title": f"【{tp['name']}】今日能耗", "label": tp["ylabel"], "unit": tp["unit"], "data": chart_data},
            "energy_types": [{"id": k, "name": v["name"], "unit": v["unit"], "unit_area": v["unit_area"], "title": v["title"], "ylabel": v["ylabel"]} for k, v in TYPE_MAP.items()],
            "cats": cat_data,
        },
    }
