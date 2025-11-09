# MuleRun Agent 爬虫

一个用于监控和追踪 [MuleRun](https://mulerun.com/) 网站上 AI agents 的 Python 爬虫项目。

## 功能特性

- ✅ 自动爬取 MuleRun 网站上的所有 agents（Most used 排序）
- ✅ 无限滚动加载，自动获取所有内容
- ✅ PostgreSQL 数据库存储
- ✅ 历史排名追踪（记录每次爬取的排名变化）
- ✅ 下架检测（自动标记消失的 agents）
- ✅ 定时任务（每 24 小时自动爬取一次）
- ✅ 单次运行和守护进程两种模式

## 项目结构

```
mulerun_crawl/
├── mulerun_crawl/              # 主包
│   ├── __init__.py
│   ├── config.py               # 配置模块
│   ├── crawler/                # 爬虫模块
│   │   ├── __init__.py
│   │   └── crawler.py
│   ├── storage/                # 存储模块
│   │   ├── __init__.py
│   │   └── database.py
│   ├── scheduler/              # 调度模块
│   │   ├── __init__.py
│   │   └── scheduler.py
│   └── utils/                  # 工具模块
│       ├── __init__.py
│       └── logging.py
├── scripts/                    # 脚本目录
│   └── query.py                # 数据查询工具
├── main.py                     # 主程序入口
├── requirements.txt            # Python 依赖
├── pyproject.toml              # 项目配置
├── setup.sh                    # 快速设置脚本
├── env.example                 # 环境变量示例
├── mulerun-crawl.service.example  # systemd 服务示例
└── README.md                   # 项目说明
```

## 安装

### 快速安装（推荐）

使用提供的设置脚本：

```bash
git clone <repository-url>
cd mulerun_crawl
./setup.sh
```

然后编辑 `.env` 文件配置数据库连接。

### 手动安装

#### 1. 克隆项目

```bash
git clone <repository-url>
cd mulerun_crawl
```

#### 2. 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

#### 4. 安装 Playwright 浏览器和系统依赖

```bash
# 安装浏览器
playwright install chromium

# 安装系统依赖（VPS 环境必需）
sudo playwright install-deps chromium
```

> **重要：** 在 Linux VPS 环境中，必须安装系统依赖，否则浏览器无法启动。

#### 5. 配置 PostgreSQL 数据库

**使用 Neon（推荐）：**

1. 在 [Neon](https://neon.tech) 创建免费账户
2. 创建新项目
3. 从控制台复制连接字符串（Connection String）
4. **重要：数据库表会在首次运行时自动创建，无需手动初始化！**

> 详细说明请查看 [DATABASE_SETUP.md](DATABASE_SETUP.md)

**或使用本地 PostgreSQL：**

确保已安装并运行 PostgreSQL，然后创建数据库：

```sql
CREATE DATABASE mulerun_crawl;
```

> 注意：即使使用本地 PostgreSQL，表也会自动创建，无需手动初始化。

#### 6. 配置环境变量

创建 `.env` 文件并配置数据库连接：

```bash
cp env.example .env
```

**Neon PostgreSQL 配置（推荐）：**

编辑 `.env` 文件，添加 Neon 连接字符串：

```env
# 从 Neon 控制台复制连接字符串
DATABASE_URL=postgresql://username:password@host.neon.tech/database?sslmode=require
```

**传统 PostgreSQL 配置（可选）：**

如果不使用 Neon，可以使用传统配置方式：

```env
DB_HOST=localhost
DB_PORT=5432
DB_DATABASE=mulerun_crawl
DB_USER=postgres
DB_PASSWORD=your_password_here
```

> **注意**：如果设置了 `DATABASE_URL`，系统会优先使用它，忽略其他数据库配置项。

## 使用方法

### 单次运行模式

执行一次爬取任务：

```bash
python main.py --mode once
```

### 守护进程模式（定时任务）

启动定时任务，每 24 小时自动爬取一次：

```bash
python main.py --mode daemon
```

如果不想立即执行一次爬取：

```bash
python main.py --mode daemon --no-immediate
```

### 数据查询工具

项目提供了 `query.py` 脚本用于查询数据：

#### 列出所有 agents

```bash
# 列出所有 agents（包括下架的）
python scripts/query.py list

# 只列出活跃的 agents
python scripts/query.py list --active-only

# 限制返回数量
python scripts/query.py list --limit 10
```

#### 查看某个 agent 的排名历史

```bash
python scripts/query.py history "/@laughing_code/chibi-sticker-maker"
```

#### 查看统计信息

```bash
# 基本统计
python scripts/query.py stats

# 包含排名变化最大的 agents
python scripts/query.py stats --show-changes
```

## 数据库结构

### agents 表（当前状态）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL | 主键 |
| link | TEXT | Agent 链接（唯一标识） |
| name | TEXT | Agent 名称 |
| description | TEXT | 描述 |
| avatar_url | TEXT | 头像 URL |
| price | TEXT | 价格信息 |
| author | TEXT | 作者 |
| rank | INTEGER | 当前排名 |
| is_active | BOOLEAN | 是否活跃（False 表示已下架） |
| first_seen | TIMESTAMP | 首次发现时间 |
| last_updated | TIMESTAMP | 最后更新时间 |
| created_at | TIMESTAMP | 创建时间 |

### rank_history 表（历史排名）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL | 主键 |
| agent_link | TEXT | Agent 链接（外键） |
| rank | INTEGER | 排名 |
| crawl_time | TIMESTAMP | 爬取时间 |
| created_at | TIMESTAMP | 创建时间 |

## 配置说明

主要配置在 `config.py` 文件中，可以通过环境变量覆盖：

- `CRAWLER_CONFIG`: 爬虫配置（滚动延迟、超时时间等）
- `DATABASE_CONFIG`: 数据库连接配置
- `SCHEDULER_CONFIG`: 定时任务配置
- `LOG_CONFIG`: 日志配置

## VPS 部署

> 📖 **详细部署指南**: 查看 [VPS_DEPLOYMENT.md](VPS_DEPLOYMENT.md) 获取完整的部署步骤和故障排查指南。

### 快速部署（5 步）

```bash
# 1. 克隆项目
git clone <repository-url> && cd mulerun_crawl

# 2. 运行设置脚本
chmod +x setup.sh && ./setup.sh

# 3. 配置数据库（编辑 .env 文件）
nano .env
# 添加: DATABASE_URL=postgresql://...

# 4. 测试运行
source .venv/bin/activate
python main.py --mode once

# 5. 部署为 systemd 服务
sudo cp mulerun-crawl.service.example /etc/systemd/system/mulerun-crawl.service
sudo nano /etc/systemd/system/mulerun-crawl.service  # 修改路径和用户
sudo systemctl daemon-reload
sudo systemctl enable mulerun-crawl
sudo systemctl start mulerun-crawl
```

### 常用命令

```bash
# 查看服务状态
sudo systemctl status mulerun-crawl

# 查看日志
sudo journalctl -u mulerun-crawl -f
tail -f logs/crawler.log

# 重启服务
sudo systemctl restart mulerun-crawl
```

## 日志

日志文件保存在 `logs/crawler.log`，会自动轮转（最大 10MB，保留 5 个备份）。

## 系统要求

- **操作系统**: Linux (Ubuntu/Debian 推荐)
- **Python**: 3.10 或更高版本
- **内存**: 至少 1GB RAM（推荐 2GB+）
- **磁盘空间**: 至少 500MB（用于浏览器和日志）
- **网络**: 稳定的互联网连接

## 注意事项

1. **系统依赖**: 必须安装 Playwright 系统依赖，否则浏览器无法启动
2. **反爬虫**: 代码中已设置合理的延迟和 User-Agent，请遵守网站的 robots.txt 和使用条款
3. **数据库备份**: 建议定期备份 PostgreSQL 数据库
4. **资源占用**: Playwright 会占用一定内存，确保 VPS 有足够资源
5. **网络稳定性**: 确保 VPS 网络连接稳定

## 开发

### 运行测试

```bash
# 单次运行测试
python main.py --mode once
```

### 查看日志

```bash
tail -f logs/crawler.log
```

## License

MIT

