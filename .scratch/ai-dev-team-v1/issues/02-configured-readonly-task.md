# 02: 由项目与 Run 配置驱动一次只读任务

Milestone: M1 — 跑通最小协作
Status: ready-for-agent

**What to build:** 用户登记项目并选择本次岗位执行配置后，主管能读取共享职责/Skill，在选定 Harness 上完成一次只读任务，展示实际结果及所用配置，而不是让用户手工拼接每次启动指令。

**Blocked by:** 01 — 补齐工具派发的失败边界。

**Execution gate:** 2026-10-13 已按用户 `/implement` 指令仅实施本票，先核验 01 原始证据并取得必要环境/验收资源授权。用户处理原生信任与认证门禁后，两种 Harness 均完成配置驱动的实际只读派发、共享方法读取与结果核对。本票通过；仅关闭本次已确认空闲的测试 Pane，保留样例与证据。停止，不进入 03。

## 上下文与范围

对应 [TASKS T02](../../../TASKS.md)，覆盖 [PRD A02 的资产前置、A10 的配置部分](../../../PRD.md)；配置、共享资产与规则身份以 [DESIGN 第 2 节](../../../DESIGN.md) 为准。

先提供主管和一个开发岗位必需的职责与方法，不一次写齐完整团队。岗位不硬绑定 Harness/模型；共享 Skill 逐目录链接，任务显式引用。保留官方 Herdr Skill，不以自建执行适配器替换。

## Acceptance criteria

- [x] 完成“登记项目 → 合并全局/项目/Run 配置 → 选择岗位执行配置 → 实际只读派发 → 读取结果”的可复现路径，不为接入修改业务代码。
- [x] 普通配置按全局 < 项目 < Run 合并；映射/列表处理一致，不增加通用 Task 级执行覆盖。安全限制不能按普通覆盖规则放宽。
- [x] 仅调整执行配置即可切换已支持 Harness；岗位内容和任务意图不改写，模型使用已验证的原生参数。
- [x] 两种 Harness 可读取同源的必需 Skill/支持文件；既有文件或软链接不被覆盖，断链、未知字段、无效引用和必需能力缺失明确失败。
- [x] 本次执行可输出脱敏配置快照和实际依赖规则的身份/指纹，不保存凭证、不扫描无关资产；运行中变更处置留给 05。
- [x] 展示的是实际只读结果，不冒充业务 Task 已验收；正式 Task/Attempt 协议由 03 完成，权限模式不替代用户授权。

## 验证与执行约束

用一个小型只读任务和必要的配置拒绝案例验证，不建设通用安装器、模型翻译器或配置框架。用户级安装/链接和权限变化另行确认；既有 Herdr 安装与 profile 不重复配置，YOLO 不作为默认。

## Comments

### 2026-10-13 · 实现、定向验证与环境阻塞

**结论：本票阻塞，未通过完整验收。** 只实施本票，不进入 03；triage `Status` 不表示验收完成。完整路径停在原生 Harness 启动门禁，尚未提交任何本票任务提示，不能把解析成功或工具测试当作实际只读结果。

**前置证据**：核对 01 的 `05/06/07/09/12/18/22/30/31/39` 命令和原生记录：缺参、无效目标、不支持 kind 均明确失败；两种 Harness 各一次提示、一次精确响应、零工具调用；Codex timeout 后无重发。旧基线原生记录哈希一致；Claude 01 日志旧哈希匹配前 27 行，随后仅追加 `cost-state`。官方 Herdr Skill 两路径同源，SHA-256 仍为 `b16ba0d9a22adbaf259d2022cd323801f8e51d530c94cb0cd23a69069292506b`。不重复安装、冒烟或修改既有 profile。

**实现变更**：新增主管/开发职责、两个共享方法 Skill、只读 Workflow/结果模板、三层样例及 `skills/orchestrator/scripts/configure.py`。标准库入口仅 `register / prepare`，采用 JSON 语法的 YAML 子集；不包装 Herdr、不建立模型翻译器或 Task/Attempt 状态机。快照记录配置来源及明确依赖指纹；项目规则支持文件使用显式清单，常见导入遗漏明确失败。DESIGN 2.4 增补实际入口，没有另建规格文档。

**授权与资源**：用户明确批准四个 `orchestrator/development` 用户级逐目录链接、外部本票记录，以及 `<READONLY_FIXTURE_REPO>` 新样例仓库的初始化和一次本地基线提交。该样例基线为 `222b3cc762bd3748a9c6aca4a0b8ed753775d271`，仅含 `README.md`、`AGENTS.md`，无远端；本项目未初始化/提交。已创建的测试 Pane 为 `PANE-M1-02-CODEX-INITIAL`（Codex 已退出至 Shell）、`PANE-M1-02-CLAUDE`（Claude 原生信任等待）。未替用户确认，未放宽权限，未用 YOLO。用户选择“保留现场，由我处理”；现场未关闭或删除。

**证据位置**：`<M1_02_EVIDENCE>/`。修改前 DESIGN/本票副本保留于此。项目登记及全局配置在 `<M1_02_CONTROL_ROOT>/`；修复后的可用准备输出为该目录 `runs/m1-02-fixture/{codex,claude}-readonly-v2/`。旧准备输出仅保留为审查前历史，不用于后续派发。

| 验证 | 实际命令/结果 | 证据 |
| --- | --- | --- |
| 语法与配置边界 | `ast.parse(configure.py)` 通过；`python3 -I -B test_configure_temporary.py` 的 12 项定向测试全部通过，覆盖覆盖顺序、限制并集/交集、未知字段、非法参数、断链、缺失能力、路径越界及不覆盖记录 | `01-local-setup.json`、`03-targeted-config-checks.json` |
| 项目登记 | `configure.py --home <control> register --project <control>/project-input.yaml` 退出 0，未改业务文件 | `02-fixture-baseline.json`、`04-project-registration.json` |
| 两种配置解析 | `configure.py ... prepare --global <control>/global.yaml --project-id m1-02-fixture --run examples/run-{codex,claude}.yaml --run-id {codex,claude}-readonly-v2` 均退出 0；角色/目标不变，生成 prompt 逐字节相同；执行配置分别来源于项目层及 Run 层 | `05-prepared-configurations.json`、`06-pre-dispatch-input-check.json`、`16-post-review-preparation.json` |
| Codex 实机启动 | `herdr agent start m1-02-codex --kind codex --pane PANE-M1-02-CODEX-INITIAL --timeout 30000 -- --profile herdr --model gpt-5.6-sol` 工具返回启动后，原生进程退出；`get/read` 返回 agent_not_found，按原 Pane 读取确认为 `account/read ... workspace routing discovery unauthorized (401)`；未派发、未重试 | `07`–`10` |
| Claude 实机门禁 | `herdr agent start m1-02-claude --kind claude --pane PANE-M1-02-CLAUDE --timeout 30000 -- --model fable --permission-mode manual` 返回 `agent_not_ready`；原生 UI 为新样例目录信任询问，未代按确认、未派发 | `11`–`13` |
| 独立审查与修复 | 一次 `code-review` 确认 5 个问题：常见凭证形式、资产引用绕过读范围、规则支持依赖遗漏、scope 软链接判断及配置来源哈希竞争。均已定点修复，5 个复现检查全部通过；未运行第二轮独立审查 | `14-review-fix-checks.json`、`15-independent-review-resolution.json` |
| 只读现场 | Git 工作区干净，样例文件哈希与基线一致；未产生实际任务响应，不能认定只读派发验收通过 | `17-fixture-unchanged.json` |

**勾选依据与缺口**：仅配置合并/边界和快照/明确依赖身份两项已有充分证据。逐目录同源链接和失败拒绝已验证，但两种 Harness 实际读取自有方法/支持文件及返回项目事实尚未验证，故包含这些条件的复合验收项不勾选。没有改写岗位提示词或任务意图，但本轮实际切换/结果仍受启动门禁阻塞。

**最小后续动作**：用户在 `PANE-M1-02-CLAUDE` 自行决定原生目录信任，并自行修复 Codex 认证/路由；收到用户明确“已处理，继续”后先检查现场，再判断是否可继续原定两次只读验收。若仍无法启动，保留 BLOCKED，不盲目重发、换模型或改权限。模型参数只复用 01 的本机证据，Claude 的 `fable` 是本地别名，不宣称服务端模型身份。

**验证与清理**：未跑无关全量套件；两份本次临时验证测试在实际通过并核对归属/指纹后已删除，输出及审查证据保留。未自动关闭用户要求保留的 Pane，未删除验收仓库或工作区。未联网检索；本票使用本地正式依据、原生 CLI 帮助及原始验收记录。

### 2026-10-13 · 用户解除门禁后续验收

**结论：本票通过。** 用户明确回复“已处理，继续”后先重新读取原 Pane 和配置指纹，没有把该回复直接当作工具已就绪。Claude 原会话已在 manual 模式就绪；用户恢复的 Codex 是无参数启动，未用于验收。确认它空闲后关闭本次旧测试 Pane `PANE-M1-02-CODEX-INITIAL`，从新建响应取得 `PANE-M1-02-CODEX-RETRY`，严格按 Run 配置以 `--profile herdr --model gpt-5.6-sol` 启动。项目/岗位/方法/任务意图不改写，未修改默认权限、凭证或 profile。

| 验收项 | 实际结果与证据 |
| --- | --- |
| 完整路径 | 已登记项目和两份 `*-readonly-v2` 准备输出经主管消费；真实 Herdr 启动、单次派发、等待/读取和源文件核对完成。配置解析不是最终验收替身。见 `04`、`16`、`19`、`21`–`34` |
| 三层与切换 | 开发 Harness 的 Codex 选择来自项目层，Claude 选择来自 Run 层；两份 prompt 逐字节相同。启动/原生记录分别为 Claude 本机 `fable` 别名映射 `gpt-6-astra`、Codex `gpt-5.6-sol`。见两个 Run 的 snapshot/dispatch-input、`21`、`26`、`34` |
| 同源方法实际生效 | Claude 原生记录为一次 `Skill(development)` 和 8 次成功 `Read`（含共享支持文件与 `~/.claude/skills` 发现路径）；Codex 为 7 次限定文件读取，实际返回岗位、Skill、支持文件、Workflow、模板、AGENTS、README 内容。两者均报告 `readonly-file-evidence-v1` 且没有无关读取/写操作。见 `34-native-result-reconciliation.json` |
| 实际只读结果 | 两者均准确报告 README 第 1 行项目名 `M1 Readonly Notes`、第 5 行模块 `notes`、第 7 行声明命令 `python3 -m unittest discover`，并明确未运行验证命令。完整原生结果保存在 `33-claude-actual-result.md`、`33-codex-actual-result.md`；结论只是 OBSERVED，不是正式业务 Task 验收 |
| 权限与不重发 | Claude 共享文件读取审批由用户在原生 UI 处理，执行全程仍显示 manual；Codex 原生 turn_context 为 `read-only / on-request`。Codex 唯一一次投递等待超时后仅 get/read/wait，原生记录证实两种 Harness 各只有 1 条任务提示；未重复派发或改模型。见 `22`–`30`、`34` |
| 最终差异与清理 | 样例 Git 状态为空、HEAD 仍为 `222b3cc762bd3748a9c6aca4a0b8ed753775d271`，两个输入文件哈希不变；角色/方法/输入依赖未变。按原授权确认本次两个执行者身份及空闲后关闭 `PANE-M1-02-CLAUDE`、`PANE-M1-02-CODEX-RETRY`，其他会话与样例仓库保留。见 `35`、`37`、`38` |

**实际失败与核清记录**：
- 一次 `pane process-info <id>` 使用位置参数被本机拒绝，改为 `--pane <id>` 后成功（`20`、`21`）；无副作用。Claude blocked 状态下请求长历史被 Herdr 拒绝，按错误提示改读 visible（`24`、`25`）。
- Claude 完成后 Herdr 长历史仍仅返回尾屏；没有追加模型提示或要求写文件，按已确认会话 ID 从原生记录取得完整结果和工具调用，证据来源在 `34` 明示。
- 最终整文件指纹检查发现 Codex profile 变化，`35` 保留该项失败而非改写为全通过。进一步核对确认旧 profile 的全部 17 行字节仍为完整前缀，仅追加 `[tui.model_availability_nux]` 两个提示计数；权限段完全未变，原生执行仍为只读/on-request。`37` 记录原/新哈希、追加内容和核清依据；原快照未覆盖、profile 未修改。这不是规则采用或权限变更，不实现/宣称工单 05 的运行中变更机制。

**收口范围**：12 项初始配置定向检查 + 5 项审查缺陷复现通过；已做一次独立 review，5 个确认问题均修复，不机械增加第二轮 review 或全量测试。先前阻塞阶段的 Comments 与证据保留为历史。本票全部六项现在均有实际证据；只完成 M1 工单 02，不代表 PRD A01/A02/A10 的完整产品场景全部通过，不涉及开发写入权限、正式 Task/Attempt 或跨项目完整复用。不自动提交本项目、不推送、不重置、不删除工作区，停止，不进入 03。

### 2026-10-13 · 后续新会话默认更新

用户最新明确并二次确认的项目决定，仅面向主管/员工未来新会话取代本票当时“YOLO 不作为默认”的策略，当前规则见 DESIGN 第 2.4 节。本票原始命令、失败尝试、快照、只读结果、验收勾选和通过结论全部保留；历史 profile 的拒绝测试不能证明新默认仍有同样沙箱限制。`readonly` 工作流继续限制行为，新默认不扩大业务授权，其实际模型调用仍待验证。


