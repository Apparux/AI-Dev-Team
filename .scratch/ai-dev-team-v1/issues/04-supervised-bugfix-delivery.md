# 04: 一个真实小 Bug 的完整交付

Milestone: M1 — 跑通最小协作
Status: ready-for-agent

**What to build:** 用户给出一个范围明确的低风险 Bug，主管用最少岗位完成实际修复、定向验证和独立分支交付，报告中的结果能够回溯到任务、执行身份与最终代码版本。

**Blocked by:** 03 — 带执行身份和工作区归属的交付演练。

**Execution gate:** 2026-10-13 本票通过，范围为用户明确批准的真实测试缺陷修复（非生产实现 Bug）；Run/Task completed、revision=10，已由新进程重读。已停止派发，等待 M1 人工复盘；**不得自动领取 05 或启动 implement-spec。** `Status` 是 triage 标签，不代替本段实际验收结论。

## 上下文与范围

对应 [TASKS T04 与 M1 出口](../../../TASKS.md)，验收 [PRD A03](../../../PRD.md)；调度、证据和交付遵循 [DESIGN](../../../DESIGN.md)。本票验证的是产品最小协作闭环，不是再做一次“查询 Pane”的工具冒烟。

选择获准的真实 Git 项目、一个低风险缺陷及相关验证命令。只启用主管和必要开发岗位；主管安排和验收，不亲自承担业务修复。复杂恢复、完整岗位质量流程、并行和跨项目仍属于后续票。

## Acceptance criteria

- [x] 用户目标、验收条件、基准版本和允许操作范围明确；首次代码写入前已有 Task/Attempt、持久记录及独立工作区归属。
- [x] 主管依据配置和显式 Skill/任务引用派发，开发执行者实际修改代码并产出对应版本的结构化结果与定向验证证据。
- [x] 主管有界观察并检查结果、差异、版本和验证输出；进程结束、idle/done、员工自报 PASS 都不能直接完成 Task/Run。
- [x] 权限或能力不足、投递不明、结果身份不符时明确停止并保留现场，不通过未经授权的参数改动与重试、重复派单或静默回退模型/工具掩盖失败；DESIGN 第 2.4 节已批准的新会话默认不替代本次任务授权。
- [x] 在获准的本地提交范围内交付 Run 独立分支与明确版本，报告区分通过、失败、未验证和人工事项；不推送、不合入主分支、不写用户原工作区。
- [x] 汇总 01–04 的实际验收证据、Herdr 限制、尚未验证能力及后续建议，提交用户复盘。没有明确后续授权时即使 05 的技术依赖已满足也不继续。

## 验证与执行约束

以这个真实 Bug 的最短定向验证为准，不机械 TDD、全量测试或自动提交。发现任务实际涉及高风险、缺少必要 Review 或范围不清时请求调整，不跳过门禁。M1 完成不等于 M2–M4 或 A01–A10 全部通过。

## Comments

### 2026-10-13：前置核验、用户确认的验收目标与执行授权

- 03 已基于 `<M1_03_RETRY_RUN>/` 的 work/verify 结果、原生调用对账、事件与 `evidence/38-final-reread-and-workspaces.json` 核对通过；仅为非业务交付，旧阻塞 Run 原样保留。
- 用户指定真实 Git 项目 `<ACCEPTANCE_REPO>`，只读排查后明确确认 `fileName` 与 `file` 都是预期兼容字段。用户随后批准将“既有测试错误要求 `file` 上传返回 400”这一真实测试缺陷作为本票目标；不是生产实现 Bug，不删除兼容逻辑。
- 基准为干净 `main` 的 `6270eba2773aca47f67cd9713d3c35952ae0c2df`。唯一目标代码写路径为 `src/test/java/com/bxw/filetransit/oss/LegacyUploadControllerTest.java`：保留两种字段成功上传与实际内容/元数据检查；缺失、未知字段和空文件仍拒绝且不调用 OSS。
- 用户已批准独立 worktree/分支、必要员工会话、外部证据和本地提交，并批准最小状态门禁扩展计划。计划分支 `ai-dev-team/m1-04-upload-field-tests`，worktree `<M1_04_WORKSPACE>`，Run `<M1_04_RUN>/`。主管不代修目标测试；work/verify 用同一 developer 岗位的不同 Claude 会话串行执行。
- 仅使用模拟 OSS 与本地离线定向验证；不读取/消费真实凭证、不访问真实 OSS、不安装依赖、不改业务实现或部署、不写原工作区、不推送、不合并。共享资产仅增加显式测试交付分支，旧模式/默认启动参数不变。
- 已完成命令：目标仓库 `git status --porcelain=v1 --untracked-files=all`、`git rev-parse HEAD`、`git symbolic-ref --short HEAD`；结果为干净、上述基准及 `main`。Herdr 0.9.3 服务/协议兼容，当前主管 Pane/会话已只读核对。尚未运行目标测试、派发业务员工或创建业务提交。
- 实施前备份与 Git 基线：Run 的 `evidence/00-baseline-and-backups.json`；13 个本票共享资产/工单原件保存在 `backups/`。AI-Dev-Team 本身无 Git，未擅自初始化；其修改以后续差异和指纹留证。
- 本条只记录目标与授权，不勾选任何尚无交付证据的验收项。结束后在本票补充实际结果并停止，不领取 05。

### 2026-10-13：控制入口扩展与真实派发

- 复用 `identified-delivery-v1`，新增显式 `versioned-test-fix`：只接受单 Task 的精确测试路径授权、本地提交和绑定最终 commit 的验证；旧非业务模式保持禁止仓库提交。配置解析器、默认模型参数、发现链接和 resources 未变；生产修改仍不获授权。
- 语法检查通过。临时协议检查先完成 16 项，再补验证配置漂移门禁；一次独立 code-review 确认 4 项实际缺陷（子模块差异忽略、Task 独有输入未版本化、BLOCKED 输出版本重读、CRLF/Blob 字节一致性），修复后 21 项定向检查通过，原 Reviewer 定点复核均关闭。证据：Run `evidence/01-state-syntax.json`、`02-state-gates.json`、`03-state-gates-final.json`、`05-state-review-fixes.json`、`06-control-review.json`。这些是控制工具验证，不是产品闭环验收。已通过的本次临时测试与合成仓库已核对归属并清理，清单见 `09-temporary-test-cleanup.json`。
- 共享实现/方法实际差异与指纹：`evidence/07-control-final.diff`、`07-control-final-manifest.json`。由于根项目无 Git，这些资产未作 Git 提交；回滚可使用本票 `backups/`，不触碰旧 Run 快照。
- `git worktree add -b ai-dev-team/m1-04-upload-field-tests <Run workspace> 6270eba2773aca47f67cd9713d3c35952ae0c2df` 成功（`08-worktree-create.json`）。项目登记及 Run initialize 退出 0（`10`、`11`），owner 为 `OWNER-M1-04`；任务 `upload-field-tests`、阶段 `work-001` 的意图先于投递持久化。
- 工作员工实际启动配置来自快照：Claude `--permission-mode bypassPermissions --model fable`。真实 Pane `PANE-M1-04-SHARED`、会话 `SESSION-M1-04-WORK` 已绑定（`16`、`17`）；仅一次 prompt（`18`）。短等待 timeout 后 `agent get` 确认 working，未重发；working 时 recent 历史读取受限后改用官方 visible 读取（`19`–`21`）。此时尚未受理员工结果、未宣称 Task 完成。
- 最短验收命令固定为 `mvn -o -Dtest=LegacyUploadControllerTest#uploadsExactBytesAndReturnsCompatibleJsonWithSameNamedQueryParameter+rejectsMissingWrongFieldAndEmptyFileWithoutUploading -Dspring.config.location=file:<Run>/inputs/test-application.properties test`。只验证两个相关方法，纯虚拟配置指纹已固定；不运行 CORS 等范围外检查或全量套件。离线 Maven 不是网络沙箱，仍由 mock OSS 与实际命令核查落实不调用真实服务。

### 2026-10-13：本票通过与 M1 人工复盘交付

- **结论：本票通过（用户批准的真实测试缺陷范围）；生产实现未修改。** 交付分支 `ai-dev-team/m1-04-upload-field-tests`，基准 `6270eba2773aca47f67cd9713d3c35952ae0c2df`，最终 commit `9e9b46eddfa46bd80857140dbc7248d182ed567f`（`test: fix legacy upload field compatibility assertions`，无 Co-Authored-By）。唯一变更为已有 `LegacyUploadControllerTest.java`，11 行增加、6 行删除。
- 员工实际参数化成功用例以覆盖 `fileName/file`，保留字节/长度/MIME/响应/路径/流关闭断言；把非法字段改成 `unknown`，并覆盖缺失文件及两种字段的空文件，均检查 400 和 OSS 无交互。主管没有替员工改测试或写结果。
- 验证命令使用上条固定的原样 argv：work 在基准实际退出 1，2 tests/1 failure/0 errors/0 skipped，旧断言 expected 400 but was 502（合法 file 进入上传，旧拒绝用例未 stub 上传结果导致无 ETag）；并非环境失败。work 在最终 commit 退出 0，3 tests/0 failures/0 errors/0 skipped。独立 verify 在同一 commit 原样执行一次，同为 3 tests 全通过；真实 Surefire 新报告是两个参数化成功实例＋一个拒绝实例。
- work 的证据为 `tasks/upload-field-tests/attempts/work-001/{result.yaml,evidence/03-baseline-validation.json,evidence/07-final-validation.json}`；独立 verify 为 `tasks/upload-field-tests/attempts/verify-001/{result.yaml,evidence/02-final-validation.json,evidence/04-surefire-results.json,evidence/06-independent-review.json}`。主管核对原生工具调用而非依赖 PASS 文案，见 `evidence/25-work-native-reconciliation.json`、`40-verify-native-reconciliation.json`。
- verify 使用相同 developer 岗位但新会话 `SESSION-M1-04-VERIFY`，原 work 退出后复用空 Pane `PANE-M1-04-SHARED`；非并发、非同会话。两阶段各只投递一次，timeout 后仅观察，无重发、切模型或参数回退。两次 `/exit` 后均实际核对 Pane 无 Agent 且前台回到 Shell（`28`、`43`）；没有把 idle/done 当作已停写或完成。
- 受支持状态入口执行 work stopped/accept → verify dispatch/bind/stopped/accept → finish。新进程 `state.py --run-dir <Run> inspect` 退出 0，Run/Task completed、revision=10、pending_executions={}；工作区/分支/HEAD、实际唯一差异和 `git diff --check` 均核对通过，原工作区仍为干净 main/原基准。证据 `evidence/47-final-reread-and-workspaces.json`；机器报告 `reports/upload-field-tests.json`。未推送、未合并、未发布。
- 第 4 验收项证据边界：本次实际覆盖单次投递 timeout 后对账与不重发，负向协议检查覆盖缺授权、错误身份、越界、版本/配置漂移；权限/能力拒绝的既有实测复用 01–03，本 Run 未重新注入认证/权限故障，不据此声称完整故障矩阵通过。
- 本票非阻塞问题：Herdr working 时不能读取完整 alternate-screen 历史，使用 visible 与原生会话对账；verify 的结果准备辅助 Python 曾在执行前因源码编码失败，保留诊断后用 ASCII 源码修正，未重跑测试、未改许可命令（verify `evidence/08-result-preparation-diagnostic.json`）。
- M1 汇总报告：`<M1_04_RUN>/reports/m1-review.md`。01 工具级边界、02 配置驱动只读、03 带身份非业务交付的实际证据被引用而非重跑；04 增加真实测试代码/提交/独立最终版本验证。原 03 Codex shared-daemon 身份冲突未证明修复，本次 Claude 成功不外推。完整恢复/取消/接管、双向业务、跨项目/技术栈、并行/多 Run/集成、生产 Bug 和真实 OSS 仍未验证。
- 验收仅 mock OSS 两个相关方法，未执行全量套件。Maven resources 按现有构建复制应用资源到忽略的 target，但 Spring 显式虚拟 config location 替代默认运行时加载，Agent 未读取或打印真实配置/凭证。README 中旧字段限制说明未在本票同步。
- 本次临时控制协议测试已清理；目标测试修改是用户要求的交付，保留。共享资产无 Git 仓库，仅备份/指纹/差异留证，未擅自初始化。交付分支、worktree、证据和必要验证配置均保留，员工已退出，本次 Pane 留为 Shell。
- **已停止派发，未领取 05，未启动 implement-spec；等待 M1 人工复盘及后续明确授权。**

