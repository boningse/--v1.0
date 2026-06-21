# 能耗监测系统 - 数据库表结构文档

> 基于 `web.config` MySQL 连接字符串导出  
> 数据库服务器: `192.168.12.100:3306`  
> 用户: `bnse`  
> 导出日期: 2026-06-20

---

## 数据库概览

| 数据库 | 说明 | 表数量 | 命名规则 |
|--------|------|--------|---------|
| `bnse_ems` | 主数据库(配置/元数据) | 62 | 固定表名 |
| `bnse_energydata` | 分项能耗数据 | ~500+ | `{YYYYMM}_energydata_{sign}_e{et}_t{gran}` |
| `bnse_servicedata` | 支路能耗数据 | ~500+ | `{YYYYMM}_servicedata_{sign}_t{gran}` |
| `bnse_tenementdata` | 分户能耗数据 | ~500+ | `{YYYYMM}_tenementdata_{sign}_e{et}_t{gran}` |
| `bnse_meterdata` | 仪表原始数据 | ~500+ | `{YYYYMM}_meterdata_{sign}_t0` |
| `bnse_originaldata` | 原始记录数据 | ~500+ | `{YYYYMM}_recorddata_{sign}` |

---

## 一、bnse_ems（主配置库）

### 1.1 building — 建筑/楼宇

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| name | varchar(50) | | 建筑名称 |
| sign | varchar(50) | | 建筑编码(唯一标识) |
| introduction | varchar(500) | | 详细介绍 |
| briefIntroduction | varchar(500) | | 简介 |
| type | varchar(1) | | 建筑类型 |
| shortName | varchar(255) | | 简称 |
| remark | varchar(50) | | 备注 |

### 1.2 energyitem — 能源分项

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键(1=总用电,11=空调,12=动力,13=照明,14=特殊,15=误差等) |
| ParentId | int(11) | MUL | 父级ID(层级结构) |
| name | varchar(50) | | 分项名称 |
| introduction | varchar(500) | | 详细介绍 |
| briefIntroduction | varchar(500) | | 简介 |

### 1.3 energytype — 能源类型

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键(1=电,2=冷量,3=热量,11=水,12=燃气) |
| EnergyUnitId | int(11) | MUL | 能源单位ID |
| name | varchar(50) | | 类型名称 |

### 1.4 energyunit — 能源单位

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| name | varchar(50) | | 单位名称 |
| scalingRatio | float | | 换算比例 |
| showName | varchar(50) | | 显示名称 |
| showNameCN | varchar(50) | | 中文显示名 |
| feature | varchar(50) | | 特征 |
| introduction | varchar(500) | | 介绍 |

### 1.5 energyunitchange — 能源单位换算

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| EnergyUnitIdDown | int(11) | MUL | 下级单位 |
| EnergyUnitIdUp | int(11) | MUL | 上级单位 |
| scalingRatio | float | | 换算比例 |

### 1.6 buildingenergy — 建筑能耗表达式

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| EnergyTypeId | int(11) | PRI | 能源类型 |
| EnergyItemId | int(11) | PRI | 能源分项 |
| BuildingId | int(11) | PRI | 建筑ID |
| remark | varchar(50) | | 备注 |
| expression | mediumtext | | 能耗计算公式 |

### 1.7 buildingproperty — 建筑属性值

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| PropertyId | int(11) | PRI | 属性ID |
| BuildingId | int(11) | PRI | 建筑ID |
| value | mediumtext | | 属性值 |
| remark | varchar(50) | | 备注 |

### 1.8 buildingtype — 建筑类型

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| type | varchar(255) | PRI | 类型编码 |
| name | varchar(255) | | 类型名称 |

### 1.9 energyitemproperty — 分项属性

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| EnergyItemId | int(11) | PRI | 分项ID |
| PropertyId | int(11) | PRI | 属性ID |
| BuildingId | int(11) | PRI | 建筑ID |
| value | mediumtext | | 属性值 |
| remark | varchar(50) | | 备注 |

### 1.10 service — 支路

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| BuildingId | int(11) | MUL | 所属建筑ID |
| PowerFacilityId | int(11) | MUL | 所属供电设施ID |
| name | varchar(50) | | 支路名称 |
| switchType | int(11) | | 开关类型 |
| sign | varchar(50) | | 支路编码 |
| serviceType | int(11) | | 支路类型 |

### 1.11 servicecascade — 支路级联关系

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| SwitchGateId | int(11) | MUL | 开关网关ID |
| ServiceId | int(11) | MUL | 支路ID |
| MeterId | int(11) | MUL | 仪表ID |
| ParentServiceId | int(11) | MUL | 父支路ID |
| defaultSwitch | int(11) | | 默认开关状态 |
| lineNumber | varchar(50) | | 线路编号 |
| remark | varchar(50) | | 备注 |

### 1.12 powerfacility — 供电设施(变压器/配电柜)

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| BuildingId | int(11) | MUL | 所属建筑ID |
| ParentId | int(11) | MUL | 父设施ID |
| sign | varchar(50) | | 设施编码 |
| name | varchar(50) | | 设施名称 |
| type | int(11) | | 设施类型 |

### 1.13 equipment — 设备

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| ServiceId | int(11) | MUL | 所属支路ID |
| BuildingId | int(11) | MUL | 所属建筑ID |
| EnergyItemId | int(11) | MUL | 所属分项ID |
| PeriodicityId | int(11) | MUL | 周期ID |
| name | varchar(50) | | 设备名称 |
| ratingPower | float | | 额定功率 |
| sign | varchar(50) | | 设备编码 |

### 1.14 equipmentenergy — 设备能耗表达式

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| EnergyTypeId | int(11) | PRI | 能源类型 |
| EquipmentId | int(11) | PRI | 设备ID |
| remark | varchar(50) | | 备注 |
| expression | mediumtext | | 能耗计算公式 |

### 1.15 equipmentproperty — 设备属性

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| PropertyId | int(11) | PRI | 属性ID |
| EquipmentId | int(11) | PRI | 设备ID |
| value | mediumtext | | 属性值 |
| remark | varchar(50) | | 备注 |

### 1.16 equipmentperiodicityproperty — 设备周期属性

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| EquipmentId | int(11) | PRI | 设备ID |
| PeriodicityPropertyId | int(11) | PRI | 周期属性ID |
| value | varchar(500) | | 属性值 |

### 1.17 tenement — 分户

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| BuildingId | int(11) | MUL | 所属建筑ID |
| name | varchar(50) | | 分户名称 |
| sign | varchar(50) | | 分户编码 |

### 1.18 tenementrelation — 分户层级关系

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| TenementId | int(11) | MUL | 分户ID |
| ParentTenementId | int(11) | MUL | 父分户ID |
| remark | varchar(50) | | 备注 |

### 1.19 tenementenergy — 分户能耗表达式

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| EnergyTypeId | int(11) | PRI | 能源类型 |
| TenementId | int(11) | PRI | 分户ID |
| EnergyItemId | int(11) | PRI | 分项ID |
| remark | varchar(50) | | 备注 |
| expression | mediumtext | | 能耗计算公式 |

### 1.20 tenementequipment — 分户设备关联

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| TenementId | int(11) | PRI | 分户ID |
| EquipmentId | int(11) | PRI | 设备ID |
| remark | varchar(50) | | 备注 |

### 1.21 tenementproperty — 分户属性

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| PropertyId | int(11) | PRI | 属性ID |
| TenementId | int(11) | PRI | 分户ID |
| value | mediumtext | | 属性值 |
| remark | varchar(50) | | 备注 |

### 1.22 tenementservice — 分户支路关联

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| TenementId | int(11) | PRI | 分户ID |
| ServiceId | int(11) | PRI | 支路ID |
| remark | varchar(50) | | 备注 |

### 1.23 meter — 仪表

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| BuildingId | int(11) | MUL | 所属建筑ID |
| sign | varchar(50) | | 仪表编码 |
| rate | float | | 倍率 |
| ip | varchar(50) | | IP地址 |
| port | varchar(50) | | 端口 |
| gatewayversion | varchar(50) | | 网关版本 |
| gatewaycode | varchar(50) | | 网关编码 |
| address | varchar(50) | | 地址 |
| phaserate | float | | 相位倍率 |
| coilrate | float | | 线圈倍率 |
| meterClass | int(11) | | 仪表类别 |
| isComputer | int(11) | | 是否计算机(默认1) |

### 1.24 meterfunction — 仪表功能

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| FunctionId | int(11) | PRI | 功能ID |
| MeterId | int(11) | PRI | 仪表ID |
| remark | varchar(50) | | 备注 |

### 1.25 meterproperty — 仪表属性

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| PropertyId | int(11) | PRI | 属性ID |
| MeterId | int(11) | PRI | 仪表ID |
| value | mediumtext | | 属性值 |
| remark | varchar(50) | | 备注 |

### 1.26 meterfunctionproperty — 仪表功能属性

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| PropertyId | int(11) | PRI | 属性ID |
| FunctionId | int(11) | PRI | 功能ID |
| MeterId | int(11) | PRI | 仪表ID |
| value | mediumtext | | 属性值 |
| remark | varchar(50) | | 备注 |

### 1.27 meterfunctionlimitsetting — 仪表功能限值设置

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| LimitId | int(11) | MUL | 限值ID |
| BuildingSign | varchar(50) | | 建筑编码 |
| MeterSign | varchar(50) | | 仪表编码 |
| FunctionId | int(11) | | 功能ID |
| remark | varchar(50) | | 备注 |
| value | mediumtext | | 限值 |
| operateTime | datetime | | 操作时间 |
| username | varchar(50) | | 操作人 |

### 1.28 meterfunctionoperation — 仪表功能操作记录

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| BuildingSign | varchar(50) | | 建筑编码 |
| MeterSign | varchar(50) | | 仪表编码 |
| FunctionId | int(11) | | 功能ID |
| remark | varchar(50) | | 备注 |
| operate | int(11) | | 操作类型 |
| operateTime | datetime | | 操作时间 |

### 1.29 functiontype — 功能类型

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| name | varchar(50) | | 功能名称 |
| valueType | int(11) | | 值类型 |
| physicalType | int(11) | | 物理类型 |
| measure | varchar(50) | | 量纲 |
| rate | float | | 倍率 |
| remark | varchar(50) | | 备注 |

### 1.30 limitsetting — 限值设置模板

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| name | varchar(50) | | 模板名称 |
| type | int(11) | | 类型 |
| remark | varchar(50) | | 备注 |
| defaultValue | mediumtext | | 默认值 |

### 1.31 switchgate — 开关网关

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| MeterId | int(11) | MUL | 仪表ID |
| BuildingId | int(11) | MUL | 建筑ID |
| FunctionId | int(11) | MUL | 功能ID |
| sign | varchar(50) | | 网关编码 |

### 1.32 switchgatesetting — 开关网关设置

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| BuildingSign | varchar(50) | | 建筑编码 |
| SwitchGateSign | varchar(50) | | 开关网关编码 |
| remark | varchar(50) | | 备注 |
| value | mediumtext | | 设置值 |
| operateTime | datetime | | 操作时间 |
| username | varchar(50) | | 操作人 |

### 1.33 switchoperation — 开关操作记录

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| BuildingSign | varchar(50) | | 建筑编码 |
| SwitchGateSign | varchar(50) | | 开关网关编码 |
| operateTime | datetime | | 操作时间 |
| remark | varchar(50) | | 备注 |
| operate | int(11) | | 操作(0关/1开) |

### 1.34 powermap — 供电图

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| BuildingSign | varchar(50) | | 建筑编码 |
| name | varchar(50) | | 图名称 |
| content | mediumtext | | 图形内容 |

### 1.35 periodicity — 周期定义

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| name | varchar(50) | | 周期名称 |

### 1.36 periodicityproperty — 周期属性

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| PeriodicityId | int(11) | MUL | 周期ID |
| name | varchar(50) | | 属性名称 |

### 1.37 property — 属性定义

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| name | varchar(50) | | 属性名称(英文) |
| showName | varchar(50) | | 显示名称(中文) |
| entityType | varchar(50) | | 实体类型(building/equipment/meter等) |
| dataType | varchar(50) | | 数据类型 |

### 1.38 propertyvalue — 属性可选值

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| PropertyId | int(11) | MUL | 属性ID |
| sequence | int(11) | | 排序 |
| value | mediumtext | | 可选值 |

### 1.39 tb_user — 系统用户

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| useraccount | varchar(50) | PRI | 登录账号 |
| username | varchar(255) | | 用户姓名 |
| userpassword | varchar(50) | | 登录密码 |
| userroles | varchar(5000) | | 用户角色权限 |
| signroles | varchar(5000) | | 建筑编码权限(逗号分隔) |
| flag | int(1) | | 管理员标识(1=管理员,0=普通) |
| createdate | datetime | | 创建时间 |
| leftname | varchar(255) | | 左侧名称 |
| rightname | varchar(255) | | 右侧名称 |

### 1.40 systemconfig — 系统配置

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| useraccount | varchar(255) | PRI | 用户账号 |
| id | int(11) | | ID(默认0) |
| titleName | varchar(50) | | 系统标题 |
| titleText | text | | 标题文本 |

### 1.41 user — 用户(旧)

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| PermissionId | int(11) | MUL | 权限ID |
| name | varchar(50) | | 用户名 |
| password | varchar(50) | | 密码 |

### 1.42 userbuilding — 用户建筑关联

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| UserId | int(11) | MUL | 用户ID |
| BuildingSign | varchar(50) | | 建筑编码 |
| remark | varchar(50) | | 备注 |

### 1.43 permission — 权限定义

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| name | varchar(50) | | 权限名称 |

### 1.44 fatherbuilding — 父建筑

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI,auto_increment | 主键 |
| name | varchar(255) | | 名称 |
| location | mediumtext | | 位置 |

### 1.45 fathersonbuilding — 父子建筑关联

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI,auto_increment | 主键 |
| fid | int(11) | | 父建筑ID |
| sid | int(11) | | 子建筑ID |

### 1.46 excel — Excel报表模板

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI | 主键 |
| BuildingSign | varchar(50) | | 建筑编码 |
| name | varchar(50) | | 模板名称 |
| filename | varchar(500) | | 文件名 |
| timeType | varchar(50) | | 时间类型(day/month/year) |

### 1.47 exceptiondata — 异常数据记录

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| buildingId | varchar(50) | | 建筑ID |
| sign | varchar(50) | | 表号/编码 |
| funcid | int(11) | | 功能码 |
| startTime | datetime | | 开始时间 |
| startData | double | | 开始数据 |
| endTime | datetime | | 结束时间 |
| endData | double | | 结束数据 |
| describe | varchar(255) | | 异常描述 |
| DValue | double | | 差值 |

### 1.48 removeexceptiondata — 已处理异常数据

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(11) | PRI,auto_increment | 主键 |
| buildingSign | varchar(255) | | 建筑编码 |
| meterSign | varchar(255) | | 仪表编码 |
| funcid | int(11) | | 功能码 |
| data | double | | 数据 |

### 1.49 chinaworkday — 中国工作日

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| chinadate | datetime | PRI | 日期 |
| workday | int(11) | | 是否工作日 |

### 1.50 tb_operationparameterlist — 运行参数配置

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(255) | PRI,auto_increment | 序号 |
| name | varchar(255) | | 参数名称 |
| buildingname | varchar(255) | | 建筑名称 |
| sign | varchar(255) | | 建筑编码 |
| ptype | int(1) | | 参数类型(0=环境,1=无量纲,2=电,3=水,4=冷,5=热,6=蒸汽,7=天然气) |
| puint | varchar(255) | | 参数单位 |
| pformula | varchar(1000) | | 参数公式 |
| pdescription | varchar(2000) | | 参数描述 |
| createdate | datetime | | 创建时间 |

### 1.51 tb_webpath — Web路径配置

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| id | int(10) | PRI,auto_increment | 主键 |
| name | varchar(255) | | 路径名称 |
| url | varchar(255) | | 路径URL |
| type | int(1) | | 类型(0=下载,1=原路径,2=图片) |

### 1.52 uploadtime — 上传时间

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| buildingSign | varchar(50) | PRI | 建筑编码 |
| uploadTime | datetime | | 上传时间 |

### 1.53 transconf — 传输配置

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| meterid | int(11) | | 仪表ID |
| orifuncid | int(11) | | 原始功能ID |
| newfuncids | varchar(500) | | 新功能ID列表 |
| filename | varchar(500) | | 文件名 |
| cmd | varchar(500) | | 命令 |

### 1.54 test / testtt — 测试表

`test` 和 `testtt` 为测试用表，结构从略。

---

## 二、视图 (Views)

### 2.1 v_building — 建筑完整信息视图

关联 building + buildingproperty + property，提供建筑的所有属性信息。

| 关键字段 | 说明 |
|---------|------|
| buildid | 建筑ID |
| buildingname | 建筑名称 |
| sign | 建筑编码 |
| name | 属性名(如Area=面积) |
| showName | 属性显示名 |
| value | 属性值 |
| entityType | 实体类型 |
| dataType | 数据类型 |

### 2.2 v_service — 支路完整信息视图

关联 service + servicecascade，提供支路的级联和仪表信息。

| 关键字段 | 说明 |
|---------|------|
| id | 支路ID |
| name | 支路名称 |
| ParentServiceId | 父支路ID |
| MeterId | 仪表ID |
| sign | 支路编码 |
| buildingSign | 建筑编码 |

### 2.3 v_service1 — 支路简化视图

与 v_service 类似但不含 buildingSign 字段。

### 2.4 v_tenement — 分户能耗视图

关联 tenement + tenementenergy，提供分户的能耗表达式信息。

### 2.5 v_householdenergy — 分户能耗层级视图

| 关键字段 | 说明 |
|---------|------|
| sign | 建筑编码 |
| buildid | 建筑ID |
| TenementId | 分户ID |
| TenementName | 分户名称 |
| ParentTenementId | 父分户ID |

### 2.6 v_parentbuilding / v_parentbuilding1 — 父子建筑视图

提供 fatherbuilding + fathersonbuilding + building 的关联信息。

---

## 三、bnse_energydata（分项能耗数据）

### 3.1 表命名规则

```
{YYYYMM}_energydata_{buildingSign}_e{energyType}_t{granularity}
```

| 段 | 说明 | 示例值 |
|----|------|--------|
| YYYYMM | 年月 | 202606 |
| buildingSign | 建筑编码 | 3701122502 |
| energyType (e) | 能源类型 | 1=电, 2=冷量, 3=热量, 11=水, 12=燃气 |
| granularity (t) | 粒度 | 0=小时级, 1=日级, 2=月级 |

**示例**: `202606_energydata_3701122502_e1_t0` = 2026年6月 建筑3701122502 电能 小时级

### 3.2 通用表结构（所有粒度相同）

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| energyid | int(11) | PRI | 分项ID(来自 energyitem 表) |
| timefrom | datetime | PRI | 数据时间 |
| flagdata | int(11) | | 数据标志 |
| data | double | | 能耗数值(kWh/GJ/t/m³等) |

---

## 四、bnse_servicedata（支路能耗数据）

### 4.1 表命名规则

```
{YYYYMM}_servicedata_{buildingSign}_t{granularity}
```

### 4.2 通用表结构

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| sign | varchar(50) | PRI | 支路编码(来自 service 表) |
| funcid | int(11) | PRI | 功能ID |
| timefrom | datetime | PRI | 数据时间 |
| flagdata | int(11) | | 数据标志 |
| data | double | | 支路能耗数值 |

---

## 五、bnse_tenementdata（分户能耗数据）

### 5.1 表命名规则

```
{YYYYMM}_tenementdata_{buildingSign}_e{energyType}_t{granularity}
```

### 5.2 通用表结构

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| sign | varchar(50) | PRI | 分户编码(来自 tenement 表) |
| energyid | int(11) | PRI | 分项ID |
| timefrom | datetime | PRI | 数据时间 |
| flagdata | int(11) | | 数据标志 |
| data | double | | 分户能耗数值 |

---

## 六、bnse_meterdata（仪表原始数据）

### 6.1 表命名规则

```
{YYYYMM}_meterdata_{buildingSign}_t0
```

> 注意：仅存在小时级(t0)粒度

### 6.2 通用表结构

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| sign | varchar(50) | PRI | 仪表编码(来自 meter 表) |
| funcid | int(11) | PRI | 功能码(来自 functiontype 表) |
| receivetime | datetime | PRI | 接收时间 |
| flagdata | int(11) | | 数据标志 |
| data | double | | 仪表读数 |

---

## 七、bnse_originaldata（原始记录数据）

### 7.1 表命名规则

```
{YYYYMM}_recorddata_{buildingSign}
```

> 只有一个表，不区分粒度

### 7.2 通用表结构

| 字段 | 类型 | 键 | 说明 |
|------|------|-----|------|
| sign | varchar(50) | PRI | 编码 |
| funcid | int(11) | PRI | 功能码 |
| receivetime | datetime | PRI | 接收时间 |
| data | double | | 原始数据值 |
| virtual | tinyint(4) | | 是否虚拟(默认1) |

---

## 八、核心关系图

```
fatherbuilding (父建筑)
  └── fathersonbuilding
        └── building (子建筑/楼宇)
              ├── buildingproperty → property
              ├── buildingenergy → energyitem + energytype
              ├── powerfacility (供电设施: 变压器/配电柜)
              │     └── service (支路) → servicecascade → meter
              │           └── equipment (设备)
              │                 ├── equipmentproperty
              │                 └── equipmentenergy
              ├── tenement (分户)
              │     ├── tenementrelation (层级)
              │     ├── tenementenergy
              │     ├── tenementequipment
              │     └── tenementservice
              ├── meter (仪表) → meterfunction → functiontype
              └── excel (报表模板)

数据存储:
  energydata    ← energyitem (按分项)
  servicedata   ← service (按支路)
  tenementdata  ← tenement (按分户)
  meterdata     ← meter (按仪表)
  originaldata  ← 原始采集记录
```

---

## 九、能源类型对照

| energy_type_id | 名称 | 单位 | 表字段 |
|---------------|------|------|--------|
| 1 | 电 | kWh | e1 |
| 2 | 冷量 | GJ | e2 |
| 3 | 热量 | GJ | e3 |
| 11 | 水 | t(吨) | e11 |
| 12 | 燃气 | m³ | e12 |

## 十、数据粒度对照

| gran | 名称 | 表后缀 | 说明 |
|------|------|--------|------|
| 0 | 小时 | _t0 | 每小时一条 |
| 1 | 日 | _t1 | 每天一条 |
| 2 | 月/年 | _t2 | 每月一条 |

## 十一、分项ID层级

| id | name | ParentId | 层级 |
|----|------|----------|------|
| 1 | 建筑总用电 | NULL | 根 |
| 11 | 空调用电 | 1 | 一级分类 |
| 12 | 动力用电 | 1 | 一级分类 |
| 13 | 照明插座 | 1 | 一级分类 |
| 14 | 特殊用电 | 1 | 一级分类 |
| 15 | 误差 | 1 | 一级分类 |
| 16 | 水 | 1 | 一级分类 |
| 17 | 热 | 1 | 一级分类 |
| 18 | 冷量 | 1 | 一级分类 |
| 1101 | 冷热站 | 11 | 二级分组 |
| 1102 | 冷冻泵 | 1101 | 三级分项 |
| 1103 | 冷却泵 | 1101 | 三级分项 |
| ... | ... | ... | ... |
