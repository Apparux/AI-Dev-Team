---
name: orchestrator
description: 登记项目、解析三层 Run 配置并组织受监督执行；需要只读核查、带身份/工作区归属的非业务交付，或获准的版本化测试修复时使用。
---

# 受监督主管

1. 读取主管职责、当前工单和正式依据，核对前置票据的实际证据。确认仓库、基准、范围、工作区、结果写入、模型调用和终端资源授权。
2. 必读本目录 `references/configuration.md`。新会话默认见 `DESIGN.md` 2.4：Codex 使用 `--no-daemon` 隔离执行上下文，保留 YOLO/gpt-6.1-sol；Claude bypassPermissions 且沿用所选模型。按实际解析配置启动并核对身份；不重启既有会话、不改全局配置、不把高权限模式当业务批准或沙箱。
3. 按下面明确的模式入口执行；配置、能力或证据不足时报告 BLOCKED，不静默换参数或工具。

## 带身份的交付

Task/dispatch 协议为 `identified-delivery-v1` 时，必读 `references/identified.md` 与 `scripts/state.py`。initialize 缺省为 `non-business`；明确批准的测试修复显式指定 `versioned-test-fix`，按对应授权和版本门禁执行，不混用两种模式。按入口完成独立工作区绑定、任务/阶段意图、真实执行身份绑定、单次派发、员工结果核验与持久状态；只有受支持状态入口可推进。创建/启动/读取复用官方 `herdr` Skill，不开发执行适配器。主管只派发/核验，最终只读核对工作区、结果版本和真实检查输出，按本票实际证据收口后停止，不自动进入下一工单。

## 只读观察

1. 按配置说明使用 `scripts/configure.py register/prepare`。工具返回 BLOCKED 时停止；既有登记/Run 不覆盖。
2. 读取 `dispatch-input.json.supervisor_reads`，核对快照参数与有效限制。加载已有官方 `herdr` Skill，检查环境、服务和实际原生状态。
3. 在获准空闲 Pane 使用输出的原生参数启动；真实 ID 从 JSON 取得。剩余信任/认证/权限/提问界面交给用户，不代确认。
4. 记录目标身份和单次发送意图，将 prompt 原样投递一次，有界观察。员工仅终端返回观察结果，不要求写文件。
5. timeout/stalled/unknown 不代表未投递；先 get/read/wait，不自动重发或换模型。对照源文件与实际调用核对结果及前后差异，仅报告只读观察，不推进正式 Task 状态。

该 Skill 不安装工具、不变更用户全局权限、不提供通用 Runtime 或完整恢复；归属或状态不明时保留现场。
