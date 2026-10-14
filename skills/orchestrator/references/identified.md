# 身份与持久状态入口

本入口处理受监督的 `non-business` 非业务交付与显式获准的 `versioned-test-fix` 版本化测试修复，协议均为 `identified-delivery-v1`。配置仍按 `configuration.md` 合并；没有数据库、调度循环、自动重派、自动接管或完整恢复。

## 启动与身份

先明确仓库、固定基准、独立分支/worktree、外部 Run 目录及授权。Git 工作区分配由主管执行获准的原生 Git 命令，状态工具不会选择、初始化或创建仓库。新会话默认及边界见 `DESIGN.md` 2.4；已经运行的会话不因此重启。

`state.py --run-dir <目录> initialize --request <初始化JSON>` 接受 Run/项目/仓库/worktree/分支/基准、owner_id、configuration（home/global/run）、authorization 文件引用、repair_limit、tasks 和可选 mode。mode 缺省为 `non-business`，新分支必须显式指定 `versioned-test-fix`；Run 与 dispatch 保存 mode，Task/Result 顶层 schema 不增加 mode。任务卡格式见 `templates/identified-task.json`。Run 内各阶段岗位在配置中预先选定，不提供 Task 级 Harness 覆盖。初始化拒绝已有或不完整的状态目录；外部目录可已有本票备份/输入/证据，但不能已有 ownership/state/tasks。

初始化在该 worktree 专用 Git 管理目录排他发布 `ai-dev-team-owner.json`，绑定 Run、记录目录、工作区和分支；不同记录目录不能认领同一个 worktree。这个新增管理记录不是业务文件或权限配置，不自动移除/抢占；初始化中断或归属不明时保留现场并阻塞。

## versioned-test-fix 授权

仅接受一个 Task，`depends_on: []`。authorization 必须恰好包含以下字段，不加字段或省略：

```text
decision mode run_id task_id repository workspace branch baseline record_root
attempt_result_write business_code_write test_code_write local_commit employee_sessions evidence_write
original_workspace_write remote_write network_access write_paths validation_argv validation_inputs reason
```

- `decision: approved`、`mode: versioned-test-fix`；Run/Task 与仓库、工作区、分支、基准、记录目录均匹配本次请求，reason 写明批准范围。
- `attempt_result_write/test_code_write/local_commit/employee_sessions/evidence_write` 均为 true；`business_code_write/original_workspace_write/remote_write/network_access` 均为 false。
- `write_paths` 来自 authorization，不是 Task 字段；精确列出 Task scope 内已有的规范相对路径，必须为基线已跟踪的 regular 文件（`100644 blob`），不接受目录、通配符或软链接。`validation_argv` 为非空的许可命令 argv 数组列表，逐项固定可执行文件及参数。
- `validation_inputs` 为必需列表，可为空；每项为 `{path, sha256}` 且文件必须位于本 Run `inputs/`。Run 保存这些外部验证配置引用，状态边界核对指纹；与规则一样，缺失或漂移即阻塞，不自动更新授权或改用真实配置。

初始化工作区必须处于 baseline 且 clean；输入 context 与规则指纹的固定方式见 `configuration.md`。本模式只增加显式许可的测试修改与本地 commit，不构成安全沙箱或额外业务授权。

## 派发与状态

主管更新统一使用：

```sh
python3 -I -B <共享源>/skills/orchestrator/scripts/state.py --run-dir <Run目录> <动作> --request <动作JSON> --owner <主管ID> --generation <代际> --revision <已读修订号> --reason <原因>
```

| 动作 | 请求字段与完成条件 |
| --- | --- |
| dispatch | task_id / attempt_id / phase / executor_id。落盘唯一目录与投递意图，返回配置和 cwd；尚未投递。 |
| bind | task_id / attempt_id / executor / pane_id / session_id / evidence。先按官方 Herdr 创建/启动，从实际 JSON/原生记录取得真实身份；evidence 引用 Run evidence 下的原生观察记录。绑定后才投递一次。 |
| stopped | 与 bind 相同。核对结果已落盘、身份和空闲，主管按用户授权实际停止本次进程，以该身份的退出/停止证据解除写入占用；idle/done 单独不能证明 stopped 或 Task 完成。 |
| accept | task_id / attempt_id。只读取该 Attempt 的固定结果路径，核对身份、阶段、规则、成果及真实检查输出；测试修复另核对 HEAD、clean 与许可路径。PASS 只进入下一门禁。 |
| finish | task_id。所有必需阶段已核验且版本不变、无在途写入、依赖闭合时写版本绑定报告；测试修复再次核对 HEAD、clean、许可路径及最终 commit 的检查输出。其他必需 Task 未完成则 Run 仍 active。 |
| handoff | new_owner_id / approval（文件引用）。仅无待处理执行时，依据明确批准记录交接并增加代际；旧身份失效。不按时间戳/超时抢占。 |

先落盘 dispatch，再启动执行、bind，再单次 prompt。work → verify 串行执行，verify/review 的 executor_id 和 session_id 均须与成果生产者不同；可以是同一岗位，但不能复用同一执行会话。工具超时不证明未投递；只 get/read/有界观察，身份或停止不明时保留占用并报告 BLOCKED，不生成替代 Attempt。新的 fix 计数一次；失败超限暂停 Run，换 Harness/会话不重置。

## 协议与证据

员工使用同一个 `templates/identified-result.json`，并按 `skills/development/references/identified.md` 写入本 Attempt。`publish` 是独立的员工入口，不需要主管身份，不能写全局状态；原子排他发布不覆盖已有结果。身份错误/旧/重复提交拒绝，草稿保留为历史；主管不能将终端文字伪造为员工文件。

配置/任务/派发/结果采用 JSON 语法，`.yaml` 只是文件名。带指纹的文件引用为 `{path, sha256}`（`handoff_refs` 保持字符串列表）；成果版本为 `{base_commit, head_commit, artifacts}`。Review 复用结果 envelope，findings 含 id/location/version/severity/evidence/blocking/disposition；version 是输入版本对象的规范 JSON SHA-256。审批/报告字段见对应模板。

两种模式的成果门禁不同：

- `non-business` 保持 `head_commit == base_commit == baseline`，work/fix PASS 需要非空 artifact 成果，`changes.code: []`。
- `versioned-test-fix` 的 input/output 均绑定真实 Git commit，`base_commit == baseline`、`artifacts: []`；HEAD 必须等于输出 commit，Run 与原工作区保持 clean，原工作区仍在 baseline。baseline 之后每个提交仅改许可测试文件，不接受 merge、删除/改型或越界后再回退掩盖。`changes.code`、最终 commit 检查与基线失败证据的填法见员工 `identified.md` 的对应分支；按该分支调整 Result 字段，保留公共模板的旧模式格式。

结构校验不能证明检查真实发生。主管对照任务验收、实际原生工具调用、检查原文和成果内容确认；一份合法 JSON 或员工 PASS 不足以完成 Task。任务卡中的 acceptance 是主管与独立核验者的检查清单，不是工具能理解的自然语言断言。测试修复报告的 `business_task_accepted: true` 仅表示真实项目测试修复已验收，必须明确 `test-fix / production implementation unchanged`；不是生产实现已修复的声明。

## 一致性与再次读取

`inspect` 不修改状态。每个状态动作都需文件锁、主管身份/代际和预期修订号。快照为同目录原子替换，事件先落盘同步；修订号、事件链、快照指纹和修复计数必须一致。跨文件不是原子事务，部分事件或快照不一致一律停止推进，保留现场供人工对账。

在新进程运行 `state.py --run-dir <目录> inspect` 可读取任务路径、状态、主管身份、当前/待处理 Attempt 和证据引用；不会自动继续、重派或声称完整中断恢复。结果/状态工具只防协议内误操作，不抵御高权限 Shell 绕过；同 Run 采用保守单写入者，不实现跨 Run 的通用调度/锁服务。
