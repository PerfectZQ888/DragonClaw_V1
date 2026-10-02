# 🔒 Security Policy

## 支持的版本

| 版本 | 支持状态 |
|------|:------:|
| V1.3 (latest) | ✅ |
| < V1.3 | ❌ |

## 报告漏洞

**请勿在公开 Issues 报告安全漏洞!**

用 GitHub Private Vulnerability Reporting:
https://github.com/PerfectZQ888/DragonClaw/security/advisories/new

我们会:
- 24 小时内确认
- 评估严重性并给出修复时间线
- 修复后公开致谢 (如您愿意)

## 安全最佳实践

- 🔑 **永远不要 commit** `.env`, `auth_token`, `openclaw.json` 到 git
- 🔑 使用 **strong token** (≥ 32 字符)
- 🔒 **不要在公网暴露 dashboard** 默认端口 8888
- 🔒 用 **firewalld** 限制源 IP
- 📝 定期 rotate `REGISTRY_SERVICE_TOKEN`