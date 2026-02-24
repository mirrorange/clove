# Clove 🍀

<div align="center">

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)

**全力以赴的 Claude 反向代理 ✨**

[English](./README_en.md) | [简体中文](#)

</div>

## 🌟 这是什么？

Clove 是一个让你能够通过标准 Claude API 访问 Claude.ai 的反向代理工具。简单来说，它让各种 AI 应用都能连接上 Claude！

**最大亮点**：Clove 是首个支持通过 OAuth 认证访问 Claude 官方 API 的反向代理（就是 Claude Code 用的那个）！这意味着你能享受到完整的 Claude API 功能，包括原生系统消息和预填充等高级特性。

## 🚀 快速开始

只需要三步，就能开始使用：

### 1. 安装 Python

确保你的电脑上有 Python 3.13 或更高版本

### 2. 安装 Clove

```bash
pip install "clove-proxy[rnet]"
```

### 3. 启动！

```bash
clove
```

启动后会在控制台显示一个随机生成的临时管理密钥。登录管理页面后别忘了添加自己的密钥哦！

### 4. 配置账户

打开浏览器访问：http://localhost:5201

使用刚才的管理密钥登录，然后就可以添加你的 Claude 账户了～

## ✨ 核心功能

### 🔐 双模式运行

- **OAuth 模式**：优先使用，可以访问 Claude API 的全部功能
- **网页反代模式**：当 OAuth 不可用时自动切换，通过模拟 Claude.ai 网页版实现

### 🎯 超高兼容性

与其他反代工具（如 Clewd）相比，Clove 的兼容性非常出色：

- ✅ 完全支持 SillyTavern
- ✅ 支持绝大部分使用 Claude API 的应用
- ✅ 甚至支持 Claude Code 本身！

### 🛠️ 功能增强

#### 对于 OAuth 模式

- 完全访问 Claude API 的全部功能
- 支持原生系统消息
- 支持预填充功能
- 性能更好，更稳定

#### 对于 Claude.ai 网页反代模式

Clove 处理了 Claude.ai 网页版与 API 的各种差异：

- 图片上传支持
- 扩展思考（思维链）支持

即使是通过网页反代，Clove 也能让你使用原本不支持的功能：

- 工具调用（Function Calling）
- 停止序列（Stop Sequences）
- Token 计数（估算值）
- 非流式传输

Clove 尽可能让 Claude.ai 网页反代更接近 API，以期在所有应用程序中获得无缝体验。

### 🎨 友好的管理界面

- 现代化的 Web 管理界面
- 无需编辑配置文件
- 所有设置都能在管理页面上完成
- 自动管理用户配额和状态

### 🔄 智能功能

- **自动 OAuth 认证**：通过 Cookie 自动完成，无需手动登录 Claude Code
- **智能切换**：自动在 OAuth 和 Claude.ai 网页反代之间切换
- **配额管理**：超出配额时自动标记并在重置时恢复

## ⚠️ 局限性

### 1. Android Termux 用户注意

Clove 依赖 `curl_cffi` 来请求 claude.ai，但这个依赖无法在 Termux 上运行。

**解决方案**：

- 使用不含 curl_cffi 的版本：`pip install clove-proxy`
  - ✅ 通过 OAuth 访问 Claude API（需要在管理页面手动完成认证）
  - ❌ 无法使用网页反代功能
  - ❌ 无法自动完成 OAuth 认证
- 使用反向代理/镜像（如 fuclaude）
  - ✅ 可以使用全部功能
  - ❌ 需要额外的服务器（既然有搭建镜像的服务器，为什么要在 Termux 上部署呢 www）

### 2. 工具调用限制

如果你使用网页反代模式，避免接入会**大量并行执行工具调用**的应用。

- Clove 需要保持与 Claude.ai 的连接等待工具调用结果
- 过多并行调用会耗尽连接导致失败
- OAuth 模式不受此限制

### 3. 提示结构限制

当 Clove 使用网页反代时，Claude.ai 会在提示中添加额外的系统提示词和文件上传结构。当使用对结构要求高的提示词（如 RP 预设）时：

- 你可以预估请求将通过何种方式进行。在默认配置下：
  - 使用 Free 账户时，所有请求通过 Claude.ai 网页反代
  - 使用 Pro 账户时，Sonnet 模型通过 Claude API，Opus 模型通过 Claude.ai 网页反代
  - 使用 Max 账户时，所有请求通过 Claude API 进行
  - 若存在多账户，Clove 始终优先使用可访问该模型 API 的账户
- 请选择与请求方式兼容的提示词

## 🔧 高级配置

### 环境变量

虽然大部分配置都能在管理界面完成，但你也可以通过环境变量进行设置：

```bash
# 端口配置
PORT=5201

# 管理密钥（不设置则自动生成）
ADMIN_API_KEYS==your-secret-key

# Claude.ai Cookie
COOKIES=sessionKey=your-session-key
```

更多配置请见 `.env.example` 文件。

### API 使用

配置完成后，你可以像使用标准 Claude API 一样使用 Clove：

```python
import anthropic

client = anthropic.Anthropic(
    base_url="http://localhost:5201",
    api_key="your-api-key"  # 在管理界面创建
)

response = client.messages.create(
    model="claude-opus-4-20250514",
    messages=[{"role": "user", "content": "Hello, Claude!"}],
    max_tokens=1024,
)
```

## 🤝 贡献

欢迎贡献代码！如果你有好的想法或发现了问题：

1. Fork 这个项目
2. 创建你的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开一个 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [Anthropic Claude](https://www.anthropic.com/claude) - ~~可爱的小克~~ 强大的 AI 助手
- [Clewd](https://github.com/teralomaniac/clewd/) - 初代 Claude.ai 反向代理
- [ClewdR](https://github.com/Xerxes-2/clewdr) - 高性能 Claude.ai 反向代理
- [FastAPI](https://fastapi.tiangolo.com/) - 现代、快速的 Web 框架
- [Tailwind CSS](https://tailwindcss.com/) - CSS 框架
- [Shadcn UI](https://ui.shadcn.com/) - 现代化的 UI 组件库
- [Vite](https://vitejs.dev/) - 现代化的前端构建工具
- [React](https://reactjs.org/) - JavaScript 库

## ⚠️ 免责声明

本项目仅供学习和研究使用。使用本项目时，请遵守相关服务的使用条款。作者不对任何滥用或违反服务条款的行为负责。

## 📮 联系方式

如有问题或建议，欢迎通过以下方式联系：

- 提交 [Issue](https://github.com/mirrorange/clove/issues)
- 发送 Pull Request
- 发送邮件至：orange@freesia.ink

## 🌸 关于 Clove

丁香，桃金娘科蒲桃属植物，是一种常见的香料，也可用作中药。丁香（Clove）与丁香花（Syringa）是两种不同的植物哦~在本项目中，Clove 更接近 Claude 和 love 的合成词呢！

---

<div align="center">
Made with ❤️ by 🍊
</div>
