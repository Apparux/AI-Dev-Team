# 03: 带执行身份和工作区归属的交付演练

Milestone: M1 — 跑通最小协作
Status: ready-for-agent

**What to build:** 在独立 Run 工作区中完成一次不修改业务代码的交付演练；用户可以从持久记录辨认谁执行了什么、结果属于哪次派工，并在重新读取记录时避免旧结果或第二位主管错误推进状态。

**Blocked by:** 02 — 由项目与 Run 配置驱动一次只读任务。

**Execution gate:** 2026-10-13 本票通过。02 实际验收已核实；首个 Run 的身份冲突与失败记录完整保留。用户批准新的隔离 Run/worktree、Codex 单次 `--no-daemon` 覆盖及两阶段调用后，真实 Codex work → 独立 Claude verify → 结果受理 → completed 已跑通，新进程可重新读取完整状态与证据。三个 Git 工作区均干净、固定基准和输入指纹不变。仅完成非业务演练，不宣称完整中断恢复；停止，不执行 04。

## 上下文与范围

对应 [TASKS T03](../../../TASKS.md)，建立 [PRD A03、A06 的基础保护](../../../PRD.md)。遵循 [DESIGN 第 3、5、6 节](../../../DESIGN.md)；首次业务代码写入前必须完成本票。

Task 是可验收交付单元，work/verify/review/fix 是内部阶段，每次派工建立独立 Attempt。先实现最小身份、协议、基本状态、单主管和工作区归属；本票只证明记录可再读取，不承诺完整中断恢复。

## Acceptance criteria

- [x] 在获准基准上分配 Run 独立工作区/分支，完成“任务卡 → 阶段派发 → 本次结果 → 核验 → 状态记录”的非业务交付路径；用户原工作区不被写入或自动提交。
- [x] 两种 Harness 能使用相同结果协议，明确 Run、Task、阶段、Attempt、执行者、成果版本、真实检查和证据归属；结果路径不被其他 Attempt 覆盖。
- [x] 结果通过结构、身份、阶段与成果版本检查后才可推进；错误身份、重复/旧结果、循环依赖及无证据的 completed 推进被拒绝。
- [x] 通过受支持的状态入口阻止同 Run 第二主管写入及交接后旧身份继续更新；归属不明时阻塞，不以超时为由自动抢占。不宣称这能防止任意 Shell 越权。
- [x] 状态原子替换、事件和修复计数有必要一致性检查；重新读取时可定位待处理执行，不依赖终端聊天。快照/事件不一致不能默默猜测。
- [x] 按角色/任务显式限定代码与结果的允许写入范围；新会话按 DESIGN 第 2.4 节使用已批准的宽权限进程，但不扩大业务写入授权，历史只读 profile 不是当前写入配置。同工作区不派发两个写入者。

## 验证与执行约束

用一个正常交付和已识别的身份/状态拒绝案例验证，优先原生文件和 Git 能力，仅补必要的确定性小工具。不建数据库、服务、队列或完整流程引擎。无获准 Git 仓库、归属或权限时停止，不替用户初始化或选择其他仓库。

## Comments

### 2026-10-13 · 最小实现、权限默认变更与真实执行阻塞

**结论：本票阻塞，未通过完整验收。** 只实施 03；按用户额外要求同步其他相关票据/说明的前瞻性启动默认，未执行其他票据。`ready-for-agent` 不代表本票已通过或可以继续 04。

**前置与授权**：读取正式规则及 PRD/DESIGN/TASKS，核对 02 两份实际结果、原生调用对账和最终清单。清单 17 个项目文件指纹匹配；Codex 原生记录整文件匹配，Claude 验收时前 64 行完整匹配。复用既有安装、链接与工具证据，不重装、不重复冒烟。用户明确批准既有仓库 `<READONLY_FIXTURE_REPO>`、基准 `222b3cc762bd3748a9c6aca4a0b8ed753775d271`、分支 `m1-03-identified-delivery`、独立工作区 `<M1_03_BLOCKED_WORKSPACE>` 及外部 Run 记录；不初始化本项目或其他仓库。

**用户纠正的默认**：后续本项目主管/员工新会话采用 Codex `--yolo --model gpt-6.1-sol`、Claude `--permission-mode bypassPermissions` 且沿用已选模型（本次 fable）。经风险/回滚说明和二次确认后更新项目配置、规则指引及相关票据说明；01/02 历史命令与证据不改写，不修改用户全局配置或既有 profile，不重启原主管。高权限模式不扩大本票业务范围，不是路径沙箱；未因默认变化获得提交、推送、删除工作区、重启共享服务或额外派发授权。

**实现**：复用三层配置/路径/指纹校验，抽出 `resolve_configuration`；新默认参数支持单独的 `--yolo`，无 profile 的选择不读取旧 profile。新增 `scripts/state.py`、非业务方法/Workflow 及任务、结果、审批、报告模板。员工只通过原子排他发布写自己的结果；主管通过显式动作、flock、身份/代际和修订号推进。任务/Attempt、原生执行身份、规则与成果版本均绑定；事件和快照不一致阻塞，不自动修复。worktree 专用 Git 管理目录内的排他归属记录将其绑定到唯一 Run 记录根，不修改业务文件。没有数据库、服务、队列、自动调度或完整恢复系统。

**记录根**：`<M1_03_BLOCKED_RUN>/`。下表证据文件均相对于其 `evidence/`；修改前 25 个既有文件的备份位于 `backups/pre-change/`，指纹清单见 `00`。Run 配置和授权输入在 `inputs/`，任务在 `tasks/fixture-report/`，阻塞报告在 `reports/blocked.json`。

| 验证/动作 | 实际命令与结果 | 证据 |
| --- | --- | --- |
| 静态与参数检查 | 对 configure.py/state.py 执行 `ast.parse`；新默认及旧显式配置 3 个正向、缺值/重复/越界等 4 个拒绝通过；JSON 语法通过 | `01-static-config-checks.json` |
| 独立工作区 | `git -C <既有仓库> worktree add -b m1-03-identified-delivery <获准worktree> 222b3cc...` 退出 0；无新提交 | `02-worktree-allocation.json` |
| 首轮定向状态验证 | `python3 -I -B test_state_temporary.py`：27 项通过，覆盖正常合成流程、旧/错误/重复结果、非法完成、依赖循环、单写入者、主管交接/并发、修复上限及事件不一致 | `03-targeted-test-command.json`、`03-targeted-state-checks.json` |
| 一次独立审查与修复 | 一次 code-review 确认 15 项缺陷，已定点修复；`python3 -I -B test_review_fixes_temporary.py` 的 22 项复验通过。覆盖跨 Task 错结果、嵌套证据、原仓库资产范围、唯一工作区归属、历史成果、Review 字段、fix/依赖交接及参数误拒绝等 | `07-review-fix-command.json`、`07-review-fix-checks.json`、`08-independent-review-resolution.json` |
| 真实身份与持久化 | `state.py initialize`、`dispatch` 后退出写入进程，再以新进程 `inspect` 读取同一个 work-001 待处理执行；排他归属记录在该 worktree 专用 Git 管理目录中 | `09`–`11` |
| 新默认实际启动 | `herdr agent start m1-03-work --kind codex --pane PANE-M1-03-BLOCKED --timeout 30000 -- --yolo --model gpt-6.1-sol` 成功；本地 `/status` 查询取得原生会话 ID，再通过 `state.py bind` 绑定。原生记录为 `gpt-6.1-sol / never / danger-full-access` | `12`–`17`、`24` |
| 唯一正常模型任务 | `herdr agent prompt m1-03-work <work-prompt> --wait --timeout 30000` 超时后只观察，没有重发；原生记录确认只有 1 条匹配的正式任务提示。`/status` 是本地查询，不是第二次模型任务 | `18`–`25` |
| 实际身份拒绝 | 员工实际读取同源方法、派发/绑定/授权和规则；发现工具进程 HERDR_PANE_ID=PANE-M1-02-CODEX-INITIAL、HERDR_TAB_ID=TAB-M1-SHARED，而本次 Pane 为 PANE-M1-03-BLOCKED。CODEX_THREAD_ID/SESSION_ID 与绑定的 `SESSION-M1-03-BLOCKED` 一致。员工返回 BLOCKED，未写文件、未运行报告断言、未发布结果；主管未制造替代结果 | `24-work-native-identity-reconciliation.json`、`25-work-single-submission-and-tools.json` |
| 已授权清理与停止记录 | 核对本次执行者空闲、Pane/进程身份后仅关闭 PANE-M1-03-BLOCKED，确认原前台进程退出；`state.py stopped` 保存实际停止证据和 BLOCKED 原因，修订号到 4。未重启共享后台服务或 Herdr，未关闭其他会话 | `26-authorized-work-pane-cleanup.json`、`27-work-stopped-state.json` |
| 最终 reread / Git | 新进程 `inspect` 成功定位未受理 work-001；原仓库和 Run worktree 的 HEAD、README/AGENTS 指纹不变、Git 状态均干净 | `28-final-reread-and-workspaces.json` |
| 真实 Run 的拒绝检查 | 第二主管 finish、当前主管无结果 finish、重复 initialize 均退出 1；state/events/工作区归属记录的前后指纹完全不变 | `29-real-run-rejections.json` |

**状态边界**：持久状态保留未受理的当前 Attempt，Run/Task 主路径字段仍为 `active/running`，不表示原生进程仍在运行；`stopped.json`、事件原因及阻塞报告明确记录已停止且需人工处置。没有 accept/finish，没有 Claude verify，没有 completed，也不会自动接续。已证明的是独立进程退出后的记录再读取，**不是完整主管中断恢复**。

**勾选依据**：第 3–5 项已有确定性正/拒绝案例、真实 Run 拒绝和重新读取证据。正常非业务交付没有跑完，两种 Harness 的实际同协议结果尚未取得；角色授权/写入范围和单写入保护已验证一部分，但实际员工结果写入未走通。因此第 1、2、6 项保持未勾选，不能以合成检查或成功启动代替验收。

**未解决事项与下一步最小动作**：核清并修正新 Codex 工具子进程继承旧 HERDR 上下文的来源，或由用户明确决定可接受的身份对账方式；当前证据仅确认冲突，不把“共享后台服务继承旧环境”猜测宣称为已查明根因。涉及共享服务/用户环境的改动和额外模型执行须另行明确授权。保留原 Attempt、归属、工作区与证据；不改绑定掩盖冲突，不自动重发、新建替代执行或进入 04。

**清理与检索**：两份临时测试源码在通过并核对归属后已删除（`04`、`08-review-temporary-test-cleanup.json`）；合成夹具仅作验证证据保留，不冒充产品执行。未运行无关全量测试，未联网检索，未提交/推送/重置或删除工作区。状态查询中的账号行在纳入绑定证据前已脱敏，未保存凭证。

### 2026-10-13 · 经授权隔离重演通过

**最新结论：本票通过，六项验收均有证据。** 此结论来自新 Run 的真实交付，不是把上一次 BLOCKED 改写成成功，也不是恢复了旧 Run。

**新增授权与最小修复**：用户要求继续，并通过计划审批批准同一既有仓库、同一基准下的新分支/worktree/记录根 `m1-03-identified-delivery-retry-1`，以及两个串行阶段调用和仅本次空闲 Pane 的清理。官方本地 `codex --help` 明确支持 `--no-daemon`；只给本次 Run 增加这一参数，保留 `--yolo --model gpt-6.1-sol`。`configure.py` 仅增加精确允许组合和无值开关解析，配置说明增加该显式覆盖；`state.py` 未改，没有补恢复模块。修改前备份位于新 Run 的 `backups/pre-change/`。未修改未来会话默认、未由主管改写用户级配置、未重启共享服务。

**本次证据根**：`<M1_03_RETRY_RUN>/`。以下文件均相对于其 `evidence/`；新工作区为 `<M1_03_RETRY_WORKSPACE>`。

| 验证/动作 | 实际命令与结果 | 证据 |
| --- | --- | --- |
| 预检、备份、参数支持 | 原仓库/旧 worktree 干净且基准一致；`ast.parse` 通过，直接调用 `parse_args` 的 4 个正例、6 个拒绝例通过。对新增允许组合和开关解析做一次小范围自查；不重复此前全量独立审查 | `00-retry-preflight-backup.json`、`01-isolation-parameter-checks.json` |
| 独立资源和派发 | `git worktree add -b m1-03-identified-delivery-retry-1 <新工作区> 222b3cc...` 退出 0；`state.py initialize/dispatch/bind` 记录配置、工作区归属、任务、Attempt 和真实执行身份 | `02`–`09` |
| 真实 Codex work | `herdr agent start m1-03-retry-work --kind codex --pane PANE-M1-03-WORK --timeout 30000 -- --no-daemon --yolo --model gpt-6.1-sol` 成功。工具进程 Pane=PANE-M1-03-WORK、两个 Codex 会话 ID 均为 `SESSION-M1-03-WORK`，与绑定相符。原生 `source=cli`、模型 `gpt-6.1-sol`、`never/danger-full-access`；正常任务匹配计数为 1 | `06`–`16` |
| 报告与实际断言 | work 实际生成 `artifacts/project-facts.json`；内联 Python 对照 README 第 1/5/7 行、三项事实及 SHA-256 的断言退出 0。原生调用输出与保存的 argv/cwd/exit/stdout/stderr 一致；`state.py publish` 成功且不推进状态 | `16-work-native-reconciliation.json`、work Attempt 的 `result.yaml` 和 `evidence/project-facts-check.json` |
| 真实结果身份拒绝 | 从本次真实结果复制测试封套，分别替换为旧 Run 身份和错误原生会话；`state.py publish` 均退出 1，明确拒绝对应身份。state/events/真实结果指纹不变。这不是声称旧 Run 曾产出员工结果 | `19-real-result-identity-rejections.json` |
| 单写入者与 work 受理 | 确认本次 work 空闲、身份匹配后关闭 PANE-M1-03-WORK，进程 PID-M1-03-WORK-A/PID-M1-03-WORK-B 退出；再执行 `stopped/accept`，之后才 `dispatch verify` | `17`–`21` |
| 真实独立 Claude verify | `herdr agent start m1-03-retry-verify --kind claude --pane PANE-M1-03-VERIFY --timeout 30000 -- --permission-mode bypassPermissions --model fable` 首次因目录信任等待；用户手动确认后，绑定独立会话 `SESSION-M1-03-VERIFY` 并只投递一次核验任务。原生记录为 bypassPermissions；CLI 选择 fable、原生/UI 标签 gpt-6-astra，不据此断言提供商身份 | `22`–`33` |
| 独立实际核验 | 两个内联 Python 检查均退出 0：身份/阶段/规则/已受理 work/干净 Git，以及独立报告字段、行号、路径和双 SHA-256。实际环境 session/Pane 与绑定匹配且不同于 work；核验未改变成果，input_version=output_version。相同协议 publish 成功 | `33-verify-native-reconciliation.json`、verify Attempt 的 `result.yaml` 和两份检查 evidence |
| 完成和重新读取 | 仅关闭已确认空闲的 PANE-M1-03-VERIFY，进程 PID-M1-03-VERIFY 退出、主管 PANE-M1-03-MANAGER 保留。`state.py stopped/accept/finish` 退出 0，Run/Task 均 completed、revision=10。前一写入进程退出后，新进程 `inspect` 退出 0，pending 为空 | `34`–`38` |
| 最终范围核对 | 原仓库、旧 worktree、新 worktree 的 HEAD 均为固定基准，Git 状态干净，README/AGENTS 指纹不变。旧 Run 的 run/state/events/阻塞报告及旧 worktree 归属记录未改变；状态实现指纹与前次交付一致 | `38-final-reread-and-workspaces.json` |

**验收依据**：第 1、2 项由本次真实 Codex work、独立 Claude verify、同协议结果和 completed 报告补齐；第 3–5 项复用此前已通过且状态实现未改变的 27 项检查、22 项审查修复复验、3 项真实 Run 拒绝，并增加本次结果身份拒绝和完成后独立进程读取；第 6 项由明确授权、实际工具调用、三工作区不变、各 Attempt 独立结果，以及 work 停止后才启动 verify 的记录补齐。文件锁和 cwd 仍不是高权限 Shell 沙箱。

**成果入口**：新 Run 的 `reports/fixture-report.json`；员工成果为 `tasks/fixture-report/attempts/work-001/artifacts/project-facts.json`，两个阶段结果分别为 `work-001/result.yaml`、`verify-001/result.yaml`。报告绑定固定成果和两份已受理结果，明确只验收非业务演练，不代表业务任务已交付。

**边界与未解决事项**：本次 `--no-daemon` 隔离下身份冲突未复现，完整交付通过；共享后台环境旧值的最终来源仍未证明，也未修复共享后台服务。旧 Run 保持其原失败状态和冻结记录，不绕过规则变化校验。没有自动接管、自动重派或完整中断恢复。本票剩余验收阻塞为零，但这些范围限制继续适用。

**收尾**：两阶段的等待曾超时，均只观察已有执行，没有重发。记录器曾误将 Herdr 文本按 JSON 解析、漏识别 Codex custom_tool_call，均按实际格式修正，未新增模型调用。未创建临时测试源码，所有检查为内联执行；原先两份临时测试已清理。未执行全量测试、联网检索、提交/推送/reset 或工作区删除；用户手动完成原生目录信任，不由主管代按。两个本次测试 Pane 已关闭，证据与新旧工作区保留。停止，不执行 04。
