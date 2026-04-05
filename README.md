# Global ESG Risk Map

全球ESG风险地图是一个基于人工智能的工具，用于生成交互式网页版ESG（环境、社会、治理）风险可视化地图。该项目通过分析全球各国政策法规，为不同行业和ESG议题提供风险评估。

## 功能特性

- 🌍 **全球覆盖**：支持多国家ESG政策分析
- 📊 **交互式地图**：基于Plotly的可视化地图，支持多议题筛选
- 🤖 **AI驱动**：使用大语言模型自动分析政策内容和风险评估
- 🏭 **行业细分**：按GICS行业分类进行风险评估
- 📋 **政策详情**：点击地图查看具体政策法规信息

## 技术栈

- **后端**：Python Flask
- **前端**：HTML/CSS/JavaScript, Plotly.js
- **AI**：DashScope (阿里云)
- **数据处理**：Pandas, OpenPyXL
- **地图可视化**：Plotly Choropleth

## 项目结构

```
global_esg_risk_map/
├── data/
│   ├── input/          # 输入数据
│   ├── intermediate/   # 中间处理结果
│   └── output/         # 最终输出
├── src/
│   ├── pipeline/       # 数据处理流水线
│   └── web/            # Web应用
├── templates/          # HTML模板
├── requirements.txt    # Python依赖
├── .env               # 环境变量配置
└── README.md
```

## 安装和运行

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd global_esg_risk_map

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置API密钥

在`.env`文件中设置DashScope API密钥：

```
DASHSCOPE_API_KEY=your_api_key_here
```

### 3. 运行数据处理流水线

```bash
# 全自动运行所有步骤
python src/run_all_pipeline.py

# 或选择性运行特定步骤
python src/run_selective_pipeline.py
```

### 4. 启动Web应用

```bash
python src/web/app.py
```

访问 `http://127.0.0.1:5000` 查看地图。

## 🎛️ 交互式流水线配置

### 选择性运行流水线

```bash
python src/run_selective_pipeline.py
```

这将显示一个交互式菜单，允许您选择要执行的步骤。

### 步骤1：生成政策链接 - 自定义配置

运行时您可以：

#### 国家数量选择
选择处理的国家数量（1-192）：
```
📋 国家数量配置
==================================================
✅ 数据库中共有 192 个国家

请输入要处理的国家数量 (1-192, 默认全部): 5
✅ 已选择: 处理前 5 个国家
```

#### 议题选择
灵活选择要处理的ESG议题：

```
📋 ESG议题(topic)选择
==================================================
✅ 数据库中共有 18 个ESG议题(topic)
可选项目：
 1. 应对气候变化
 2. 可持续产品
 3. 废弃物及污染物管理
 4. 生态系统和生物多样性保护
 5. 能源管理
 ...

💡 输入格式：
   - 单个序号：5
   - 多个序号：1,3,5 或 1-3,7
   - 全部选择：all 或回车
   - 随机选择：random N（选择N个随机项目）

请选择ESG议题(topic)：1-3,7
✅ 已选择 4 个ESG议题(topic)：
   • 应对气候变化
   • 可持续产品
   • 废弃物及污染物管理
   • 能源管理
```

#### 数据处理模式
选择如何处理现有数据：

```
📝 数据处理模式
==================================================
选择如何处理现有数据：
1. 追加模式 (默认) - 在现有数据基础上追加新记录，自动跳过重复
2. 重置模式 - 清空现有文件，重新开始收集

请选择模式 (1-2，默认1): 1
```

### 推荐配置方案

| 场景 | 国家数 | 议题数 | 模型 | 温度 | 说明 |
|------|--------|--------|------|------|------|
| 快速测试 | 1-5 | 1-3 | qwen-turbo | 0.3 | 验证流程，快速迭代 |
| 小规模试点 | 10-20 | 5-8 | qwen-plus | 0.3 | 平衡质量和成本 |
| 生产级别 | 50+ | 10-15 | qwen-plus/max | 0.2 | 高质量输出 |
| 全量处理 | 192 | 18 | qwen-turbo | 0.3 | 完整数据集，时间允许时用turbo |

**💡 选择建议：**
- **议题选择**：优先选择气候变化、能源管理、社会贡献等关键议题
- **组合考虑**：国家数 × 议题数 = 总查询次数

## 数据处理流程

1. **生成政策链接** (`generate_policy_links.py`)
   - 使用AI生成相关政策法规链接
   - **新增功能**：支持选择特定ESG议题
   - **输出**：`policy_link.xlsx` (包含topic字段)

2. **政策内容分析** (`policy_content_analyse.py`)
   - 分析政策原文，提取关键信息

3. **政策风险评估** (`policy_risk_assessment.py`)
   - 对政策进行五维风险打分

4. **政策总风险计算** (`policy_total_risk_calculator.py`)
   - 根据行业相关性计算加权风险

5. **生成ESG风险地图** (`generate_global_esg_risk_map.py`)
   - 生成交互式HTML地图文件

5. **总风险汇总** (`total_risk_aggregator.py`)
   - 按国家-议题-行业汇总风险值

6. **生成地图** (`generate_global_esg_risk_map.py`)
   - 渲染交互式HTML地图

## 数据格式

### 输入数据 (`data/input/basic_data.xlsx`)

- `country_list`: 国家列表（英文名、中文名）
- `topic_list`: ESG议题列表
- `sector_list`: 行业列表
- `sector_correlation`: 行业相关性矩阵

### 中间数据 (`data/intermediate/`)

- `policy_link.xlsx`: 生成的政策链接
- `esg_risk_data.xlsx`: 分析后的风险数据

### 输出

- `templates/global_esg_risk_map.html`: 交互式地图页面

## 自定义配置

- 修改`data/input/basic_data.xlsx`添加新国家/行业/议题
- 调整`src/pipeline/`中各脚本的参数
- 自定义地图样式和交互逻辑

## 注意事项

- 需要有效的DashScope API密钥
- 数据处理可能需要较长时间，取决于API调用频率
- 建议定期更新政策数据以保持时效性

## Docker部署

### 使用Docker Compose

```bash
# 构建并启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 手动Docker构建

```bash
# 构建镜像
docker build -t esg-risk-map .

# 运行容器
docker run -p 5000:5000 -v $(pwd)/data:/app/data -v $(pwd)/.env:/app/.env esg-risk-map
```

## 贡献

欢迎提交Issue和Pull Request！

## 联系方式

[Your Contact Information]