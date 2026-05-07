# Asset Platform

Django 资产管理系统 — 结合 RAG（检索增强生成）与 DeepSeek AI，实现自然语言驱动的资产语义检索和智能财务分析。

## 功能亮点

- **RAG 智能资产检索** — 基于 BGE 中文向量模型，用自然语言搜索资产，支持语义匹配
- **AI 财务分析** — SQL 本地聚合硬数据 + 向量语义检索 + DeepSeek 生成分析报告，输出结构化的数据摘要、洞察和处置建议
- **ECharts 可视化** — 按状态/部门/分类自动生成饼图分布
- **完整的 REST API** — DRF 提供资产 CRUD、搜索、排序、分类/部门管理
- **向量索引** — 纯 numpy 实现的轻量级向量存储，无需外部数据库依赖

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | Django 4.2 + Django REST Framework |
| 数据库 | MySQL |
| AI 模型 | DeepSeek Chat API |
| 向量模型 | BAAI/bge-small-zh-v1.5 (sentence-transformers) |
| 向量存储 | NumPy (内存) + JSON 持久化 |
| 前端图表 | ECharts 5 |
| 部署 | Docker + Gunicorn |

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/kuku-1019/asset-platform.git
cd asset-platform
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入你的配置：

```env
DJANGO_SECRET_KEY=你的密钥
DJANGO_DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_ENGINE=django.db.backends.mysql
DB_NAME=mysql_asset
DB_USER=root
DB_PASSWORD=你的数据库密码
DB_HOST=127.0.0.1
DB_PORT=3306

DEEPSEEK_API_KEY=你的DeepSeek-API-Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 初始化数据库

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. 启动服务

```bash
# 开发环境
python manage.py runserver

# 或用 Docker
docker-compose up
```

访问 http://127.0.0.1:8000

### 6. 导入资产数据后重建向量索引

在管理后台 `/admin` 添加资产后，点击页面上的「重建向量索引」按钮，即可启用 RAG 搜索。

## API 文档

### 资产

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/assets/` | 列表（分页、搜索、排序） |
| POST | `/api/assets/` | 创建资产 |
| GET | `/api/assets/{id}/` | 资产详情 |
| DELETE | `/api/assets/{id}/` | 删除资产 |

查询参数：`?search=关键词` `?ordering=price` `?ordering=-id`

### 分类 & 部门

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/categories/` | 分类列表 |
| GET | `/api/departments/` | 部门列表 |

### AI 分析

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/ai-report/` | RAG 驱动的结构化财务分析 |
| POST | `/api/rag-query/` | 语义检索 + AI 问答 |
| POST | `/api/reindex/` | 重建向量索引 |

**`POST /api/ai-report/`**

```json
// Request
{ "query": "分析IT部门闲置资产，给出处置建议" }

// Response
{
  "stats": {
    "total_count": 5,
    "total_value": 34499.0,
    "avg_price": 6899.8,
    "by_status": { "使用中": 2, "闲置中": 1, "维修中": 1, "已报废": 1 },
    "by_category": { "电子设备": 3, "办公家具": 1, "软件许可": 1 },
    "by_department": { "技术部": 3, "人事部": 1, "财务部": 1 }
  },
  "analysis": "### 1. 数据摘要\n...\n### 2. 分析洞察\n...\n### 3. 处置建议\n...",
  "sources": [{ "name": "MacBook Pro", "sn": "SN001", ... }]
}
```

## 项目结构

```
asset_platform/
├── asset_platform/          # Django 项目配置
│   ├── settings.py          # 所有配置（DB、Cache、Chroma、AI）
│   ├── urls.py              # 根路由
│   └── wsgi.py
├── assets/                  # 资产应用
│   ├── models.py            # Asset / Category / Department
│   ├── serializers.py       # DRF 序列化
│   ├── views.py             # ViewSets + AI/RAG 端点
│   ├── urls.py              # API 路由
│   ├── services/
│   │   ├── ai_analysis.py   # DeepSeek AI + SQL 聚合
│   │   └── vector_store.py  # 向量存储（NumPy + JSON）
│   └── templates/
│       └── index.html       # 前端（ECharts + 交互）
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── .gitignore
```

## 运行测试

```bash
python manage.py test assets -v 2
```

## License

MIT
