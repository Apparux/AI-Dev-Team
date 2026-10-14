# 带身份的阶段执行

方法标识：`identified-delivery-v1`。仅在明确投递的 Task/dispatch 使用此协议时采用；旧只读观察继续使用 `readonly.md`。Run/dispatch 的 mode 缺省为 `non-business`；仅显式获准时使用 `versioned-test-fix`。Task/Result 顶层不增加 mode。

1. 读取本 Attempt 的 `dispatch.yaml`、`binding.json`、任务卡、Run 与授权记录、`required_reads` 和输入成果。核对 mode、Run/Task/Attempt/phase/role 与实际执行者、Pane/会话。任一不符则返回 BLOCKED，不替换身份或目录。
2. 本次最高权限启动和 mode 都不是业务授权或路径沙箱。记录只写自己 Attempt 内的 `artifacts/`、`evidence/`、提交草稿及唯一 `result.yaml`；工作区权限按下方模式分支执行。生产代码、原工作区、其他 Attempt、配置与运行环境保持不变，不推送、不调用其他 Agent。
3. `work/fix` 按对应模式产出成果；fix 必读 `failure_result` 指向的失败结果及其诊断证据。有上游依赖时读取 `dependency_results` 中固定版本的成果/结果/报告；不依赖旧聊天。`verify/review` 读取已接受 work 的结果和成果，以独立 executor_id 和新 session_id 核验（已空闲 Pane 可以复用），保持输入/输出成果版本相同，不修改被验收内容。
4. 至少运行一个与任务验收直接相关的实际检查，按模式保存真实命令输出及版本证据。项目声明的验证命令与真正运行的检查分开，不自动运行全量命令；无运行则明确未验证，不能编造 PASS/退出码。
5. 按统一结果模板填写全部字段，并应用下方模式字段规则。`executor` 逐字段取自 `binding.json`，身份/规则/输入版本取自 dispatch。Review 的 findings 绑定输入版本指纹，阻塞项未关闭不能 PASS。
6. 使用 `python3 -I -B <共享源>/skills/orchestrator/scripts/state.py --run-dir <Run目录> publish --request <本Attempt提交草稿>` 原子发布唯一结果。发布拒绝时保留草稿和错误；不覆盖结果、不改派发记录或全局状态。publish 是独立入口，仅发布、不推进状态，后续验收归主管。
7. 发布后停止本阶段写入，在终端报告结果路径和遗留问题，等待主管核对并退出本次执行。

## non-business（缺省）

仓库/worktree 只读，不修改测试或提交。`work/fix` 产生本 Attempt 内的非业务成果，记录路径与 SHA-256；PASS 的 output artifacts 非空。成果版本保持 `head_commit == base_commit == baseline`，`changes.code: []`。

检查 cwd 为本 Attempt 的 `dispatch.cwd`。证据 JSON 字段为 `argv`（字符串列表）、`cwd`、`exit_code`（整数）、`stdout`、`stderr`，保存在本 Attempt `evidence/`。结果 `checks` 条目为 `{argv, cwd, exit_code, evidence}`，evidence 为 `{path, sha256}`；不添加新模式专用的 head_commit，公共 Result 模板保持此格式。

## versioned-test-fix（显式授权）

仅一个 Task、`depends_on: []`。测试写入路径来自 `authorization.write_paths`，不是 Task 新字段，也不能以 Task scope 扩大许可。工作区内 context 的历史输入读取 baseline 的 Git 字节，不以当前文件作历史 artifact；规则/Skill 指纹仍固定，漂移即阻塞。

1. `work/fix` 仅改 Run workspace 内已授权的 tracked regular 测试文件，并完成本地 commit；生产实现不变。先改动、提交，再在该最终 commit 上做定向验证；后续若再提交，必须重新取得新 commit 的最终检查证据。`verify/review` 仅核验同一 commit，不修改源码或提交。获准验证命令可产生项目既有 Git 忽略规则覆盖的本地构建输出（如 `target/`）；不修改忽略规则，也不将这些输出当作已提交交付物。
2. input/output 仍为 `{base_commit, head_commit, artifacts}`：base_commit 固定 baseline，head_commit 为真实完整 Git commit，artifacts 必须 `[]`。输出等于本 Attempt 输入或为其后代；发布前 HEAD 等于 output head 且工作区 clean。`changes.code` 必须是从本 Attempt input commit 到 output commit 的实际相对路径排序列表；work/fix PASS 需要非空提交差异，verify/review 为 `[]` 且 input/output 相同。`changes.artifacts` 始终为 `[]`。
3. 验证命令只执行 `authorization.validation_argv` 中逐项匹配的许可 argv。`authorization.validation_inputs` 固定 Run `inputs/` 内的外部验证配置；按 `{path, sha256}` 核对后只读使用，缺失或漂移即阻塞，不自行替换配置。检查 cwd 必须为 `run.workspace`，不是 `dispatch.cwd`；记录文件仍只存本 Attempt `evidence/`，不能把命令 cwd 当证据目录。网络访问不获授权；依赖或命令条件不足时报告阻塞，不安装或联网补齐。
4. 每个 `checks` 条目恰为 `{argv, cwd, exit_code, evidence, head_commit}`；对应 evidence JSON 恰为 `{argv, cwd, exit_code, stdout, stderr, head_commit}`。evidence 仍使用 `{path, sha256}` 引用；命令、cwd、退出码与 head_commit 必须和真实调用及结果一致，head_commit 等于 `output_version.head_commit`。
5. PASS 的 checks 只放该最终 commit 上 exit_code 为 0 的实际检查。基线预期失败独立保存于本 Attempt `evidence/`，标明基线 commit，并通过 `handoff_refs` 字符串列表引用，不放进 PASS checks。实际失败或受阻填写 FAIL/BLOCKED；若 dirty、版本或其他门禁导致无法发布，保留真实诊断与草稿并向主管报告，不伪造 PASS 或改写状态。

高权限进程可以绕过协作接口，本协议不宣称能防任意 Shell 改写；完成当前阶段后等待主管，不扩展为恢复或并发执行。
