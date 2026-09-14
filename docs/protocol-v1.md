# Campus Action OS 核心协议 v1

本目录定义两个共享语义的对象：Verified Action Object（VAO）和 Action Graph。机器可读规范位于 `schemas/v1/`，示例位于 `examples/`，可执行规则测试位于 `tests/contracts/`。

## 范围与冻结边界

当前仓库 `main` 只含初始化 README；交接摘要所称的冻结实验方案文件不在 Git 树中，因而本协议不声明任何实验问题、阈值、对照组或正式测试集规则。它只定义实现契约。若冻结文件日后补入，字段映射应通过单独的 `proposals/` 评审，不直接重写 v1 语义。

## VAO 生命周期

对象必须区分三个统计阶段：

1. `verification_status=model_output`：模型首次输出；只可依据输入文本或 OCR 证据，推断必须标为 `inferred`。
2. `verification_status=rule_reviewed`：规则复核后的对象；规则可拒绝缺证据、冲突、悬空引用、循环图或不一致状态，但不能把推断升级为原文明示。
3. `verification_status=user_confirmed`：用户明确确认后的对象；确认动作应进入 `change_history`，且不会改变原始证据。

`rejected` 表示对象不可供行动执行。`task_status` 是下游任务状态，不是模型置信度；`not_created` 不表示失败。

## 字段语义

- `user_relevance.status` 只能是 `relevant`、`not_relevant`、`uncertain`、`conflict` 或 `user_confirmation_required`。`reason` 必须可解释，`evidence_ids` 可为空但关键字段缺证据时不得为 `explicit`。
- `target_population.groups` 是原文明确或安全推断的人群标签。多人群路径应在 Graph 节点用 `population_groups` 分开，而不是复制或覆盖 VAO。
- `steps` 是可执行动作，至少一个；`dependencies` 只表达步骤之间的关系。`conditions` 是至少两个结果的分支；`exceptions` 表达例外，不是普通备注。
- `deadline.value` 使用 ISO 日期、带时区的 datetime 或 `start/end` 日期范围。未知时只能使用 `value:null`、`precision:"unknown"`；不得使用空字符串、0 或占位日期。`boundary_semantics` 在原文明确时为 `inclusive`/`exclusive`，无法判断为 `unknown`。多阶段截止应使用多个 VAO 或 Graph milestone 节点。
- `evidence.source_text` 必须是可复核的原文片段；`page_or_image` 是页码或图像标识；`bounding_box` 使用 0 到 1 的 `[x_min,y_min,x_max,y_max]` 归一化坐标；`field_name` 限定到关键字段。OCR 缺损应保留可见文本并将相关字段标为 `unknown` 或 `user_confirmation_required`，不得静默修复。
- `confidence.score` 是 (0,1]，不是概率真值；`basis` 记录模型、规则复核或用户确认来源。没有默认分数。
- `epistemic_status` 的 `explicit` 只适用于证据直接表达；`inferred` 必须能追溯到证据但不是原文直述；`unknown` 表示缺失；`conflict` 表示证据互相矛盾；`user_confirmation_required` 表示安全执行前必须问用户。
- `change_history` 是追加式、不可变审计轨迹。延期、撤销、替换使用 `postponed`、`revoked`、`replaced` 事件，并在 Graph 中用 `postpones`、`revokes`、`replaces` 边。

关键字段为相关性、行动步骤、截止时间、材料、地点/平台、条件和例外。每个关键断言必须引用 `evidence_ids`；缺少证据不能标 `explicit`。冲突或歧义必须进入 `conflict` 或 `user_confirmation_required`。AI 生成的默认地点、材料和截止时间禁止写入协议。

## Action Graph

节点类型是 `action`、`precondition`、`decision`、`milestone`、`notice_revision`。边类型是：`blocks`（阻塞）、`requires`（前置要求）、`informs`（信息依赖）、`branches_to`（条件分支）、`alternative_to`、`postpones`、`revokes`、`replaces`。边端点必须存在；`branches_to` 必须有 `condition_id`。

多人群路径用节点的 `population_groups` 表达。同一行动若对不同人群的步骤或截止时间不同，应使用不同节点和显式分支。依赖检测对 `blocks`、`requires`、`branches_to`、`postpones`、`replaces` 构建有向图并拒绝任何有向环；`informs` 和 `alternative_to` 不作为执行阻塞环，但仍必须无悬空端点。

无法确定时的安全表达是：保留 `value:null` 或空证据数组、把状态写为 `unknown`/`conflict`/`user_confirmation_required`，并禁止下游自动创建或执行有副作用的任务。安全表达不是补全。

## 兼容与版本

`schema_version` 固定为 `.../v1`。新增可选字段属于向后兼容；改变枚举、必填字段、字段含义或时间边界必须升 v2。读取器必须拒绝未知 major version，允许记录并忽略已知 minor 扩展。字段删除、重命名或语义迁移必须保留显式转换器和变更记录。没有默认值：缺失、`null`、空数组各自有语义，读取器不得互换。

## 上下游用法

发布端创建带证据的模型输出；规则复核服务执行 Schema、证据覆盖、引用、状态机和图检测；数据库以 `action_id`、`change_history` 和 `source_document_id` 保存版本；学生端只把 `user_confirmed` 或满足产品安全策略的 `rule_reviewed` 对象转为任务；评测按三个阶段分别统计，不把用户确认后的修订混入模型首次输出指标。
