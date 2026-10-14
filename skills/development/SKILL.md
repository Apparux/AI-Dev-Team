---
name: development
description: 执行 AI Dev Team 岗位任务；收到显式只读核查输入，或带 Task/Attempt 身份的非业务交付、版本化测试修复派发时使用。
---

# 开发与核验方法

先读取投递的岗位、项目规则、Workflow 与结果模板，核对授权范围和模式。最高权限进程不扩大任务权限，也不是强制路径沙箱；冲突或缺失明确报告 BLOCKED。

## 带身份的交付

仅当派发协议为 `identified-delivery-v1`：必读本目录 `references/identified.md`，按 Run/dispatch 的 mode 核对身份、执行自己的 work/verify/review/fix 阶段、实际检查并发布唯一结果。缺省 `non-business` 只写本 Attempt；显式获准的 `versioned-test-fix` 另允许 work/fix 修改许可测试文件并本地提交，最终 commit 验证与证据字段按该分支执行。保留身份、版本与证据，结束后停止写入。不同模式不能混用。

## 只读观察

其他已授权的只读核查：必读本目录 `references/readonly.md`，仅读取指定输入与显式支持文件。用原生读取工具给出项目事实、内容与定位，列出未执行验证；只在终端给出结果，不创建结果文件，不自行派发执行者。问题有实际文件依据或明确阻塞原因才结束；不宣称正式 Task 已完成。
