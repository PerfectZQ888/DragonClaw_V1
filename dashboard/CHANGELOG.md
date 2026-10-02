# DragonClaw Dashboard V1 Changelog

## [v1.x.x] - 2026-04-14

### 🐛 Bug Fixes
- 修复 `task_chains.py` - 添加 `steps` 字段解决 `TypeError: chain.map is not a function`
- 修复 `tasks.py` - 添加 `tokens` 字段关联 agent token 统计
- 修复 `http_handler.py` - 添加根路径 `/` 重定向到 `/index.html`

### ⚙️ Configuration
- V2 端口修改: 8888 → 8889 (避免与 V1 冲突)

### 🧹 Cleanup
- 删除 `login.html` (认证已禁用)
- 删除 `js/*.bak` 备份文件
- 删除 `__pycache__/` Python 缓存
- 删除 `archive/` (已归档到 `/data/docs/dashboard_V1_arch/`)
- 删除 `docs/` (已归档)
- 清空 `data/` 数据目录
- 清空 `logs/` 日志目录

### 📝 Documentation
- 更新架构文档到归档目录

---

## 历史版本
- v1.0.0 - 初始版本
