# 带身份的交付报告

- mode、Run / Task、结果与证据引用。
- 固定基准、Run 分支/worktree、原工作区与最终成果版本/指纹。
- 各必需阶段的独立执行者/会话、实际检查及核验结论；完成时无在途写入。
- 完成或阻塞原因、未验证项、遗留风险和人工事项。
- `non-business`：`business_task_accepted: false`，仅验收非业务演练，head 等于 baseline，成果为 artifacts。
- `versioned-test-fix`：仅验收完成时 `business_task_accepted: true`，表示真实项目测试修复任务已验收；明确 `scope: versioned test-fix; production implementation unchanged` 和 `production_code_changed: false`，不表示修复了生产实现。列出 baseline / 最终 commit、`changed_paths`、许可测试路径与最终 commit 的检查证据；确认工作区 clean、原工作区不变及未写远端/访问真实 OSS。
- 记录可在新进程重新读取，不代表完整中断恢复或并发能力；最高权限进程和 mode 不构成安全沙箱。

`finish` 写入上述字段对应的 `reports/<task-id>.json`，不自动提交或推进下一工单。
