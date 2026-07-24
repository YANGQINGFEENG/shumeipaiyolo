# 智慧农业物联网平台 - API 文档

## 更新日期：2026-07-24

---

## 目录

1. [基地管理API](#1-基地管理api)
2. [区域管理API](#2-区域管理api)
3. [传感器API](#3-传感器api)
4. [传感器类型API](#4-传感器类型api)
5. [执行器API](#5-执行器api)
6. [执行器类型API](#6-执行器类型api)
7. [设备网关API](#7-设备网关api)
8. [设备数据上报API](#8-设备数据上报api)
9. [报警系统API](#9-报警系统api)
10. [知识库API](#10-知识库api)
11. [提示词模板API](#11-提示词模板api)
12. [AI服务API](#12-ai服务api)
13. [错误处理](#13-错误处理)
14. [设备编号规则](#14-设备编号规则)

---

## 1. 基地管理API

### 1.1 获取基地列表

**接口地址**：`GET /api/farms`

**请求参数**：
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| status | string | 否 | 按状态筛选（active/inactive） |

**响应示例**：
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "北京智能温室基地",
      "code": "BJ-001",
      "address": "北京市昌平区",
      "area": 50,
      "farm_type": "greenhouse",
      "status": "active",
      "created_at": "2026-06-23T10:00:00Z"
    }
  ],
  "total": 1
}
```

### 1.2 获取基地详情

**接口地址**：`GET /api/farms/[id]`

**响应示例**：
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "北京智能温室基地",
    "zones": [...],
    "stats": {
      "zones": 3,
      "sensors": 10,
      "actuators": 5
    }
  }
}
```

### 1.3 创建基地

**接口地址**：`POST /api/farms`

**请求体**：
```json
{
  "name": "基地名称",
  "code": "BJ-002",
  "address": "地址",
  "area": 100,
  "farm_type": "mixed"
}
```

### 1.4 更新基地

**接口地址**：`PUT /api/farms/[id]`

### 1.5 删除基地

**接口地址**：`DELETE /api/farms/[id]`

---

## 2. 区域管理API

### 2.1 获取区域列表

**接口地址**：`GET /api/farms/[farmId]/zones`

### 2.2 创建区域

**接口地址**：`POST /api/farms/[farmId]/zones`

**请求体**：
```json
{
  "name": "1号温室",
  "code": "GH1",
  "zone_type": "greenhouse",
  "area": 10,
  "description": "区域描述"
}
```

### 2.3 更新区域

**接口地址**：`PUT /api/zones/[id]`

### 2.4 删除区域

**接口地址**：`DELETE /api/zones/[id]`

---

## 3. 传感器API

### 3.1 获取传感器列表

**接口地址**：`GET /api/sensors`

**请求参数**：
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| type | string | 否 | 按类型筛选（temperature/humidity/light等） |
| farm_id | number | 否 | 按基地筛选 |

**响应示例**：
```json
{
  "success": true,
  "data": [
    {
      "id": "T-001",
      "name": "温度传感器1",
      "type": "temperature",
      "type_name": "温度传感器",
      "unit": "°C",
      "location": "1号温室",
      "status": "online",
      "battery": 95,
      "farm_id": 1,
      "zone_id": 1,
      "last_update": "2026-06-23T15:30:00Z"
    }
  ],
  "total": 10
}
```

### 3.2 获取传感器历史数据

**接口地址**：`GET /api/sensors/[id]/data`

**请求参数**：
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| startTime | string | 否 | 开始时间（ISO 8601） |
| endTime | string | 否 | 结束时间（ISO 8601） |
| limit | number | 否 | 返回数量（默认100） |

### 3.3 上传传感器数据

**接口地址**：`POST /api/sensors/[id]/data`

**请求体**：
```json
{
  "value": 25.5
}
```

---

## 4. 传感器类型API

### 4.1 获取传感器类型列表

**接口地址**：`GET /api/sensor-types`

**响应示例**：
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "type": "temperature",
      "name": "空气温度",
      "unit": "°C",
      "created_at": "2026-06-23T10:00:00Z"
    },
    {
      "id": 2,
      "type": "humidity",
      "name": "空气湿度",
      "unit": "%",
      "created_at": "2026-06-23T10:00:00Z"
    }
  ],
  "total": 11
}
```

### 4.2 创建传感器类型

**接口地址**：`POST /api/sensor-types`

**请求体**：
```json
{
  "type": "soil_temperature",
  "name": "土壤温度",
  "unit": "°C",
  "description": "监测土壤温度"
}
```

### 4.3 删除传感器类型

**接口地址**：`DELETE /api/sensor-types/[id]`

**说明**：如果该类型下存在传感器，将返回400错误。

---

## 5. 执行器API

### 5.1 获取执行器列表

**接口地址**：`GET /api/actuators`

**请求参数**：
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| type | string | 否 | 按类型筛选（water_pump/fan/heater等） |
| farm_id | number | 否 | 按基地筛选 |

### 5.2 更新执行器状态

**接口地址**：`PATCH /api/actuators/[id]`

**请求体**：
```json
{
  "state": "on",
  "mode": "manual",
  "trigger_source": "user"
}
```

### 5.3 发送控制指令

**接口地址**：`POST /api/actuators/[id]/commands`

**请求体**：
```json
{
  "command": "on"
}
```

---

## 6. 执行器类型API

### 6.1 获取执行器类型列表

**接口地址**：`GET /api/actuator-types`

**响应示例**：
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "type": "water_pump",
      "name": "水泵",
      "description": "用于灌溉和排水控制",
      "created_at": "2026-06-23T10:00:00Z"
    },
    {
      "id": 2,
      "type": "fan",
      "name": "风扇",
      "description": "用于通风和降温",
      "created_at": "2026-06-23T10:00:00Z"
    }
  ],
  "total": 7
}
```

### 6.2 创建执行器类型

**接口地址**：`POST /api/actuator-types`

**请求体**：
```json
{
  "type": "valve",
  "name": "电磁阀",
  "description": "用于控制水流开关"
}
```

### 6.3 删除执行器类型

**接口地址**：`DELETE /api/actuator-types/[id]`

**说明**：如果该类型下存在执行器，将返回400错误。

---

## 7. 设备网关API

### 7.1 获取网关列表

**接口地址**：`GET /api/gateways`

**请求参数**：
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| farm_id | number | 否 | 按基地筛选 |

**响应示例**：
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "farm_id": 1,
      "name": "1号温室网关",
      "gateway_type": "lorawan_gateway",
      "ip_address": "192.168.1.100",
      "mac_address": "AA:BB:CC:DD:EE:FF",
      "protocol": "lorawan",
      "status": "online",
      "nodes": [
        {
          "id": 1,
          "node_id": "SM-1-AB34",
          "name": "土壤湿度传感器1",
          "node_type": "sensor",
          "sensor_type": "soil_moisture",
          "location": "1号温室入口",
          "status": "online",
          "last_update": "2026-06-23T15:30:00Z"
        }
      ]
    }
  ],
  "total": 1
}
```

### 7.2 创建网关

**接口地址**：`POST /api/gateways`

**请求体**：
```json
{
  "farm_id": 1,
  "name": "新网关",
  "gateway_type": "wifi_sensor",
  "ip_address": "192.168.1.101",
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "protocol": "http"
}
```

### 7.3 删除网关

**接口地址**：`DELETE /api/gateways/[id]`

---

## 8. 设备数据上报API

### 8.1 设备数据上报（统一协议）

**接口地址**：`POST /api/device/report`

**适用场景**：
- WiFi直连传感器独立上报
- 网关聚合多个设备节点上报
- 执行器状态上报

**请求体结构**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| gateway_id | number | ✅ | 网关ID（首次上报可为0） |
| farm_id | number | ✅ | 基地ID |
| nodes | array | ✅ | 设备节点数据数组 |

**nodes数组元素结构**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| node_id | string | ✅ | 设备节点唯一标识（MAC地址或序列号） |
| type | string | ✅ | 设备类型（见设备类型字典） |
| name | string | ❌ | 设备名称 |
| value | number | ❌ | 传感器数值（传感器类型必填） |
| unit | string | ❌ | 单位 |
| state | string | ❌ | 执行器状态：on/off（执行器类型必填） |
| mode | string | ❌ | 控制模式：auto/manual |
| location | string | ❌ | 安装位置 |
| firmware_version | string | ❌ | 固件版本号 |
| signal_strength | number | ❌ | 信号强度（0-100） |
| battery_level | number | ❌ | 电池电量（0-100） |

**场景1：传感器数据上报**

```json
{
  "gateway_id": 1,
  "farm_id": 1,
  "nodes": [
    {
      "node_id": "AA:BB:CC:DD:EE:01",
      "type": "temperature",
      "name": "空气温度传感器1",
      "value": 25.5,
      "unit": "°C",
      "location": "1号温室",
      "firmware_version": "v1.2.0",
      "signal_strength": 85,
      "battery_level": 92
    },
    {
      "node_id": "AA:BB:CC:DD:EE:02",
      "type": "soil_moisture",
      "name": "土壤湿度传感器1",
      "value": 65.2,
      "unit": "%",
      "location": "1号温室北侧"
    }
  ]
}
```

**场景2：执行器状态上报**

```json
{
  "gateway_id": 1,
  "farm_id": 1,
  "nodes": [
    {
      "node_id": "WP-001",
      "type": "water_pump",
      "name": "1号水泵",
      "state": "on",
      "mode": "auto",
      "location": "泵房A区"
    },
    {
      "node_id": "FN-001",
      "type": "fan",
      "name": "温室风扇1",
      "state": "off",
      "mode": "manual",
      "location": "1号温室"
    }
  ]
}
```

**场景3：网关聚合上报（混合传感器和执行器）**

```json
{
  "gateway_id": 1,
  "farm_id": 1,
  "nodes": [
    {
      "node_id": "sensor_001",
      "type": "temperature",
      "value": 24.5,
      "unit": "°C"
    },
    {
      "node_id": "sensor_002",
      "type": "humidity",
      "value": 65.0,
      "unit": "%"
    },
    {
      "node_id": "actuator_001",
      "type": "water_pump",
      "state": "on",
      "mode": "auto"
    }
  ]
}
```

**响应示例**：
```json
{
  "success": true,
  "message": "数据上报成功",
  "processed_nodes": [
    {
      "node_id": "AA:BB:CC:DD:EE:01",
      "type": "temperature",
      "device_id": "T-1-01",
      "action": "created"
    },
    {
      "node_id": "AA:BB:CC:DD:EE:02",
      "type": "soil_moisture",
      "device_id": "SM-1-02",
      "action": "updated"
    }
  ],
  "gateway_id": 1
}
```

**自动处理逻辑**：
1. **设备类型识别**：根据`type`字段自动识别设备类别（传感器/执行器）
2. **设备自动分类**：传感器数据同步到`sensors`表，执行器数据同步到`actuators`表
3. **设备自动注册**：首次上报的设备自动创建记录
4. **ID自动生成**：统一生成格式 `{PREFIX}-{gatewayId}-{nodeId}`
5. **类型自动创建**：新设备类型自动注册到`sensor_types`或`actuator_types`表

**支持的设备类型**：

| 类型标识 | 名称 | 类别 | 单位 |
|----------|------|------|------|
| temperature | 空气温度 | 传感器 | °C |
| humidity | 空气湿度 | 传感器 | % |
| light | 光照强度 | 传感器 | Lux |
| soil_moisture | 土壤湿度 | 传感器 | % |
| soil_temperature | 土壤温度 | 传感器 | °C |
| ec | 土壤电导率 | 传感器 | μS/cm |
| ph | 土壤pH值 | 传感器 | pH |
| co2 | CO2浓度 | 传感器 | ppm |
| wind_speed | 风速 | 传感器 | m/s |
| rainfall | 降雨量 | 传感器 | mm |
| battery | 电池电压 | 传感器 | V |
| water_pump | 水泵 | 执行器 | - |
| fan | 风扇 | 执行器 | - |
| heater | 加热器 | 执行器 | - |
| valve | 电磁阀 | 执行器 | - |
| light_supplement | 补光灯 | 执行器 | - |
| irrigation | 滴灌系统 | 执行器 | - |
| ventilation | 通风机 | 执行器 | - |

---

## 9. 报警系统API

### 9.1 获取报警规则

**接口地址**：`GET /api/alarms/rules`

### 9.2 创建报警规则

**接口地址**：`POST /api/alarms/rules`

**请求体**：
```json
{
  "name": "温度过高报警",
  "sensor_type": "temperature",
  "condition_type": "above",
  "max_value": 35,
  "severity": "critical"
}
```

### 9.3 获取报警记录

**接口地址**：`GET /api/alarms/records`

**请求参数**：
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| status | string | 否 | 按状态筛选（active/acknowledged/resolved） |
| severity | string | 否 | 按严重程度筛选（info/warning/critical） |
| page | number | 否 | 页码（默认1） |
| pageSize | number | 否 | 每页数量（默认20） |

### 9.4 更新报警状态

**接口地址**：`PATCH /api/alarms/records`

**请求体**：
```json
{
  "id": 1,
  "status": "acknowledged",
  "acknowledged_by": "user"
}
```

---

## 10. 知识库API

### 10.1 获取知识列表

**接口地址**：`GET /api/knowledge`

**请求参数**：
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| page | number | 否 | 页码（默认1） |
| pageSize | number | 否 | 每页数量（默认20） |
| category | string | 否 | 按分类筛选 |
| search | string | 否 | 搜索关键词 |

### 10.2 智能添加知识

**接口地址**：`POST /api/knowledge/smart-add`

**请求体**：
```json
{
  "raw_text": "番茄晚疫病症状：叶片出现水渍状暗绿色斑点..."
}
```

**响应示例**：
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "structured": {
          "title": "番茄晚疫病症状与防治",
          "content": "...",
          "category": "病虫害防治",
          "tags": "番茄,晚疫病"
        },
        "conflicts": [],
        "has_conflicts": false
      }
    ],
    "total": 1,
    "has_any_conflicts": false
  }
}
```

### 10.3 知识对比分析

**接口地址**：`POST /api/knowledge/compare`

**请求体**：
```json
{
  "ids": [1, 2, 3]
}
```

**响应示例**：
```json
{
  "success": true,
  "data": {
    "contradictions": [
      {
        "item1": {"id": 1, "title": "知识A"},
        "item2": {"id": 2, "title": "知识B"},
        "type": "direct",
        "description": "直接矛盾",
        "detail1": "观点A",
        "detail2": "观点B",
        "severity": "high",
        "suggestion": "存在直接矛盾，请核实"
      }
    ],
    "stats": {
      "contradiction_count": 1,
      "has_contradictions": true
    }
  }
}
```

---

## 11. 提示词模板API

### 11.1 获取模板列表

**接口地址**：`GET /api/prompts`

### 11.2 渲染模板

**接口地址**：`POST /api/prompts/render`

**请求体**：
```json
{
  "template_id": 1,
  "variables": {
    "sensor_data": "温度: 25°C",
    "detection_results": "未检测到病虫害"
  }
}
```

---

## 12. AI服务API

### 12.1 AI聊天

**接口地址**：`POST /api/ai/chat`

### 12.2 AI诊断

**接口地址**：`POST /api/ai/diagnosis`

### 12.3 图片识别

**接口地址**：`POST /api/ai/image-recognition`

### 12.4 获取模型列表

**接口地址**：`GET /api/ai/models`

---

## 13. 错误处理

### 13.1 错误响应格式

```json
{
  "success": false,
  "error": "错误描述",
  "details": "详细错误信息"
}
```

### 13.2 常见错误码

| HTTP状态码 | 说明 |
|-----------|------|
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 14. 设备编号规则

### 14.1 统一设备ID格式

系统采用统一的设备编号规则，格式如下：

```
{PREFIX}-{gatewayId}-{nodeId}
```

**说明**：
- **PREFIX**：设备类型前缀（2-3位大写字母）
- **gatewayId**：网关ID（数字）
- **nodeId**：节点ID（截取后4位，大写）

**设备类型前缀映射**：

| 前缀 | 设备类型 | 示例 |
|------|----------|------|
| T | temperature（空气温度） | T-1-AB34 |
| H | humidity（空气湿度） | H-1-CD56 |
| L | light（光照强度） | L-1-EF78 |
| SM | soil_moisture（土壤湿度） | SM-1-GH90 |
| ST | soil_temperature（土壤温度） | ST-1-IJ12 |
| EC | ec（土壤电导率） | EC-1-KL34 |
| PH | ph（土壤pH值） | PH-1-MN56 |
| CO | co2（CO2浓度） | CO-1-OP78 |
| WS | wind_speed（风速） | WS-1-QR90 |
| RF | rainfall（降雨量） | RF-1-ST12 |
| B | battery（电池电压） | B-1-UV34 |
| WP | water_pump（水泵） | WP-1-WX56 |
| FN | fan（风扇） | FN-1-YZ78 |
| HT | heater（加热器） | HT-1-AB90 |
| VL | valve（电磁阀） | VL-1-CD12 |
| LS | light_supplement（补光灯） | LS-1-EF34 |
| IR | irrigation（滴灌系统） | IR-1-GH56 |
| VT | ventilation（通风机） | VT-1-IJ78 |

### 14.2 旧格式兼容

系统兼容以下旧格式，自动转换为新格式：
- 手动注册格式：`T-001` → 转换为 `T-{gatewayId}-001`
- 自动发现格式：`DN-gatewayId-nodeId` → 转换为 `{PREFIX}-gatewayId-nodeId`

---

**文档版本**：v2.1  
**最后更新**：2026-07-24  
**新增内容**：设备自动分类、统一上报协议、传感器/执行器类型API、统一设备编号规则