# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Rice Growth & Methane Emission Simulation System** (水稻生长与CH4排放模拟系统) that couples the Ricegrow crop model with CH4 emission modeling. The system provides a web interface for simulating rice growth and predicting methane emissions based on cultivar selection, water management, soil parameters, and organic matter inputs.

**Live URL**: https://rice.mayuanyuan.top

## Architecture

### Core Scientific Models

- **`Ricegrow_py_v1_0.py`** - The main rice growth model (Ricegrow)
  - `CalFun()` - Main simulation function returning growth sequences (biomass, LAI, yield, N uptake)
  - `GetTmax()`, `GetTmin()`, `CalT24H()` - Temperature data processing
  - `GetCultivarParams()` - Extracts cultivar-specific parameters

- **`RG2CH4.py`** - CH4 emission coupling model
  - `CH4Flux_coupled()` - Main function coupling rice growth with CH4 emission prediction
  - Takes water regime, soil sand content, organic matter (OMS/OMN), temperature, and biomass inputs
  - Returns daily CH4 emission data

### Web Interface

- **`app.py`** - Streamlit application with modern CSS-based UI
  - Implements variety selection, water management, and soil parameter configuration
  - Uses session state to persist user inputs across re-runs
  - Generates interactive Plotly visualizations

## Common Commands

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (development mode)
streamlit run app.py

# View logs
tail -f /tmp/streamlit.log /tmp/tunnel.log
```

### Production Deployment (via Makefile)

```bash
# First-time deployment (sets up Cloudflare tunnel)
make deploy

# Start services
make start

# Stop services
make stop

# Restart services
make restart

# Check service status
make status

# View logs
make logs        # All logs
make logs-app    # App only
make logs-tunnel # Tunnel only

# Clean temporary files
make clean
```

### Service Management Scripts

```bash
# Quick start (for already-configured environments)
./quick-start.sh

# Stop all services
./stop.sh

# Full deployment (includes cloudflared setup)
./deploy-local.sh
```

## Data Files (Required)

The system requires these CSV files in the project directory (encoding: GBK):

| Filename | Purpose |
|----------|---------|
| `调参数据.csv` | Field parameters (latitude, sowing/transplant dates, site) |
| `气象数据.csv` | Weather data (date, Tmax, Tmin, radiation, precipitation) |
| `土壤数据.csv` | Soil properties |
| `秸秆数据.csv` | Residue/crop residue inputs |
| `管理数据_多种方案.csv` | Management practices (planting dates, density) |
| `施肥数据.csv` | Fertilizer application data |
| `品种参数.csv` | Cultivar-specific parameters (PS, TS, IE, PHI, PF, etc.) |

Users can upload custom files via the interface, which are saved to `uploaded_files/` directory and take precedence over defaults.

## File Encoding Convention

**Critical**: All model functions expect CSV files with **GBK encoding**. When uploading custom files, the app converts them to GBK automatically.

## Water Management Modes

The system supports 5 irrigation regimes (affects CH4 emissions):

1. **Continuous Flooding** (模式1) - Highest CH4
2. **Intermittent Irrigation** (模式2) - Medium-high CH4
3. **Wet Irrigation** (模式3) - Medium-low CH4
4. **Controlled Irrigation** (模式4) - Medium CH4
5. **Alternate Wet-Dry** (模式5) - Lowest CH4, highest efficiency

## Key Session State Variables

- `selected_varieties` - List of selected rice cultivars
- `water_regime` - Water management mode (1-5)
- `sand_value` - Soil sand percentage (affects CH4)
- `oms`, `omn` - Organic matter inputs (slow/fast decomposition)
- `use_custom_files` - Whether to use uploaded files
- `run_simulation` - Triggers simulation when True

## Simulation Flow

1. User selects varieties (1-8 recommended for performance)
2. User configures water regime, soil type, organic matter
3. On "Run Simulation", for each variety:
   - Create temporary cultivar CSV file
   - Call `CalFun()` to run Ricegrow model
   - Extract temperature data from weather file
   - Call `CH4Flux_coupled()` with growth outputs
   - Clean up temp files
4. Display results via `display_simulation_results()`

## Deployment Architecture

- **Frontend**: Streamlit (port 8501)
- **Tunnel**: Cloudflare Tunnel (`cloudflared`) exposing localhost:8501 to public domain
- **Domain**: `rice.mayuanyuan.top` (CNAME to tunnel ID)
- **Process Management**: PID files stored in `/tmp/rice-streamlit.pid` and `/tmp/rice-tunnel.pid`

## Design System (CSS)

The app uses a custom modern green theme with CSS variables:
- Primary green: `#10B981` (Emerald 500)
- Accent colors: Blue `#3B82F6`, Purple `#8B5CF6`, Orange `#F59E0B`
- Gradient backgrounds with texture overlays
- Card-based layouts with hover effects and shadows
- Responsive design with mobile breakpoints at 768px

See `DESIGN_DOCUMENTATION.md` for full design specifications.

## Troubleshooting

**Port 8501 occupied**: Kill existing process with `kill $(lsof -t -i:8501)`

**Encoding errors**: Ensure all CSV files use GBK encoding for model functions

**Cloudflare tunnel issues**: Check `~/.cloudflared/` for config and logs

**Missing data files**: The app validates file presence on startup and shows status in sidebar

## RiceGrow 批处理模板格式对照

### 模板文件位置
原始 RiceGrow 软件版本的批处理模板位于：`/Users/mayuanyuan/Desktop/R_C_N/BatchTemplate/`

### 文件映射关系

| RiceGrow 模板文件 | 本系统对应文件 | 说明 |
|------------------|---------------|------|
| `cultivar.csv` | `data/品种参数.csv` | 品种遗传参数（PS, TS, IE, PHI等） |
| `fertilizer.csv` | `施肥数据.csv` | 肥料施用数据 |
| `irrigation.csv` | *(嵌入在管理数据中)* | 灌溉模式（1-5） |
| `planting.csv` | `管理数据_多种方案.csv` | 播种/移栽日期 |
| `residue.csv` | `秸秆数据.csv` | 秸秆/有机物输入 |
| `soil.csv` | `土壤数据.csv` | 土壤理化性质 |
| `stressfactor.csv` | *(未使用)* | 胁迫开关（可选） |
| `treatment.csv` | *(动态生成)* | 处理组合矩阵 |
| `weather.csv` | `气象数据.csv` | 气象数据元信息 |
| `Weather/站点.csv` | `气象数据.csv` | 逐日气象数据 |

### 主要格式差异

**1. 气象数据结构**
```
模板格式：
  - weather.csv：站点元信息（经纬度、年份范围）
  - Weather/JSYX.csv：逐日数据（日期、Tmax、Tmin、降水、辐射）

本系统格式：
  - 气象数据.csv：包含日期、Tmax、Tmin、辐射、降水量的单一文件
```

**2. 灌溉管理**
```
模板格式：irrigation.csv 单独定义水管理模式（1-5）
本系统格式：通过 UI 选择或嵌入在管理数据中
```

**3. 处理组合**
```
模板格式：treatment.csv 定义所有处理组合（处理号→品种号+播种号+施肥号等）
本系统格式：用户动态选择品种，系统自动生成组合
```

### 灌溉模式说明（irrigation.csv）

| 模式代码 | 英文名称 | 中文名称 | CH4排放 |
|---------|---------|---------|---------|
| 1 | Continuous Flooding | 淹水灌溉 | 最高 |
| 2 | Intermittent Irrigation | 间歇灌溉 | 中高 |
| 3 | Wet Irrigation | 湿润灌溉 | 中低 |
| 4 | Controlled Irrigation | 控制灌溉 | 中等 |
| 5 | Alternate Wet-Dry | 干湿交替 | 最低 |

### 从模板转换数据

如需使用 RiceGrow 模板数据：

```bash
# 复制并重命名模板文件
cp BatchTemplate/cultivar.csv data/品种参数.csv
cp BatchTemplate/fertilizer.csv 施肥数据.csv
cp BatchTemplate/soil.csv 土壤数据.csv
cp BatchTemplate/residue.csv 秸秆数据.csv

# 气象数据需要合并 weather.csv 和 Weather/站点.csv
# 播种数据需要将 planting.csv 转换为 管理数据_多种方案.csv 格式
```

### 批处理模板的 Weather 目录结构

```
BatchTemplate/Weather/
└── JSYX.csv          # 站点代码.csv
    格式：站代码,年/月/日,Tmax,Tmin,降水时数,降水量,太阳辐射
```

### 关键参数对照

**品种参数 (cultivar.csv → 品种参数.csv)**
- PS：感光性
- TS：感温性
- IE：基本灌浆期
- PHI：收获指数
- PF：光合转化效率
- 其他20+品种遗传参数

**施肥数据 (fertilizer.csv)**
- 施肥日期、施肥类型、施用量（kg/ha）
- 施肥方式：基肥/追肥
- 各养分含量（N、P、K等）

**土壤数据 (soil.csv)**
- 分层深度（cm）
- pH值、有机质、全氮、有效磷、速效钾
- 容重、孔隙度等物理性质

## RiceGrow 模板数据转换详细指南

### 数据结构详细对比

#### 1. 品种参数 (cultivar.csv → data/品种参数.csv)

**RiceGrow 模板列名：**
```
序号, 描述, 品种名称, 温度敏感性(TS), 光敏感性(PS), 灌浆因子, 基本早熟性,
伸长节间数, 品种最适温度(TO), 千粒重, 品种分蘖能力, 总叶龄, 收获指数(PHI),
LAI相对生长速率, 最大光合速率, 生理影响因子, 籽粒蛋白质含量, 生长呼吸系数,
单位根长的N潜在吸收速率, 单籽粒潜在累积速率, 高温敏感参数, 比叶面积, 消光系数因子
```

**本系统列名（英文）：**
```
PZ, PS, TS, TO, IE, HF, FDF, PHI, SLAc, PF, AMX, KF, TGW, RGC, LRS, TLN,
EIN, TA, SGP, PC, RAR
```

**字段映射：**
| 模板字段 | 本系统字段 | 说明 |
|---------|-----------|------|
| 品种名称 | PZ | 品种代号 |
| 光敏感性 | PS | Photosensitivity |
| 温度敏感性 | TS | Temperature sensitivity |
| 品种最适温度 | TO | Optimum temperature |
| 基本早熟性 | IE | Index of earliness |
| 灌浆因子 | FDF | Filling duration factor |
| 收获指数 | PHI | Harvest index |
| 千粒重 | TGW | Thousand grain weight |
| 总叶龄 | TLN | Total leaf number |
| 比叶面积 | SLAc | Specific leaf area |

#### 2. 气象数据 (weather.csv + Weather/站点.csv → data/气象数据.csv)

**RiceGrow 模板结构：**
```
weather.csv（站点元信息）:
  序号, 描述, 站点名称, 站点编号, 经度, 纬度, 海拔, CO2浓度, 起始年, 结束年

Weather/JSYX.csv（逐日数据）:
  站代码, 日期, Tmax, Tmin, 降水时数, 降水量, 太阳辐射
```

**本系统结构（合并后）：**
```
Stationno, Jour, Tmax, Tmin, RAIN, SRAD, CO2
```

**转换要点：**
- 模板的"降水时数"字段在本系统中未使用，可忽略
- 模板日期格式：`1980/1/1` → 本系统：`1990/1/1`
- CO2浓度从 weather.csv 读取并填充到每一行

#### 3. 土壤数据 (soil.csv → data/土壤数据.csv)

**RiceGrow 模板列名：**
```
序号, 描述, 经度, 纬度, 位置, 土壤编号, 土壤质地, 土壤矿化率, 土壤临界氮浓度
+ 各层数据: 各层深度, pH, 有机质, 全氮, 速效氮, 有效磷, 全磷, 速效钾, 全钾
+ 物理性质: 容重, 黏粒, 实际含水率, 田间持水量, 萎凋点, 饱和含水量, 饱和导水率
```

**本系统列名（英文）：**
```
pH, depth, thickness, bulkWeight, clayParticle, actualWater, fieldCapacity,
wiltingPoint, fieldSaturation, organicMatter, totalNitrogen, nitrateNitrogen,
ammoniaNitrogen, fastAvailablePhosphorus, totalPhosphorus, fastAvailableK,
slowAvailableK, caco3, soilTexture, soilMineRate, soilNConcentration
```

**字段映射：**
| 模板字段 | 本系统字段 | 说明 |
|---------|-----------|------|
| 各层深度 | depth | 土层深度 |
| pH值 | pH | - |
| 有机质含量 | organicMatter | g/kg |
| 全氮 | totalNitrogen | g/kg |
| 速效氮(硝态) | nitrateNitrogen | mg/kg |
| 速效氮(铵态) | ammoniaNitrogen | mg/kg |
| 有效磷 | fastAvailablePhosphorus | mg/kg |
| 速效钾 | fastAvailableK | mg/kg |
| 土壤质地 | soilTexture | 中壤土/砂土等 |
| 土壤矿化率 | soilMineRate | - |
| 土壤临界氮浓度 | soilNConcentration | - |
| 容重 | bulkWeight | g/cm³ |
| 黏粒含量 | clayParticle | - |
| 田间持水量 | fieldCapacity | - |
| 萎凋点 | wiltingPoint | - |

#### 4. 施肥数据 (fertilizer.csv → data/施肥数据.csv)

**RiceGrow 模板列名：**
```
序号, 日期, 施肥类型, 施肥量, 施肥方式, 氮总量, 磷总量, 钾总量,
铵态氮量, 硝态氮量, 酰胺态氮量
```

**本系统列名（英文）：**
```
type, methodName, DOY, nAmount, pAmount, kAmount,
NO3Amount, NH4Amount, UREAAmount
```

**字段映射：**
| 模板字段 | 本系统字段 | 说明 |
|---------|-----------|------|
| 施肥类型 | type | 尿素/复合肥等 |
| 施肥方式 | methodName | 撒施/沟施等 |
| 日期 | DOY | 需转换为年积日(Day of Year) |
| 氮总量 | nAmount | kg/ha |
| 磷总量 | pAmount | kg/ha |
| 钾总量 | kAmount | kg/ha |
| 硝态氮量 | NO3Amount | kg/ha |
| 铵态氮量 | NH4Amount | kg/ha |
| 酰胺态氮量 | UREAAmount | kg/ha |

**日期转换：**
```
模板: 2013/6/19 → 需计算为年积日 → DOY = 170
```

#### 5. 秸秆数据 (residue.csv → data/秸秆数据.csv)

**RiceGrow 模板列名：**
```
序号, 描述, 秸秆类型, 秸秆还田量, 秸秆残茬量, 还田方式, 翻耕深度
```

**本系统列名（英文）：**
```
previousCropType, previousCropAccount, previousCropStraw,
previousCropStubble, residueDepth
```

**字段映射：**
| 模板字段 | 本系统字段 | 说明 |
|---------|-----------|------|
| 秸秆类型 | previousCropType | 小麦秸秆/水稻秸秆等 |
| 秸秆还田量 | previousCropStraw | kg/ha |
| 秸秆残茬量 | previousCropStubble | kg/ha |
| 翻耕深度 | residueDepth | cm |
| - | previousCropAccount | 新增：作物生物量 |

#### 6. 管理数据 (planting.csv + irrigation.csv → data/管理数据_多种方案.csv)

**RiceGrow 模板列名：**
```
序号, 描述, 播种日期, 播种量, 播种深度, 种植方式, 移栽日期, 每穴株数, 每平米穴数
```

**本系统列名（英文）：**
```
plantSeedQuantity, plantingDepth, numberPerHill, numberHillsM2,
VI, SoilSand, OMN, OMS, WaterRegime
```

**字段映射：**
| 模板字段 | 本系统字段 | 说明 |
|---------|-----------|------|
| 播种量 | plantSeedQuantity | kg/ha |
| 播种深度 | plantingDepth | cm |
| 每穴株数 | numberPerHill | 株/穴 |
| 每平米穴数 | numberHillsM2 | 穴/m² |
| - | VI | 品种序号 |
| - | SoilSand | 土壤砂粒含量(%) |
| - | OMN | 快速分解有机质 |
| - | OMS | 慢速分解有机质 |
| 灌溉模式 | WaterRegime | 1-5 |

**注意：** 模板中的播种日期、移栽日期等信息在本系统中存储在 `调参数据.csv` 中。

#### 7. 调参数据 (分散字段 → data/调参数据.csv)

**RiceGrow 模板：**
- 位置信息：soil.csv 中的经度、纬度、位置
- 日期信息：planting.csv 中的播种日期、移栽日期

**本系统列名（英文）：**
```
PanelCode, SowingDate, TransplantDate, booting, heading, anthesis,
maturity, site, Latitude, year
```

### 转换脚本示例

```python
import pandas as pd
from datetime import datetime

def date_to_doy(date_str):
    """将日期字符串转换为年积日"""
    date_obj = datetime.strptime(date_str, '%Y/%m/%d')
    return date_obj.timetuple().tm_yday

# 1. 品种参数转换
def convert_cultivar(template_path, output_path):
    df = pd.read_csv(template_path, encoding='gbk', skiprows=3)
    # 重命名列
    column_map = {
        '品种名称': 'PZ', '光敏感性': 'PS', '温度敏感性': 'TS',
        '品种最适温度': 'TO', '基本早熟性': 'IE', '灌浆因子': 'FDF',
        '收获指数': 'PHI', '千粒重': 'TGW', '总叶龄': 'TLN',
        '比叶面积': 'SLAc'
    }
    df.rename(columns=column_map, inplace=True)
    df.to_csv(output_path, encoding='gbk', index=False)

# 2. 施肥数据转换（日期转DOY）
def convert_fertilizer(template_path, output_path):
    df = pd.read_csv(template_path, encoding='gbk', skiprows=8)
    df['DOY'] = df['日期'].apply(date_to_doy)
    column_map = {
        '施肥类型': 'type', '施肥方式': 'methodName',
        '氮总量': 'nAmount', '磷总量': 'pAmount', '钾总量': 'kAmount',
        '硝态氮量': 'NO3Amount', '铵态氮量': 'NH4Amount',
        '酰胺态氮量': 'UREAAmount'
    }
    df.rename(columns=column_map, inplace=True)
    df.to_csv(output_path, encoding='gbk', index=False)
```

### 转换注意事项

1. **编码问题**：模板文件使用 GBK 编码，包含中文列名，需正确处理
2. **注释行**：模板文件前几行为注释说明，需要跳过（skiprows 参数）
3. **日期格式**：施肥数据的日期需要转换为年积日 (DOY)
4. **数据合并**：气象数据需要合并 weather.csv 和 Weather/站点.csv
5. **新增字段**：本系统有一些模板中没有的字段（如 VI, SoilSand, OMN, OMS），需要根据实际情况补充
