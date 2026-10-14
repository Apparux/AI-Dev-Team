# M1 配置入口

使用 Python 3.9+ 标准库，无依赖安装。`*.yaml` 样例采用 **JSON 语法的 YAML 子集**；入口只接受该语法，不实现通用 YAML。相对 `assets_root` 以全局配置文件所在目录解析，项目仓库以项目配置文件目录解析；岗位、Skill、Workflow、模板相对共享源，项目规则/范围/任务文件相对仓库。

`examples/project.yaml` 使用公开占位路径。使用前复制为 Git 忽略的 `examples/project.local.yaml`，将 `project.repository` 填为真实且已有基准提交的 Git 根目录，并核对声明的 scope/rules 文件存在，再以该私有副本登记。占位路径不能直接使用；解析器不展开 `$HOME` 等环境变量。

```sh
python3 <共享源>/skills/orchestrator/scripts/configure.py --home <外部状态目录> register --project <项目配置>
python3 <共享源>/skills/orchestrator/scripts/configure.py --home <外部状态目录> prepare --global <全局配置> --project-id <已登记标识> --run <Run覆盖> --run-id <新的Run标识>
```

完成 register 的条件是项目真实 Git 根与基线 commit 可读、必需字段有效，且新登记成功。已有登记明确失败，业务仓库不写入。项目资源本票仅接受 `{ "mode": "none" }`；声明的验证命令只记录、不运行。

完成 prepare 的条件是三层配置和引用通过校验，输出新目录内的 `snapshot.json`、`dispatch-input.json`、`prompt.txt`。没有派发、安装或状态推进副作用。主管从输出读取参数，用户无需拼每次启动指令。

## 合并与边界

- 普通配置全局 < 项目 < Run；映射递归按键合并，列表和标量整体替换。`field_sources` 记录普通字段的最终来源，`sources` 记录三个输入的路径和指纹。
- `assets_root` 只在全局定义；项目身份、仓库、现有命令、工作范围、项目规则与资源只在项目层定义；目标、选岗和任务文件只在 Run 定义。不存在 Task 级执行覆盖。
- 项目规则引用的必读支持文件在 `project.rule_support_files` 显式列出；与 `project.rules` 一起检查、投递和记录指纹。常见的独立行 `@文件` 导入与本地 Markdown 链接若未列入清单则阻塞；自然语言中的其他必读依赖由登记者明确列出，不扫描仓库猜测依赖。
- `policies.allowed_paths` 按路径包含关系取交集，`require_approval` 和 `require_review` 取并集；空交集、请求文件越界和路径逃逸失败。授权范围不因普通字段覆盖或 profile 自动扩大。任何资产引用只要落在业务仓库中，也必须满足有效读取范围；输入与项目 scope 使用相同的软链接规范路径判断。
- 后续新会话在已批准的模型/权限配置上默认隔离 Codex 执行上下文：Codex `--no-daemon --yolo --model gpt-6.1-sol`；Claude `--permission-mode bypassPermissions` 且模型沿用原选择（本机 `fable`）。规则依据及保证边界见 `DESIGN.md` 2.4；样例配置名为 `codex_default / claude_default`。原 01/02 的 `herdr/gpt-5.6-sol` 与 `fable/manual` 组合仅保留显式旧配置解析，不再是新会话默认，不把其历史证据当作新配置实测。准备成功只证明参数符合明确支持的组合；模型不可用时停止，不自动回退。Claude 的本机别名可能映射其他模型，不将别名当提供商证明。
- `--no-daemon` 现为本项目新 Codex 会话的隔离默认，避免复用共享后台的旧执行上下文；不修改共享服务、用户全局配置或业务授权。新 Run 使用更新后的配置源，核对解析的 `execution.start_args` 包含此开关，再核对真实 Pane、会话与工具身份。旧显式参数组合保留解析，旧 Run/快照不改写；新带身份交付若仍选到共享 daemon 参数，先确认更新本次配置，不静默补参数或重试。03 当时仅对隔离重演显式覆盖，04 使用 Claude，这些历史事实不变；本次隔离修复不宣称共享 daemon 内部原因已修复。
- 未知字段、缺失/无效引用、敏感内容、自由原生参数、缺失 CLI/Skill/实际选用的 profile 和冲突链接都失败。无 profile 的新默认不读取旧 `herdr.config.toml`。配置不接受凭证或环境变量；快照不包含环境、认证配置或依赖文件正文。凭证继续由 Harness 既有环境处理。
- 每个自有 Skill 的 `resources.json` 声明必需支持文件；它属于方法资产而非执行覆盖。快照指纹覆盖当前主管/员工的职责、Skill、资源清单和支持文件、Workflow、模板、显式项目规则/输入、官方 Herdr Skill 以及使用的 profile。未选资产不遍历、不读取；identified 交付中规则或执行资产指纹漂移即阻塞，不自动刷新快照。
- identified 交付模式在 `state.py initialize` 请求中选择，不改变 configure 的三层配置 schema，也不同于项目资源的 `mode: none`。缺省 `non-business`；显式 `versioned-test-fix` 的授权字段见 `identified.md`，不把 mode 或 write_paths 加入 Task。该模式在初始化时将全部 Run/Task context 纳入 baseline Git blob 指纹，以同一种字节表示生成和复核（不受 CRLF 检出转换影响）；输入必须在基准已版本化，不用工作区当前文件作历史 artifact。规则/Skill 等执行资产仍固定指纹，许可测试写入不得与它们重叠。外部验证配置由 authorization.validation_inputs 固定 Run `inputs/` 内的文件指纹，状态边界重新核对，缺失或漂移即阻塞，不替换为真实项目配置。

## 经授权链接

分别将 `~/.claude/skills/orchestrator`、`~/.agents/skills/orchestrator` 链到共享源的 `skills/orchestrator`；`development` 同理。链接前检查目标，已有正确链接复用，其他已有条目或断链停止并请求处理。只逐目录链接，不覆盖任何已有文件或整个发现目录。安装/链接另行授权，配置工具不会自动执行。

主管必须读取 `dispatch-input.json` 中的明确引用，并检查当前 Herdr 服务和权限现场。prepare 成功只证明配置与文件前置成立，不能证明服务健康、模型配额、权限批准或只读任务结果。
