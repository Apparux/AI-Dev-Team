# 带身份的受监督交付

进入条件：前置票据有实际证据；仓库/基准、独立 Run worktree/分支、外部记录和原生启动参数均获授权。默认最高权限与交付 mode 不扩大本票动作范围，不代表写入沙箱。

Task 是交付单元，阶段为 work → 独立 verify → 必需时 review；确认缺陷进入新 fix Attempt 后复验。必需阶段与岗位在任务卡中固定，依赖不得循环。03 演练与 04 测试修复均仅 work + verify，不启动完整团队；04 使用同一开发岗位、不同 executor/session 的两个会话串行执行，员工修改，主管只派发/核验。

主管按 `skills/orchestrator/references/identified.md` 使用状态入口：初始化 → 持久 dispatch 意图 → 启动并绑定真实执行身份 → 单次派发 → 员工原子发布 → 核清实际停止 → accept → 下一必需阶段 → finish。员工方法为 `skills/development/references/identified.md`；两个模式使用同一协议和 Result envelope，具体版本与 checks 字段按员工方法分支填写。

## 模式边界

- `non-business` 为 initialize 缺省：输出限定为 Attempt 内的非业务成果、结果和检查证据。工作区只读，无代码修改、提交或推送；head 等于 baseline，work/fix PASS 有非空 artifact 成果。
- `versioned-test-fix` 须显式初始化并匹配严格授权：仅一个无依赖 Task，work/fix 仅改授权测试文件并本地 commit，之后按最终 commit 定向验证；artifacts 为空，Git 固定输入/输出。04 仅修真实 file-transit 的 `src/test/java/com/bxw/filetransit/oss/LegacyUploadControllerTest.java` 旧断言，保持 `fileName`/`file` 兼容；生产实现、原工作区和远端不变，不访问网络或真实 OSS。许可路径/命令来自 authorization，不增加 Task 字段，也不扩大为产品实现修复。04 使用指纹固定的 Run `inputs/` 内纯虚拟 `test-application.properties` 显式替代 `application.yml`，避免读取真实配置；最终验证仅运行已批准的两个现有相关方法：正常字节/元数据上传（扩展覆盖 `fileName`/`file`）与缺失/未知/空文件，不扩展到 CORS 等范围外检查，具体命令以 validation_argv 为准。

旧/错误结果不能覆盖或推进，第二主管不能直接接管；工作区不删除，归属、停止或事件不一致时阻塞，不自动修复/重派。idle 单独不能解除写入占用。

完成条件：独立阶段的真实证据绑定同一最终成果版本，无在途写入，报告可再次读取。非业务模式工作区不变；测试修复模式核对最终 HEAD、clean、许可路径和真实测试输出，原工作区不变。03 通过后不进入 04，04 通过后不进入 05；记录可读取不等于完整中断恢复，也不启用并发。
