"""
能耗监测子系统 API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, dashboard, energy, tenement, equipment, monitor, report

app = FastAPI(title="能耗监测子系统", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["仪表盘"])
app.include_router(energy.router, prefix="/api/energy", tags=["分项能耗"])
app.include_router(tenement.router, prefix="/api/tenement", tags=["分户能耗"])
app.include_router(equipment.router, prefix="/api/equipment", tags=["设备能耗"])
app.include_router(monitor.router, prefix="/api/monitor", tags=["监测数据"])
app.include_router(report.router, prefix="/api/report", tags=["报表打印"])

@app.get("/api/health")
def health(): return {"status": "ok"}
