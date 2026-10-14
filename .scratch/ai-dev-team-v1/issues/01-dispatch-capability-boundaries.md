# 01: 补齐工具派发的失败边界

Milestone: M1 — 跑通最小协作
Status: ready-for-agent

**What to build:** 用户能够在两种已选 Harness 上完成最小非业务派发，并在输入无效、能力缺失或投递结果不明时得到明确停止原因，而不是静默降级、重复发送或假报成功。

**Blocked by:** None (can start immediately).

**Execution gate:** 2026-10-13 已按用户 `/implement` 指令仅实施本票，并取得两个测试 Pane、两次无业务模型调用及空闲后关闭的明确授权。本票通过；`Status` 仍为 triage 标签，不用它表达完成状态。未获准进入工单 02，不自动继续。

## 上下文与范围

对应 [TASKS T01](../../../TASKS.md)；依据 [DESIGN 第 4、9 节](../../../DESIGN.md)。这是 [PRD A01](../../../PRD.md) 的工具能力前置，不是双向业务闭环验收。

已有证据可直接复用：Herdr 客户端/服务端及 integrations 已核对；官方 Skill 已共享安装；Claude Code 和 Codex 均完成加载、启动、提示投递和响应读取；Codex 定向只读 profile 与一次性 YOLO 查询已成功。不要重复安装或把整套冒烟重跑一遍。

本票仅补原生模型选择、无效输入/必需能力缺失和投递不明的最小安全处理。恢复、取消及业务协议由后续票完成；不提前开发 Adapter。

## Acceptance criteria

- [x] 将已有证据与待补项逐项对照，保留实际版本、命令和结论；不能仅凭工具存在或员工 PASS 宣告通过。
- [x] 在获准的小型测试场景验证有效原生模型选择参数；参数或必需能力不兼容时明确阻塞，不默默改模型、删 Skill 约束或换工具。
- [x] 无效目标/输入不会误控其他会话；实际 Pane/Agent 标识来自返回结果而非猜测。
- [x] 用一个有界、受控的失败场景验证投递不明时先观察和对账，不因超时、unknown 或缺少结果立即重复发送。
- [x] 不自动确认原生信任/权限提示；只读 profile 不当作开发写入授权，一次性 YOLO 测试不形成后续默认。
- [x] 在 DESIGN 原有能力基线补充证据及未验证项，不另建规格；若关键能力仍不足，明确报告阻塞，不自动进入下一票。

## 验证与执行约束

优先复用已有 CLI 和实际输出；只运行补缺口所需的最小场景。使用新建、获准的测试资源，不重启共享 server、不停止其他会话、不修改业务仓库。需要环境或权限调整时先说明范围并取得授权。

## Comments

### 2026-10-13 · 本票实施与验收

**结论：本票通过。** 只补工具级失败边界；不表示 PRD A01、业务状态、权限全矩阵或完整产品通过。无前置票据，已读取项目规则和 PRD、DESIGN、TASKS，核对 DESIGN 9.1 指向的原生会话工具记录，而非仅凭 `ready-for-agent` 开始验收。

**授权与范围**：用户选择“授权上述补测”，范围为当前 tab 的两个不抢焦点 sibling Pane、各一次无业务模型调用、证据保存和仅关闭本次已确认空闲的 Pane。项目不是 Git 仓库；未初始化 Git、创建验收仓库、提交、推送、重置或删除工作区。未改用户配置、权限、hooks 或 Skills，未开发 Adapter、业务状态系统或后续票资产。

**变更与证据**：项目内仅更新 `DESIGN.md` 第 9 节及本票。详细记录在 `<M1_01_EVIDENCE>/`，其中 `DESIGN.before.md`、`01.before.md` 保留修改前副本，命令 JSON 保留 argv、时间、退出码与输出。正式能力基线仍只维护在 DESIGN，不另建规格。

| 验收项 | 实际验证命令/结果与证据 |
| --- | --- |
| 1 · 已有证据与缺口对照 | `herdr status`、`claude --version`、`codex --version` 确认 Herdr 0.9.3 / Claude Code 2.1.296 / Codex 0.162.1；只读核对既有 Claude、Codex profile 和 YOLO 原生记录中的查询与返回。复用安装、加载、基础交互及 profile 边界，不整套重跑。见 `01`–`03`、`31-baseline-reuse.json` 及 DESIGN 9.1、9.3 |
| 2 · 模型与失败边界 | Claude：`herdr agent start m1-01-claude --kind claude --pane PANE-M1-01-CLAUDE --timeout 30000 -- --model fable --permission-mode manual`，退出码 0；本机既有别名映射为 `gpt-6-astra`，UI 与原生响应记录一致，不宣称验证 Anthropic Fable。Codex：`herdr agent start m1-01-codex --kind codex --pane PANE-M1-01-CODEX --timeout 30000 -- --profile herdr --model gpt-5.6-sol`，退出码 0，原生 model 匹配。`claude --model` / `codex --model` 缺值分别退出 1 / 2；`agent start m1-no-kind --kind m1-missing-kind --pane PANE-M1-01-CLAUDE --timeout 1000` 退出 2、明确 unsupported，未在该 Pane 启动 Agent。负向请求均停止，未换模型、删约束或换工具重试。见 `05`、`06`、`09`–`15`、`18`–`19`、`30` |
| 3 · 无效输入与真实 ID | `herdr agent prompt M1/INVALID M1_INVALID_DO_NOT_DELIVER --wait --timeout 1000` 退出 1、`agent_not_found`，未回退到聚焦会话。两个有效 Pane ID 分别来自 `pane split --current --direction right/down --cwd <项目目录> --no-focus` 返回；前后既有 Agent 身份与状态序列一致。见 `04`、`07`、`08`、`16`、`36`–`37` |
| 4 · 超时后观察对账 | 单次 Codex 标记提示使用 `agent prompt m1-01-codex <标记提示> --wait --timeout 100`，退出 1、`timeout`。随后依次 `agent get`、`agent read --source recent-unwrapped --lines 100`、`agent wait --until done --timeout 30000`、get/read 和原生记录对账；没有再次 prompt。最初 get=idle 而 read 已显示 Working，最终原生记录只有 1 条测试用户消息、1 条精确响应、0 次工具调用。见发送前的 `20-dispatch-intent.json` 及 `22`–`24`、`26`–`30` |
| 5 · 权限不扩展 | Claude 运行前后 UI 均为 manual；Codex 原生 `turn_context` 为 `read-only / on-request`，没有 `--yolo`、sandbox 覆盖或权限确认按键。两次提示禁止工具/文件操作，原生记录工具调用数均为 0。本次未出现信任或审批提示，不据此声称再次验证了审批拒绝路径。见 `13`、`18`、`25`、`30` |
| 6 · 基线与停止 | DESIGN 9.3 记录本票实测，9.4 保留未验证变体。新 Pane `PANE-M1-01-CLAUDE`、`PANE-M1-01-CODEX` 经身份、响应与 done 核对后关闭，退出码均为 0；原有会话与调用方焦点仍在。见 `32`–`37`。不领取 02 |

**未解决/未验证边界**：真实 Skill 断链、支持文件缺失、非空无效模型名/服务端拒绝、working 起点等待、`agent_prompt_stalled / unknown` 独立故障复现、连接中断与无法对账的副作用未演练；没有为测试破坏真实安装、权限或共享 server。这些不是本票所选最小负向场景的通过证据，也不影响已完成的缺参、不支持 kind 和真实 timeout 演练。模型身份只确认到本机 Harness 配置/记录层，未验证服务端底层实现。恢复、取消、业务状态、开发写入权限和双向业务闭环仍由后续票验证。

**验证与清理**：实际运行最小 CLI/原生会话检查，无业务代码改动，因此未运行编译、全量套件或新增测试文件。只清理了已获准的两个测试 Pane；运行证据与修改前副本保留。工具探索中一次 Python 读取因系统 Python 缺少 `tomllib` 失败，改为标准库定向读取后完成，未安装依赖。

**最终收口**：`39-focused-verification.json` 的 17 项定向证据核对全部通过；独立 `code-review` 对照修改前副本检查两份文档增量及对应证据，未报告问题，结果保存在 `40-independent-review.json`。审查后仅追加本段收口记录，最终文档指纹与证据索引见 `42-delivery-manifest.json`。本票通过，停止；不进入 02。

### 2026-10-13 · 后续新会话默认更新

用户最新明确并二次确认的项目决定，仅面向主管/员工未来新会话取代此前的非默认策略，启动参数与权限边界见 DESIGN 第 2.4 节。该授权来自最新决定，不来自本票的一次性 YOLO 测试；本票原始命令、验收勾选、通过结论及证据不变，也不据此证明新默认的模型调用已通过或扩大业务操作授权。
