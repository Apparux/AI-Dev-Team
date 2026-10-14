# Issue tracker: Local Markdown

本项目的工单和规格存放于 `.scratch/`，路径均相对于项目根目录。

## 文件约定

- 每个功能一个目录：`.scratch/<feature-slug>/`。
- 规格：`.scratch/<feature-slug>/spec.md`。
- 实施工单：`.scratch/<feature-slug>/issues/<NN>-<slug>.md`，从 `01` 编号，每张工单独立成文件。
- 普通工单在文件顶部附近使用 `Status:` 行记录 triage 状态，取值见 `triage-labels.md`。
- 评论和对话历史追加到文件底部的 `## Comments` 下。

## 发布到 issue tracker

按上述约定创建规格或工单文件，按需创建目录。

## 获取相关工单

读取用户提供的文件路径。若仅提供编号，在对应功能的 `issues/` 下查找；编号有歧义时，先确认所属功能。

## Wayfinding 操作

供 `/wayfinder` 使用；子工单的执行状态与普通工单的 triage 状态分开处理。

- 地图：`.scratch/<effort>/map.md`，包含 Notes、Decisions-so-far、Fog。
- 子工单：`.scratch/<effort>/issues/<NN>-<slug>.md`，从 `01` 编号，正文记录待解决的问题。
- 类型：顶部附近的 `Type:` 行，取值为 `research`、`prototype`、`grilling` 或 `task`。
- 执行状态：`Status: open`、`Status: claimed` 或 `Status: resolved`。
- 阻塞关系：`Blocked by: NN, NN`；列出的工单全部 resolved 后才解除阻塞。
- 下一项：扫描该目录，选择编号最小、状态为 open 且未被阻塞的工单。
- 领取：开始工作前设置 `Status: claimed` 并保存。
- 完成：在 `## Answer` 下追加答案，设置 `Status: resolved`，再向地图的 Decisions-so-far 追加结论摘要和工单链接。
