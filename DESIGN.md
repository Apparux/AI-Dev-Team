# AI Dev Team — DESIGN

> 版本：1.0 · Grill 已确认 · 产品尚未实施，工具实测基线见第 9 节  
> 产品边界与验收：`PRD.md` · 实施依赖：`TASKS.md`

> 发布说明：本文及工单 01–04 的机器路径、会话、Pane/Tab、PID 和 owner 使用一致的脱敏定位符；原始证据保留在本地，公开定位符不能作为真实执行目标。

## 1. 架构与职责边界

主管 Agent 加载 Orchestrator Skill，在 Herdr 内复用官方 Herdr Skill / CLI。业务层只负责岗位、任务阶段、交接、审批记录、验收和业务状态；不实现通用多 Agent Runtime。

| 责任 | 实现边界 |
| --- | --- |
| 终端、Pane、Harness 启动、输入、输出和运行状态观察 | 复用 Herdr，参数以实际安装版为准 |
| 有条件的原生会话恢复、显式 worktree 操作 | 复用 Herdr / Git；不推定所有 Harness 等价 |
| Run / Task / Attempt、依赖、门禁和业务恢复 | AI Dev Team 的 Skill、结构化文件和必要的小工具 |
| 工具权限 | Harness 原生机制及用户已有规则；业务审批记录不替代执行权限 |
| 最终代码是否合格 | 对应版本的成果、实际检查和必要的独立 Review，不采用终端状态代替 |

Role、Workflow、业务状态不以 Herdr 专属语义定义。Pane ID、Agent 名称等只进入 execution 元数据；保持这一边界，不提前实现第二 Backend 或 Adapter SDK。

V1 的信任前提是受监督、遵守协议的 Agent。唯一写入者、审批门禁和目录归属是协作与防误操作机制，不是抵御任意 Shell 写入的安全沙箱。

## 2. 共享资产与配置

### 2.1 资产与加载

只维护一份共享源：`roles/` 定义职责，`skills/<name>/SKILL.md` 定义方法，`workflows/` 定义阶段/门禁，`templates/` 定义交付格式。岗位引用所需 Skills 和执行配置，不把职责、模型与工具命令混成一份固定提示词。

逐个 Skill 目录建立软链接：

- `~/.claude/skills/<name>` → 共享的 `skills/<name>`。
- `~/.agents/skills/<name>` → 同一个共享目录，供 Codex 发现。

不替换整个发现目录；名称冲突、已有文件或链接先检查并请求处理，不自动覆盖。安装属于用户环境变更，实施时单独说明范围、回滚方式并取得授权。共享位置由安装配置指定，不写死开发机器路径。

主管明确投递必读 Skill、项目规则和任务卡引用，不只依赖原生隐式触发。断链、支持文件无法读取或必要能力缺失应阻塞；不能仅凭“已加载”自报认定生效。两种 Harness 的软链接发现、支持文件路径及实际遵循情况均需实测。

### 2.2 配置规则

普通字段按 **全局默认 < 项目配置 < Run 覆盖** 合并；映射按键覆盖，标量/列表整体替换。未知字段、无效引用和相互矛盾的配置明确报错。Task 选择 Run 内已配置的岗位，不再增加通用 Task 级执行覆盖。

以下仅示意 AI Dev Team 自有配置，不是 Herdr 原生格式：

```yaml
assets_root: /path/to/ai-dev-team
execution: { backend: herdr }
harnesses:
  claude_code: { kind: claude, start_args: [--permission-mode, bypassPermissions, --model, fable] }
  codex: { kind: codex, start_args: [--yolo, --model, gpt-6.1-sol] }
roles:
  manager:
    harness: claude_code
    definition: roles/manager.md
    skills: [skills/orchestrator]
  backend:
    harness: claude_code
    definition: roles/backend.md
    skills: [skills/development]
  reviewer:
    harness: codex
    definition: roles/reviewer.md
    skills: [skills/review]
workflow: workflows/bugfix.yaml
policies:
  review_max_rounds: 2
```

- `harnesses` 中的条目是执行配置；可有多个条目使用同一种 `kind`，但采用不同原生模型参数。Role 选择配置，岗位内容不嵌入模型名称。
- 模型由目标 CLI 的原生参数选择，不建立模型翻译器；本机实测后记录有效参数。
- 项目差异至少包括项目标识、Git 仓库、现有验证命令、工作范围、项目规则及必要的资源隔离方式。无需为无关项目配置数据库或端口。
- 安全限制不按普通覆盖规则放宽：允许范围取各层约束的交集，强制审批/Review 要求取并集；冲突时阻塞。具体例外走审批，不修改宿主或项目的权限规则。
- 快照不得含密钥、Token 或其他凭证；凭证由 Harness 既有环境处理，启动参数也必须检查敏感内容。

### 2.3 运行中变更

Run 保存解析后的配置快照，以及所用 Role、Skill、Workflow、项目规范及必需支持文件的路径和版本/内容指纹，不扫描无关资产。普通配置修改只影响新 Run。

后续派发、验收和恢复前核对相关规则指纹。变化时暂停受影响的新派发，记录差异和在途任务；结果在规则对账前不得推进完成。用户决定采用新规则并重验、恢复原规则或停止。不得自动覆盖共享源、静默热更新，或假定在途 Agent 已冻结。V1 不建设不可变资产仓库或完整版本管理系统。

### 2.4 M1 工单 02 的最小入口

自有资产为 `roles/manager.md`、`roles/developer.md`、`skills/orchestrator/`、`skills/development/`、`workflows/readonly.md` 与 `templates/readonly-result.md`。职责不含 Harness/模型；每个 Skill 的 `resources.json` 声明必需支持文件。两个用户发现目录仅按授权新增 `orchestrator`、`development` 的逐目录链接，指向同一共享源；官方 Herdr Skill 保持原样。

`skills/orchestrator/scripts/configure.py` 使用 Python 3.9+ 标准库，接受 JSON 语法的 YAML 子集。`examples/global.yaml`、`examples/project.yaml` 和 `examples/run-{codex,claude}.yaml` 给出本票范围；两份 Run 样例仅岗位 Harness 选择不同。

```sh
python3 <共享源>/skills/orchestrator/scripts/configure.py --home <外部状态目录> register --project <项目配置>
python3 <共享源>/skills/orchestrator/scripts/configure.py --home <外部状态目录> prepare --global <全局配置> --project-id <项目标识> --run <Run覆盖> --run-id <新Run标识>
```

登记要求已有 Git 根和基线 commit，不写业务仓库。准备步骤只输出解析快照、逐字段来源、实际依赖指纹及主管派发输入；不安装、不包装 Herdr、不建立 Task/Attempt 状态机。主管按 `skills/orchestrator/SKILL.md` 加载官方 Herdr Skill，消费所选原生参数并进行实际派发、读取和源文件核对。prepare 成功不是执行成功或业务验收。

字段/格式、路径归属、有限原生参数与失败规则见 `skills/orchestrator/references/configuration.md`。执行配置区分下述已批准的新会话默认与 9.3–9.4 的历史验证组合；历史组合不限制后续经明确批准的新默认，也不证明新组合已可用。外部状态目录、链接、验收仓库及模型调用仍须具体授权；原生权限模式不形成业务写入授权。

**本项目未来新会话默认（2026-10-13，用户明确要求并二次确认）**：以下为主管和员工新建会话的启动默认；授权来自本次用户决定，而非第 9 节的一次性测试。只改本项目启动参数，不修改用户全局配置、既有 profile 或历史快照，不重启、改造既有会话。

| Harness | 新会话启动默认 |
| --- | --- |
| Codex | `codex --no-daemon --yolo --model gpt-6.1-sol` |
| Claude Code | `claude --permission-mode bypassPermissions --model fable` |

Claude 只更新权限模式，保留已选模型；表中的 `fable` 是当前选择，不强制覆盖其他已选模型，也不改变 9.3 所述本机别名的证据边界。经 Herdr 启动时，将对应原生参数传入 `agent start ... -- <native-args>`。

- **风险与业务边界**：Codex `--yolo` 跳过原生审批并关闭原生沙箱；Claude `bypassPermissions` 跳过原生权限审批。宽权限进程仍须遵守角色/任务授权范围、业务审批、Git 门禁和单写入者协议；cwd、文件锁及状态入口校验不是安全沙箱，不能阻止任意 Shell 越权。此默认不授权额外任务或跨过工单 04 后的人工关口。
- **只读语义**：`readonly` 工作流仍是行为限制，不代表进程受只读沙箱约束。历史 `--profile herdr` 的文件写入、socket 和网络拒绝实测只适用于当时配置，不能外推到新默认；既有 profile 保留为历史只读入口，不作为当前写入配置。
- **验证与失败**：工单 03 首个 Run 的 Codex 因工具环境 Pane 冲突而 BLOCKED，原记录保留。经用户批准，`m1-03-identified-delivery-retry-1` 在同一仓库的新 worktree 中显式使用 `codex --no-daemon --yolo --model gpt-6.1-sol`，真实 Pane/会话匹配；Codex work 和独立 Claude `bypassPermissions` verify 均发布同协议 PASS，主管核验后完成状态并由新进程重新读取。当时仅为该 Run 的隔离覆盖；本次将隔离方式收口为新会话默认，不将其表述为共享后台环境已修复。证据见 `<M1_03_RETRY_RUN>/evidence/16-work-native-reconciliation.json`、`33-verify-native-reconciliation.json`、`38-final-reread-and-workspaces.json`。Claude 启动选择仍为 `fable`，本机原生/UI 标签为 `gpt-6-astra`，不据此断言提供商身份。模型、参数或必需能力不可用时明确 `BLOCKED`；默认之外的配置变更仍需明确授权，不静默换模型、profile 或回退到共享 daemon。

**隔离默认补测（2026-10-13）**：本次批准将 `--no-daemon` 加入本项目共享配置的 Codex 默认，模型与权限选择不变。两个不同 Pane 的真实只读探针分别执行一次；Pane/Tab/workspace、两个 Codex 会话 ID 和 cwd 均匹配主管侧真实身份，工具父进程分别属于各自 Pane，第一个会话存活时第二个没有串用其身份。证据为 `<CODEX_ISOLATION_DIAGNOSTICS>/evidence/15-isolated-a-verified.json`、`20-isolated-b-verified.json`。探针使用 `gpt-6.1-sol`、既有 `herdr` profile 的 read-only/on-request，未启用 YOLO；普通 daemon 对照因额度不足在工具执行前停止，不记作本轮故障复现或 daemon 已修复。新 Run 核对实际解析参数，旧快照不刷新。Herdr 正常升级不锁版本、不触发整套 M1 重验，只对不兼容或实际异常补最小检查。

## 3. Run、Task 与阶段执行协议

### 3.1 状态目录与写入归属

```text
~/.ai-dev-team/
├── config.yaml
├── projects/<project-id>.yaml              # 也可引用项目内差异配置
└── runs/<project-id>/<run-id>/
    ├── run.yaml                           # 目标、解析配置、规则指纹、基准与交付分支
    ├── owner.json                         # 当前主管身份与接管记录引用
    ├── state.json                         # Run / Task 状态、当前执行、修复计数
    ├── events.jsonl                       # 状态变更和重要决定
    ├── approvals/<action-id>.json
    ├── tasks/<task-id>/
    │   ├── task.yaml
    │   └── attempts/<attempt-id>/
    │       ├── dispatch.yaml              # 主管写入的阶段、角色、身份和投递记录
    │       ├── result.yaml                # 此次执行者写入
    │       └── evidence/                  # 检查、Review 等证据
    └── reports/
```

路径为建议布局，运行记录不提交进业务仓库。全局配置和项目登记不充当跨 Run 共享任务状态。

- 每个 Run 只有一个主管写全局状态、任务卡和审批决定；员工只写自己的本次结果/证据及获授权的代码范围。
- 首次写代码前就要有 Run / Task / Attempt 身份、工作区归属和基本持久记录，不等到恢复模块才补。
- 同一 Run 的主管进入与状态更新需要最小排他/身份检查；不能只靠“请勿同时启动”的提示。旧主管是否存活不明时不自动抢占，不仅凭超时或陈旧时间戳清除归属。
- 接管须核对旧主管和在途执行，取得明确决定并记录新身份；已交接的旧主管不能继续按原身份更新状态。
- 记录使用同目录临时文件与原子替换；事件带身份、修订号、前后状态、原因和时间。快照与事件不能假装跨文件原子事务：不一致时停止推进，对账后追加修正记录。
- 仅为身份检查、结构校验、原子写入和对账补必要的轻量工具；不据此建立服务、消息队列或通用存储层。

### 3.2 Task 与 Attempt

Task 至少包含 `run_id / task_id / owner_role / objective / scope / depends_on / workspace / context_refs / acceptance / required_stages`。必需阶段和对应岗位在派发前确定；低风险可不要求独立 QA/Review，但必要验证不省略。拒绝不存在的依赖和循环依赖。

每次阶段派工建立新的 Attempt，至少记录：

- `run_id / task_id / attempt_id / phase / role`，其中 `phase` 为 `work / verify / review / fix`；`work` 包括代码或其他交付物产出。
- 输入成果版本、规则指纹、验收要求、结果绝对路径。
- execution 元数据：Harness 执行配置、Agent 身份、Pane ID、工作区、基准版本、投递意图及观察结果。

Attempt 是业务派工身份，不是 Herdr 的可靠投递回执。必须先落盘投递意图，再调用 Herdr；工具超时或返回成功都不能单独证明任务未执行或已完成。

结果必须回传相同的 Run / Task / Attempt / phase / role，并包含 `outcome: PASS|BLOCKED|FAIL`、摘要、成果路径、实际变更、输入/输出版本、检查命令/退出码/证据、遗留风险和交接引用。代码结果记录基准/结果 commit 及未提交状态；非代码成果记录路径与内容指纹。Review 结果另带 findings 和结论。

主管检查结构、身份、当前阶段、代码/成果版本与证据。迟到、重复、旧规则下或已撤销执行的结果只保存为历史，不能覆盖当前结果或推进状态。取消待确认期间收到结果，也不能据此自动转成 completed。

### 3.3 会话与依赖

- 不同 Task 默认新会话，不建设岗位池。同 Task 修复可复用身份明确的开发会话，但仍建立新的阶段执行记录。
- 同一工作区同一时刻仅一个写入者；投递身份不明或旧写入者未停止时，不启动替代写入者。
- QA/Review 消费同 Task 已上报的成果，不建成“等待该 Task completed”的循环依赖。Reviewer 使用与实现者分离的会话/执行者。
- 跨 Task 依赖只在上游 completed 后解锁，并绑定所消费的成果版本。上游成果后续改变时，主管阻塞受影响的下游推进并重新检查，不静默沿用旧交接证据。

## 4. Herdr 调度协议

1. 检查 `HERDR_ENV=1`、本机 CLI/必需 Skills、执行权限、规则指纹和工作区；不把环境变量存在等同于 server 健康或能力已通过验收。
2. 核对本 Run 主管归属和当前阶段，选择最小岗位，落盘任务与投递意图。
3. 通过官方 Skill / CLI 创建或选择位置，从 JSON 返回取得真实 ID，不猜 Pane ID。`agent start` 需要已有空闲 Shell Pane。
4. 复用 `herdr agent start <name> --kind <kind> --pane <id> [-- <native-args>]`；派发短指令，明确任务、阶段、Skill 和结果路径。具体参数以本机版本验证为准。
5. 使用有界观察/等待，检查用户控制请求、`agent read`、结果和 Git 状态；不长时间困在一次阻塞等待里。具体超时能力在 T01 验证，不自造 CLI 参数。
6. 原生审批或提问界面先读取并交给用户，不自动按确认。无法识别的状态也不能视为许可。
7. 按协议和证据推进 Task；`idle/done`、员工 PASS、Prompt 等待返回都不是充分条件。

`wait` 不绑定某个业务 turn。`timeout / agent_prompt_stalled / unknown` 不证明提示未投递，禁止盲目重复发送。Ctrl+C 可能仅打断当前 turn，必须观察实际停止结果；不假定存在统一的 `agent stop`。

主管需在 Herdr 内按官方 Skill 使用执行能力；退出后不由本系统自动唤醒。暂停/取消从主管接收并记录请求后按协议处理，不承诺进程级即时急停。

## 5. 状态、审批与恢复

### 5.1 状态与门禁

| 对象 | 状态/字段 | 含义 |
| --- | --- | --- |
| Run | `active / paused / awaiting_approval / completed / cancelled / failed` | `awaiting_approval` 表示当前没有可派发的安全工作或被必要审批阻断 |
| Task 主路径 | `pending → running → reported → verifying → reviewing → completed` | 可显式跳过不要求的独立 Review；开发自测可作为验证证据，不必额外派 QA |
| Task 异常 | `blocked / needs_fix / interrupted / failed / cancelled` | 保存原因、当前/历史执行和下一步，不凭状态名推定安全可重试 |
| Approval | `requested / approved / rejected` | 每个待批动作独立记录，不从 Harness 授权模式推定批准 |
| 取消控制 | `cancellation_requested` 与未确认停止列表 | 取消未确认时 Run 保持暂停并显示原因，不冒充 cancelled |

- 开发结果有效后进入验证；验证或 Review 发现确认缺陷进入 `needs_fix`，修复后重新上报、复验和必要复核。关键证据不足不能跳到 completed。
- **暂停**：停止本 Run 新派发和新危险动作；列出在途执行，允许安全落盘，不伪称进程冻结。
- **审批等待**：阻塞受影响任务及下游；其他无依赖的安全任务可以继续。暂停或取消控制优先于这种继续规则。
- **失败升级**：必需 Task 超过修复上限或关键验收无法完成时，整个 Run 暂停新派发；不因其他任务完成而判定 Run 完成。用户决定继续、调整范围或停止。
- **完成**：所有必需 Task、最终集成门禁和待处理审批均已闭合，没有仍可能修改交付物的在途操作，报告绑定实际最终版本。
- **failed** 表示已确认不能继续的运行，不把仍等用户决定的情况伪装成终态。取消彻底确认后才进入 cancelled。

### 5.2 审批对象

审批记录至少包含动作 ID、Run / Task / Attempt、拟执行动作及目标范围、相关版本/规则、风险原因、用户决定与是否已经执行/执行结果是否明确。高风险动作不得仅写“允许继续”而无具体对象。

批准只用于对应动作，不跨任务、重派、范围变化或不明结果自动复用。拒绝不得在恢复时变成许可；它取消尚未执行的动作，不隐式回滚已存在代码。执行结果不明时先对账，不重新消费批准去重做外部操作。

业务批准不能越过 Harness 或用户已有权限限制。无法可靠限制的高风险动作保留阻塞记录并交给用户执行；不为此自建通用拦截层。

### 5.3 恢复与取消对账

| 现场 | 处理 |
| --- | --- |
| 原主管或写入者可能仍在运行 | 核对归属和会话，观察或明确交接；不抢占、不并行重派 |
| 当前 Attempt 的结果已落盘 | 核对身份、规则和实际成果版本后重新验收，不只读 PASS |
| 进程已消失但已有代码/成果 | 标为 interrupted，保存现场；核对可用证据和接续策略后才允许新写入 |
| 消息投递或副作用不明 | blocked，请求人工处理；无结果文件不等于从未执行 |
| 旧 Attempt 或取消中的迟到结果 | 留存并参与对账，不覆盖当前执行、不自动完成 |
| 取消已请求但停止未确认 | 停止新派发，持续显示未停止项；不删除现场、不宣告取消完成 |

恢复顺序：主管归属 → Run/Task/事件/审批 → Herdr 实际状态 → 结果与 Git/成果 → 规则指纹 → 记录接续决定。新 Attempt 或换 Harness 必须有明确的对账依据、允许的配置和单写入归属；不承诺恰好执行一次。

客户端 detach、Herdr server 重启、Harness 原生 resume 是不同事件。前者可保留进程；server 重启不保留原进程，仅恢复布局及符合条件的原生会话。任何原生 resume 都不直接恢复业务完成状态。

## 6. 多 Run、工作区与集成

### 6.1 工作区与输入

- 每个 Run 在明确基准 commit 上拥有独立 Git worktree、独立集成分支及运行目录。识别仓库真实归属，避免同一仓库的不同路径/别名被当成可共用工作区。
- 用户原工作区只用于读取约定事实，不自动提交、搬走或覆盖未提交修改。任务依赖未提交内容时先请用户明确基线，不悄悄忽略。
- 单写入流程可直接使用本 Run 的独立工作区；只有存在独立并行写入需求时，再分配 Task 级 worktree/分支。新 Task 会话不意味着必须再复制一个工作区。
- 分配分支、创建 worktree 和本地提交必须在明确的允许范围内，并遵守原有权限规则；未获授权时阻塞相应操作。
- 默认串行；接口、共享文件 Owner 和依赖明确后才并行。不同 Run 不能写对方的工作区、分支、状态或结果。

### 6.2 集成责任与最终证据

主管从已有开发岗位指定集成 Owner，不增加新岗位，不亲自承担业务修复。Owner 在本 Run 的集成工作区逐项整合已验收成果，检查基准、提交、实际差异和未提交状态。原写入者不得同时修改被整合的成果。

冲突、越界变更或用户修改出现时暂停并报告，不自动覆盖；不得 `reset --hard`、强推、丢弃冲突或自动删除工作区。

多 Task 的 Run 将最终集成作为明确的交付单元，依赖输入 Task 的 completed 成果。单 Task 的 Run 可直接在其最终版本完成同等门禁，不为形式再建一个 Task。

在最终集成 commit 上运行与验收和集成风险相关的检查；必要时独立 Review 集成差异及受影响路径。未变化、仍适用的 Review 证据可以引用，但不能用各分支分别 PASS 推断集成 PASS。后续修改使受影响的检查/Review 失效，应重验，而不是机械重跑所有检查。

交付时本 Run 的代码工作区无未交代的变更或后台写入，报告给出基准 commit、最终 commit、分支和证据。只完成本 Run 分支交付；跨 Run 合并、推送、主分支整合及其复验不由 V1 自动执行。

### 6.3 测试资源

项目配置按实际需要提供 Run 级端口、临时目录、测试数据库/schema 等隔离输入，验证命令必须使用这些输入。复用项目已有能力，不建设通用环境供应或资源排队系统。

不能确认隔离时，只阻塞相关共享资源操作，由用户安排独占执行；其他独立工作可继续。普通只读数据和安全共享缓存不强制复制。不能将 worktree 隔离外推为网络服务、数据库或后台进程隔离。

## 7. QA、Review 与有限修复

1. 开发者提交真实成果与检查证据，主管核对可进入验证的条件。
2. 按风险使用现有定向检查；QA/Reviewer 默认不修改被验收业务代码，必要实现或测试改动交回开发范围处理。
3. 根据 Workflow/风险执行独立 Review。Finding 包含稳定 ID、定位与受检版本、严重度、具体证据、是否阻塞及理由、修复/复核状态。
4. 违反验收条件、新增的已确认正确性错误/回归及实际安全等缺陷阻塞；风格、可选优化、未恶化的范围外旧问题不阻塞。不确定的判断不能冒充确认缺陷，关键验证缺口也不能被当成 PASS。
5. Review 结论区分 `PASS / BLOCKED / INCONCLUSIVE`；证据不足或争议无法解决时主管交给用户，不自行豁免已确认缺陷。
6. 修复进入新的阶段执行，重跑受影响检查；需要独立复核的 finding 由 Reviewer 明确关闭，新增回归按新 finding 记录。
7. 每 Task 默认最多两轮修复循环。进入新的修复循环即计数，不按 finding 分别发预算，也不因换会话、Harness 或 Attempt 重置；超限或关键证据无法取得时按 Run 级失败升级处理。

是否新增测试取决于真实回归风险和关键行为；不强制 TDD、覆盖率指标或庞大测试矩阵。没有实际运行的检查标为未验证，临时验证物的清理遵循项目规则，验收证据必须保留。

## 8. 最终报告

报告引用实际证据，不复制完整终端聊天；至少包含目标与完成范围、交付分支/版本、通过/失败/未验证的检查、Review 及修复结论、未解决事项和需要用户执行的动作。

无法满足必需门禁时仍可输出进展报告，但不能把 Run 标成 completed。变更范围需要调整时先取得用户明确决定并更新验收基线，不能由主管悄悄删掉失败项。报告注明未跨 Run 合并、未自动发布。

## 9. 官方依据、当前证据与待实机验证

以下为本轮实际查阅的官方资料；**官方描述、源码静态证据、本机端到端验收是不同证据层级**。

| 来源 | 可确认的边界 |
| --- | --- |
| [官方 Herdr Skill，固定提交](https://github.com/herdrdev/herdr/blob/241b99cd397bb642eaabcfee1647bcecffb26be1/skills/herdr/SKILL.md) | Herdr 内的启动/读取/投递/等待/交互；默认 sibling pane + 同 cwd，不自动提供 worktree；wait 不绑定业务 turn |
| [Herdr Agent automation](https://herdr.dev/docs/agent-automation/) / [CLI reference](https://herdr.dev/docs/cli-reference/) | 启动依赖已有 Shell Pane；使用真实返回 ID 和原生启动参数，具体语法以安装版为准 |
| [Agent CLI 源码](https://github.com/herdrdev/herdr/blob/241b99cd397bb642eaabcfee1647bcecffb26be1/src/cli/agent.rs) | 本轮静态核对的命令分派没有统一 agent stop；发送 Ctrl+C 不等于已确认停止 |
| [Session state](https://herdr.dev/docs/session-state/) / [Socket API](https://herdr.dev/docs/socket-api/) | detach 与 server 重启不同；原生恢复有条件，事件历史不能替代业务持久记录 |
| [Worktree 源码](https://github.com/herdrdev/herdr/blob/241b99cd397bb642eaabcfee1647bcecffb26be1/src/worktree.rs) | 复用 Git worktree 操作；不据此推定自动整合和最终验收 |
| [Claude Code Skills](https://code.claude.com/docs/en/skills#where-skills-live) | 用户 Skill 目录条目可以是指向其他目录的软链接 |
| [Codex Skills](https://learn.chatgpt.com/docs/build-skills) | 用户发现目录为 `$HOME/.agents/skills`，支持跟随 Skill 文件夹软链接 |

### 9.1 已有本机实测证据

| 检查 | 实际结果与边界 |
| --- | --- |
| 版本与环境 | Herdr 客户端/服务端均为 0.9.3，协议兼容、无需重启；Claude Code 2.1.296、Codex 0.162.1；`HERDR_ENV=1`。已存在的 integration 为 Claude v10、Codex v8，本轮未修改 hooks |
| 官方 Skill 安装 | 从本机 `herdr --skill` 导出原文到 `~/.agents/skills/herdr/SKILL.md`；`~/.claude/skills/herdr` 链接至同一目录。两条路径与内嵌原文 SHA-256 一致；未替换整个发现目录 |
| Skill 与基本交互 | Claude Code 当前会话及新会话、Codex 新会话均实际加载官方 Herdr Skill；父会话经 Herdr 启动、投递并读取两种 Harness 的响应。尚未验证 AI Dev Team 自有岗位及完整 Task/Result 交接 |
| Claude 调用 Herdr | 新会话执行环境检查与当前 Pane 查询成功，已核对原生工具记录；目录信任和命令审批曾阻塞，Herdr 可观察到 blocked。测试末尾 UI 显示 auto mode，故不把本次记录视为 manual 权限流程全程验证 |
| Codex 默认只读限制 | 显式只读沙箱可执行普通命令并读取 socket 文件信息，但查询 Herdr 报 `Operation not permitted`；只放行该 Unix socket 后查询成功，定位为 socket 连接权限问题 |
| Codex 按需 profile | 新增 `~/.codex/herdr.config.toml`，仅 `--profile herdr` 启用。继承 `:read-only`，使用 limited 网络策略和代理，只允许 Herdr socket；实际 Codex 会话查询成功。文件写入、其他 Unix socket 均被拒绝，未授权网站返回 `403 blocked-by-allowlist`。原 `config.toml` 未编辑 |
| Codex YOLO 对照 | 经一次性明确授权，以 `--yolo` 启动的测试会话显示 YOLO mode，加载 Skill 并成功查询 Pane；该结果不证明沙箱门禁有效，也不是默认策略或后续运行的授权 |

本轮没有业务代码改动、worktree 创建、server 重启或完整产品验收。临时测试 Pane、目录和权限探针已清理，原生 CLI 会话记录保留。未在 `PATH` 定位 Pi/OpenCode 的结果仍只是入口检查，不构成支持结论。

**定位已有证据**：官方 Skill 的 SHA-256 为 `b16ba0d9a22adbaf259d2022cd323801f8e51d530c94cb0cd23a69069292506b`。原生测试会话标识：Claude `SESSION-TOOLS-CLAUDE`；Codex profile `SESSION-TOOLS-CODEX-PROFILE`；Codex YOLO `SESSION-TOOLS-CODEX-YOLO`。这些是证据定位标识，不是可复用的业务任务或当前在线 Agent。

### 9.2 历史已验证的最小启动入口

本节保留旧只读入口的命令与证据；本项目未来新会话默认以 2.4 为准，不从本节推导。

在已获准使用的 Herdr 环境中，以真实创建响应取得的空闲 Pane ID 为目标：

```sh
herdr agent start <name> --kind codex --pane <actual-pane-id> -- --profile herdr
```

本机定向 profile 的配置方式参见 [Codex 官方配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)。Profile 自身已继承只读权限，不再叠加 `--sandbox read-only` 去覆盖其 socket 例外。该配置是按需的只读调度/核查入口，不能直接作为写代码员工的执行配置；写入场景需要另行确认能力和授权。

允许连接 Herdr socket 不是 API 方法级只读过滤，仍须遵守 Skill 和人工审批。它与 `--yolo` 都不替代业务审批；本项目没有因此设置全局默认或未来会话的自动授权。

### 9.3 工单 01 增量实测（2026-10-13）

**结论：本票工具级最小失败边界通过，不是 A01 或业务流程验收。** 本次先核对 9.1 所列原生会话中的实际工具调用及返回，再仅补以下缺口；未重装 Herdr、Skills、integration 或 profile。版本仍为 Herdr 客户端/服务端 0.9.3（protocol 22，兼容）、Claude Code 2.1.296、Codex 0.162.1。

证据根目录：`<M1_01_EVIDENCE>/`（下表文件名均相对该目录）。命令记录含实际 argv、起止时间、退出码、stdout/stderr；`31-baseline-reuse.json` 保存已复用原生记录的路径、指纹与核对行号。该目录仅为本票验证证据，不代表 Run/Task/Attempt 业务状态系统已实现。

| 对照项 | 本票实测结果与边界 | 证据 |
| --- | --- | --- |
| 既有安装、加载、启动、投递、读取及 Codex profile | 复用 9.1；原始 Claude 与 Codex profile 会话确有 `test "${HERDR_ENV:-}" = 1 && herdr pane current --current` 及成功返回。旧 YOLO 记录仅为历史对照，不再次运行、不扩展授权 | `01-herdr-status.json`–`03-codex-version.json`、`31-baseline-reuse.json` |
| Claude 原生模型参数 | `herdr agent start m1-01-claude --kind claude --pane PANE-M1-01-CLAUDE --timeout 30000 -- --model fable --permission-mode manual` 成功。返回 argv 保留参数；本机既有 `ANTHROPIC_DEFAULT_FABLE_MODEL=gpt-6-astra`，UI 与实际响应记录均为 `gpt-6-astra`。证明的是当前环境的别名解析与调用，**不是 Anthropic Fable 模型身份或跨环境同名映射的验证** | `12-claude-start.json`、`13-claude-start-read.json`、`15-model-resolution.json`、`21-claude-prompt.json`、`25-claude-result-read.json`、`30-native-reconciliation.json` |
| Codex 原生模型参数 | `herdr agent start m1-01-codex --kind codex --pane PANE-M1-01-CODEX --timeout 30000 -- --profile herdr --model gpt-5.6-sol` 成功；argv、UI、原生 `turn_context.model` 一致，取得指定标记响应。原生记录仍为 `read-only / on-request`，未叠加 sandbox 参数或使用 YOLO | `18-codex-start.json`、`19-codex-start-read.json`、`28-codex-reconciled-read.json`、`30-native-reconciliation.json` |
| 无效原生参数 | `claude --model` 返回退出码 1：`argument missing`；`codex --model` 返回退出码 2：`a value is required`。停止这两个无效请求，不删参数重试、不切换模型 | `05-claude-missing-model.json`、`06-codex-missing-model.json` |
| 无效目标 | 故意使用非法测试目标 `M1/INVALID` 执行 `agent prompt ... --wait --timeout 1000`，退出码 1、`agent_not_found`。不改用当前/聚焦 Pane；前后既有 Agent 的 Pane、会话身份与状态序列一致 | `07-invalid-target.json`、`04-agents-before.json`、`36-agents-after.json` |
| 缺失必需 Harness 能力 | 在本次创建的空 Shell Pane 上要求 `--kind m1-missing-kind`，退出码 2：`unsupported interactive agent kind`；随后读取确认该 Pane 未启动 Agent。不换 kind、不删约束，终止该负向请求。有效场景使用的是另行明确指定的测试请求 | `08-split-claude.json`、`09-missing-harness-kind.json`、`10-pane-after-rejection.json`、`11-claude-shell.json` |
| 投递超时后先对账 | Codex 唯一一次标记投递使用 `--wait --timeout 100`，退出码 1、`timeout`。紧接着 `agent get` 仍为 idle，但 `agent read` 已显示原提示和 Working；不把该 idle 当未投递或完成。只做 get/read、`agent wait ... --until done --timeout 30000` 和原生记录核对，**没有重发** | `20-dispatch-intent.json`、`22-codex-prompt-timeout.json`–`24-codex-read-after-timeout.json`、`26-codex-bounded-observation.json`–`30-native-reconciliation.json` |
| 权限、身份与收尾 | 用户明确批准两个 sibling 测试 Pane、各一次无业务模型调用及空闲后关闭；Pane ID 来自 split JSON，未猜测有效 ID。Claude UI 为 manual，Codex 为既有只读 profile；两份原生记录各 1 条测试用户消息、1 条精确标记响应、0 次工具调用。未发送任何信任/权限确认；本次没有出现需要处理的原生审批。两个测试 Pane 在核对身份和 done 后关闭，既有会话和调用方焦点保留 | `08-split-claude.json`、`16-split-codex.json`、`30-native-reconciliation.json`、`32-claude-before-close.json`–`37-caller-after.json` |

本次原生会话定位：Claude `SESSION-M1-01-CLAUDE`；Codex `SESSION-M1-01-CODEX`。精确标记分别为 `M1_01_CLAUDE_20261013T005350`、`M1_01_CODEX_20261013T005350`。原生证据的模型字段是 Harness 记录，不能据此独立证明服务端底层模型身份。

**最小复现与停止规则**：先检查必需文件/能力和本机模型别名解析，再从获准创建响应取得新 Pane ID；上表 ID/名称是历史证据，不可照抄为在线目标。只用已核准原生参数，不自动降级。投递前记录本次目标、标记和单次发送意图；若遇到 `timeout / agent_prompt_stalled / unknown`，先 get/read、有界观察及原生记录对账。只有实际匹配响应才能证明本次测试产生结果，单独的 `idle/done` 或 wait 返回不够。身份、输出或副作用仍不明时明确 BLOCKED，请用户决定；不得重发或另起替代执行者。缺少必需 Skill/支持文件或出现原生审批时同样停止，不自动修改环境或确认提示。

### 9.4 工单 02 配置驱动只读验收（2026-10-13）

**工单 02 通过，仅覆盖配置与一次只读任务，不是正式业务 Task 或完整 A01/A02/A10 验收。** 在单独获准的隔离样例 Git 项目中完成登记、三层解析、选岗与 Harness、实际读取同源方法、单次投递和结果核对。实现入口见 2.4。

- 验收状态根：`<M1_02_CONTROL_ROOT>/`；项目 `m1-02-fixture`。两份 `runs/m1-02-fixture/{codex,claude}-readonly-v2/` 保存配置来源、依赖指纹及派发输入。岗位、方法和任务 prompt 不变，执行选择分别来自项目层与 Run 层。
- 证据根：`<M1_02_EVIDENCE>/`。`03` 的 12 项配置检查和 `14` 的 5 项审查缺陷复现通过；一次独立审查确认的问题及修复见 `15`，临时测试文件已按项目规则清理。
- 原生执行：Claude `SESSION-M1-02-CLAUDE`，参数仍为 `--model fable --permission-mode manual`；Codex `SESSION-M1-02-CODEX`，参数仍为 `--profile herdr --model gpt-5.6-sol`，原生上下文为 `read-only / on-request`。两者实际读取职责、Skill、支持文件、Workflow、模板和指定项目文件，并返回正确项目事实及 `readonly-file-evidence-v1`。工具调用与唯一任务提示对账见 `34`，完整结果见 `33-{claude,codex}-actual-result.md`。
- 原生信任/读取审批由用户处理；Codex 首次 401 未触发自动凭证修复。用户恢复的无参数 Codex 未用于验收，按已批准执行配置启动新测试会话后才派发。Codex 单次投递 timeout 后只观察，没有重发。Claude Herdr 历史读取只能取得尾屏时，使用对应原生会话记录核验完整答案，没有额外模型调用。
- 样例文件与 commit 均未改变；只关闭已核对空闲的本次测试 Pane，证据与仓库保留。Codex profile 的整文件哈希因 TUI 提示计数追加而变化：旧权限内容逐字节保留，原/新哈希和追加内容在 `37` 明示；未覆盖原快照、修改 profile 或实现运行中规则变更机制。

### 9.5 尚待验证

- 自有正式 Task/Result 协议和实际代码交付；两个方向的主管—员工完整业务闭环。02 仅完成最小主管/开发职责与只读方法，未一次建设完整团队。
- 非空但不存在的模型名与服务端拒绝等变体；01 的缺参/不支持 kind、02 的有限配置拒绝与受控临时断链/缺失支持文件案例不外推完整错误矩阵或跨环境模型映射。
- working 起点下的等待、`agent_prompt_stalled / unknown` 的独立故障复现、连接中断及副作用无法对账场景；本票只覆盖一次 idle 起点的真实投递超时，不证明 exactly-once。审批拒绝、暂停、取消、迟到结果和业务状态是否一致仍待后续票验收。
- Ctrl+C 的实际停止语义、重复主管、安全接管及规则变更检测。
- 主管退出、客户端 detach、隔离 server 重启、原生 resume 后的业务对账。
- Run 内并行、同项目多 Run、Git/测试资源分别隔离、逐项集成及最终版本门禁。
- 第二个不同技术栈项目只靠差异配置复用。

能力基线和必要复现入口只维护在本节；具体未完成项对应 TASKS 中的前置验收，不把后续恢复或完整业务场景倒置为工具冒烟的完成条件。A01–A10 尚未完成整体验收，不创建独立 compatibility 规格或完整规格副本。
