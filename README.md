# HydroGLM MCP for Codex

本项目通过本机 stdio MCP 为 Codex 添加 `ask_hydroglm` 工具，用于调用瀚海 HydroGLM 或 HydroGLM-plus。它不会替换 Codex 当前使用的模型。

[完整中文安装、使用与排障说明](docs/使用说明.md)

## 仓库文件

- `server.py`：MCP stdio 服务和 `ask_hydroglm` 工具。
- `setup.sh`：配置个人 Key 并注册 MCP。
- `configure_key.py`：隐藏输入并安全保存 API Key。
- `diagnose.py`：检查 Key 与模型列表接口。
- `probe_chat.py`：发送一次真实问答请求，诊断生成接口。
- `docs/使用说明.md`：完整安装、调用、会话和排障指南。
- `SECURITY.md`：密钥与安全问题处理说明。

## 快速开始

要求：Linux、Codex CLI、Python 3.10 或更高版本，以及绑定到目标智能体的 HydroGLM API Key。本项目只使用 Python 标准库，无需安装第三方 Python 包。

1. 克隆仓库或下载源码压缩包并解压。
2. 在仓库目录运行：

   ```bash
   bash setup.sh
   ```

3. 按提示输入自己的 API Key。输入不会回显。安装脚本会保存密钥并注册 MCP。
4. 重启 Codex，然后提问：

   > 用 `ask_hydroglm` 查询：水库汛限水位有什么作用？

默认使用 HydroGLM。使用 HydroGLM-plus：

```bash
bash setup.sh HydroGLM-plus
```

## 工具参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `question` | string | 是 | 发给 HydroGLM 的问题。最多 20,000 个 Python 字符。 |
| `agent` | string | 否 | `HydroGLM` 或 `HydroGLM-plus`；默认 `HydroGLM`。密钥必须绑定到所选智能体。 |
| `session_id` | integer | 否 | 上一次回答返回的会话编号，用于继续服务端会话。 |
| `web_search` | boolean | 否 | 启用瀚海侧联网搜索；默认关闭。 |
| `enable_thinking` | boolean | 否 | 启用智能体思考模式；默认关闭。 |

工具返回文本答案；如接口返回 `session_id`，会附在答案末尾。MCP 不提供本地对话记忆，也不暴露函数调用结果。

## 密钥与数据

- 每位使用者配置自己的 API Key。不要提交密钥、密钥截图或 `credentials.json`。
- 默认密钥文件：`~/.config/hydroglm-mcp/credentials.json`。安装脚本以仅本人可读写的权限保存。
- `XDG_CONFIG_HOME` 可改变密钥目录。环境变量 `HANHAI_HYDROGLM_API_KEY` 或 `HANHAI_HYDROGLM_PLUS_API_KEY`（取决于智能体）优先于文件配置。
- 问题内容会发送到 `hanhai-ai.com`。不要发送不应离开本机的数据。

## 连通性诊断

`diagnose.py` 只检查 `/models` 接口，不会生成回答：

```bash
python3 diagnose.py --agent HydroGLM
```

`probe_chat.py` 会实际提交一次问题并生成回答，可能产生服务用量：

```bash
python3 probe_chat.py --agent HydroGLM --question '请用一句话说明水库汛限水位的作用'
```

HTTP 200 的模型列表响应不能证明问答生成接口正常。若问答返回 504，记录时间、状态码、请求编号和错误内容，并联系接口提供方。

## 移除

```bash
codex mcp remove hydroglm
```

不再使用时，可同时在平台撤销 API Key，并删除本机密钥文件。

## 许可证

本项目采用 [MIT 许可证](LICENSE)。
