"""
登录认证 - 对应老系统 H/UsersHandler.ashx?M=4
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import db
from utils.auth import password_ok, create_access_token, decode_access_token

router = APIRouter()
security = HTTPBearer()

def current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    payload = decode_access_token(credentials.credentials)
    if not payload: raise HTTPException(401)
    return payload

from pydantic import BaseModel

class LoginRequest(BaseModel):
    useraccount: str = ""
    userpassword: str = ""

@router.post("/login")
async def login(data: LoginRequest):
    acc = data.useraccount
    pwd = data.userpassword

    # 先验证密码规则
    if not password_ok(acc, pwd):
        return {"success": False, "message": "密码错误"}

    # 查数据库
    user = db.query_one("constr_ems", "SELECT username, useraccount, userroles, signroles, flag, createdate FROM tb_user WHERE useraccount=%s", (acc,))

    if not user:
        # 不在 tb_user 表中，但密码验证通过了（如 zhyk）
        # 尝试用 useraccount 匹配 building sign
        building = db.query_one("constr_ems", "SELECT sign, name FROM building WHERE sign LIKE %s", (f"%{acc}%",))
        if not building:
            # 尝试用 useraccount+% 匹配 building sign
            building = db.query_one("constr_ems", "SELECT sign, name FROM building WHERE sign LIKE %s", (f"%{acc}",))

        if not building:
            # 最后尝试: 用 building 表里的 name 模糊匹配 useraccount
            # 通过 useraccount 直接查询 sign （支持多建筑映射）
            building = db.query_one("constr_ems",
                "SELECT b.sign, b.name FROM building b JOIN user u ON u.sign = b.sign WHERE u.useraccount=%s",
                (acc,))

        if not building:
            return {"success": False, "message": "账号不存在"}

        user = {
            "username": building["name"],
            "useraccount": acc,
            "userroles": building["name"],
            "signroles": building["sign"],
            "flag": 0,
            "createdate": None,
        }

    token = create_access_token({"useraccount": user["useraccount"], "username": user["username"] or user["useraccount"], "signroles": user.get("signroles") or ""})

    return {
        "success": True,
        "token": token,
        "user": {
            "username": user["username"],
            "useraccount": user["useraccount"],
            "userroles": user.get("userroles"),
            "signroles": user.get("signroles"),
            "flag": user.get("flag"),
            "createdate": str(user["createdate"]) if user.get("createdate") else None,
        }
    }


@router.get("/buildings")
async def get_buildings(user: dict = Depends(current_user)):
    """返回用户可访问的建筑列表。admin/super 返回全部，其它返回自己的"""
    account = user.get("useraccount", "")
    is_admin = account in ("admin", "super", "管理员", "超级管理员")
    if is_admin:
        buildings = db.query("constr_ems", "SELECT sign, name FROM building ORDER BY name")
    else:
        signs = [s.strip() for s in user.get("signroles", "").split(",") if s.strip()]
        if not signs:
            return {"success": False, "message": "无建筑权限"}
        buildings = db.query("constr_ems", "SELECT sign, name FROM building WHERE sign=%s", (signs[0],))
    return {"success": True, "data": buildings, "is_admin": is_admin}

@router.get("/my_building")
async def my_building(user: dict = Depends(current_user)):
    """获取当前用户的子系统建筑"""
    signroles = user.get("signroles", "")
    signs = [s.strip() for s in signroles.split(",") if s.strip()]
    if not signs:
        return {"success": False, "message": "无建筑权限"}

    b = db.query_one("constr_ems", "SELECT id, name, sign, type FROM building WHERE sign=%s", (signs[0],))
    if not b:
        return {"success": False}

    # 获取建筑属性(面积等)
    props = db.query("constr_ems", "SELECT name, showName, value FROM v_building WHERE sign=%s", (signs[0],))

    return {"success": True, "building": b, "properties": props}

@router.get("/title")
async def get_title(user: dict = Depends(current_user)):
    """获取子系统标题 - 对应 M=25"""
    signroles = user.get("signroles", "")
    signs = [s.strip() for s in signroles.split(",") if s.strip()]
    if not signs: return {"success": False}

    row = db.query_one("constr_ems", "SELECT titleName, titleText FROM systemconfig WHERE useraccount=%s LIMIT 1", (user["useraccount"],))
    if not row:
        row = db.query_one("constr_ems", "SELECT titleName FROM systemconfig WHERE useraccount='admin' LIMIT 1")

    b = db.query_one("constr_ems", "SELECT name FROM building WHERE sign=%s", (signs[0],))

    return {"success": True, "title": row["titleName"] if row else "能耗监测系统", "building_name": b["name"] if b else ""}
