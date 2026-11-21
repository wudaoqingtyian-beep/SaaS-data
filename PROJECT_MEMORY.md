# PROJECT_MEMORY.md

# B2B SaaS 客户使用与服务运营分析平台

> 本文件是项目的长期记忆与开发约束。使用 Cline 开发前，必须先完整阅读本文件，再检查当前工作区。本文描述的是求职作品 Demo，不是生产级 SaaS 系统。

## 0. 给 Cline 的首要指令

1. 开始任何修改前，完整阅读本文件，并检查当前工作区目录、已有代码、README、依赖文件和 Git 状态（如果是 Git 仓库）。
2. 如果工作区已有项目，不要直接覆盖或删除已有文件。先判断现有内容是否与本项目有关；不确定时保留并报告。
3. 严格按本文的 MVP 范围开发。不要擅自增加登录注册、权限系统、云部署、复杂后端、机器学习、LLM、Agent、消息队列或不必要的依赖。
4. 先完成数据结构、模拟数据生成和分析函数，再开发 Streamlit 页面。不要先堆 UI，再补数据逻辑。
5. 每个阶段都要运行对应测试或最小验证。不得声称运行过未实际执行的测试。
6. 优先选择简单、可解释、易维护的实现。核心分析逻辑应放在独立 Python 模块中，避免全部写在 Streamlit 页面里。
7. 业务结论必须由数据支持。把“数据观察”“可能原因”和“建议动作”分开；不得把相关性或前后对比写成因果结论。
8. 所有业务数据均为模拟数据。界面、README 和演示材料必须明确标注“模拟数据 / Demo”，不得声称来自真实企业。
9. 每完成一个阶段，向用户报告：完成内容、修改文件、实际运行的命令及结果、未完成事项和已知限制。
10. 如果需求与本文冲突，以本文的项目边界为准；如确实需要改变方向，先提出差异和影响，不要自行扩大范围。

---

## 1. 项目概述

### 1.1 项目名称

**B2B SaaS 客户使用与服务运营分析平台**  
英文名称：**Customer Usage & Service Operations Analytics**

### 1.2 项目定位

这是一个面向求职作品集的轻量级数据分析与数据运营 Demo。模拟一家向企业客户提供软件服务的 B2B SaaS 公司，通过分析企业客户的产品使用记录、技术支持工单和客户跟进记录，帮助运营人员：

- 了解客户整体使用情况和服务质量；
- 发现产品使用活跃度下降、核心功能使用不足、工单积压等异常；
- 按透明、可解释的规则识别需要优先关注的客户；
- 记录培训、回访和问题处理等运营动作；
- 对比跟进前后的指标变化，观察运营动作之后发生了什么。

### 1.3 目标岗位

- 初级数据分析师 / 经营分析助理；
- 数据运营 / 用户运营 / 客户运营；
- 客户成功运营 / 服务运营（作为补充投递方向）。

### 1.4 项目核心展示能力

1. SQL：多表关联、过滤、分组聚合、时间范围统计；
2. Python：数据生成、数据校验、指标计算和异常识别；
3. Pandas：数据清洗、分组分析和趋势对比；
4. 数据可视化：KPI、趋势图、分类统计、客户明细；
5. 业务分析：从数据现象定位分析方向，提出可执行的运营动作；
6. 效果追踪：记录运营动作并观察动作前后的指标变化。

### 1.5 项目边界

这是单机、本地运行、单用户的分析 Demo。它不是完整客户管理系统，也不是生产级 SaaS 产品。

**本期必须实现：**

- 本地 SQLite 数据库；
- 四张核心业务表；
- 可重复生成的模拟数据；
- 四个 Streamlit 分析页面 / 模块；
- SQL 与 Pandas 分析；
- 透明的规则型客户风险提示；
- 客户跟进记录的新增、查看和前后指标对比；
- 基本自动化测试和使用文档。

**本期明确不做：**

- 登录、注册、角色权限和多租户隔离；
- 真实 SaaS 产品埋点或外部 API 接入；
- 真实客户信息、真实公司名称和真实合同数据；
- 机器学习流失预测、深度学习、LLM、Agent；
- 自动发送邮件、短信、工单或营销消息；
- 复杂前后端分离、FastAPI 服务、微服务、Docker、云部署；
- 财务结算、真实续费流程和合同管理。

---

## 2. 目标用户与典型使用流程

### 2.1 目标使用者

虚拟 SaaS 企业中的客户运营人员、客户成功人员或数据分析人员。

### 2.2 典型流程

1. 打开经营总览，查看客户活跃情况和工单服务表现；
2. 进入客户使用分析，筛选活跃度下降或核心功能使用较少的客户；
3. 进入服务工单分析，查看客户是否存在未解决工单、响应慢或重复问题；
4. 打开客户风险清单，检查系统给出的风险分数、触发规则和相关证据；
5. 对需要跟进的客户记录培训、回访或问题处理动作；
6. 在后续日期查看跟进前后的活跃指标变化，并形成简短分析结论。

---

## 3. 功能需求说明书（PRD）

## 3.1 全局要求

- 页面语言：简体中文；必要的数据库字段和代码变量使用英文 snake_case。
- 所有页面显著标注“演示数据为模拟生成”。
- 页面提供全局日期范围筛选（适用于有日期维度的指标）；支持行业、区域、套餐筛选的模块可以提供对应筛选器。
- 筛选条件变化后，相关 KPI、图表和明细必须同步变化。
- 空数据、缺失值和除零场景要有友好提示，不能出现未处理异常。
- 对时间指标明确单位，统一优先使用小时（h）；图表和表格的小数位保持一致。
- 不展示真实个人信息。客户联系人、手机号、邮箱不在本项目数据范围内。

## 3.2 模块 A：客户经营总览

### 目标

让使用者快速掌握客户规模、产品使用和技术支持服务的整体情况。

### 核心 KPI

1. 企业客户数：customers 表中的客户数量；
2. 近期活跃客户数：所选期间内至少有一条 usage_weekly 记录且 active_users > 0 的客户数；
3. 客户活跃率：近期活跃客户数 / 客户总数；
4. 核心功能使用客户数：所选期间内 core_feature_uses 总和大于 0 的客户数；
5. 工单总量：所选期间内创建的工单数量；
6. 工单解决率：所选期间创建的工单中 status 属于 resolved 或 closed 的数量 / 所选期间创建的工单总量；
7. 平均首次响应时间：有 first_response_at 的工单，从 created_at 到 first_response_at 的平均小时数；
8. 平均解决时间：有 resolved_at 的工单，从 created_at 到 resolved_at 的平均小时数。

### 图表

- 每周活跃客户数趋势；
- 每周工单创建量与已解决量趋势；
- 工单类别分布；
- 不同套餐或行业的客户数量 / 活跃率对比。

### 验收标准

- KPI 有明确口径；
- 日期筛选会影响对应指标和图表；
- 没有工单或没有活跃记录时显示 0 或空状态，不报错；
- 活跃率计算结果位于 0% 到 100% 之间。

## 3.3 模块 B：客户产品使用分析

### 目标

分析企业客户是否持续使用产品，以及核心功能是否得到采用。

### 核心分析指标

- 每周活跃天数（active_days）；
- 每周登录次数（login_count）；
- 每周活跃用户数（active_users）；
- 核心功能使用次数（core_feature_uses）；
- 核心功能使用用户数（core_feature_users）；
- 总使用时长（usage_minutes）；
- 客户核心功能采用率：所选期间内 core_feature_uses > 0 的客户数 / 客户总数；
- 客户活跃变化：比较观察窗口前 4 周与最后 4 周的平均 active_days。

### 页面功能

- 按客户、行业、区域、套餐筛选；
- 展示每周活跃客户数趋势；
- 展示客户活跃天数分布；
- 展示核心功能采用情况；
- 提供客户使用明细表；
- 标记活跃度显著下降的客户。

### 业务分析原则

活跃度下降只是一个需要进一步分析的现象，不等同于客户流失。系统不得仅凭使用频率下降就断言客户会流失。

### 验收标准

- 能查看单个客户近 12 周的使用趋势；
- 能比较不同客户群体的使用情况；
- 趋势比较必须使用相同长度的前后窗口；
- 前期均值为 0 时，不计算百分比下降，显示“无可比基线”。

## 3.4 模块 C：客户服务工单分析

### 目标

分析客户技术支持需求、处理效率和服务质量。

### 核心指标

- 工单总量；
- 未解决工单数：status 属于 open 或 in_progress；
- 工单解决率；
- 平均首次响应时间；
- 平均解决时间；
- 平均满意度：仅对有 satisfaction_score 的工单计算；
- 高优先级工单数：priority 属于 high 或 urgent。

### 图表和明细

- 工单类别分布；
- 工单优先级分布；
- 每周工单数量趋势；
- 不同类别工单的平均解决时间；
- 未解决工单列表（客户、问题类别、优先级、创建时间、当前状态、已等待小时数）。

### 业务分析原则

- 未解决工单没有 resolved_at，不得参与平均解决时间计算；
- 没有 first_response_at 的工单不得参与平均首次响应时间计算；
- 没有满意度评分的工单不得按 0 分纳入平均满意度；
- 工单量多不必然代表服务质量差，需要结合客户规模、类别和处理时长分析。

### 验收标准

- 状态、类别和优先级筛选正常；
- 时间指标只基于有效时间戳计算；
- 未解决工单可按等待时长排序；
- 所有时间差非负。

## 3.5 模块 D：客户风险提示与运营跟进

### 目标

基于可解释规则，识别需要人工关注的客户，并记录运营动作。

### 客户风险分数（规则型，不是预测模型）

每个客户计算 0 到 100 分的风险分数，按以下规则累加，最高不超过 100：

| 触发条件 | 加分 |
|---|---:|
| 最近 4 周平均 active_days < 2 天 / 周 | +25 |
| 与最早 4 周相比，最近 4 周平均 active_days 下降 >= 30% | +30 |
| 当前未解决工单数 >= 2 | +20 |
| 存在创建超过 72 小时仍未解决的工单 | +15 |
| 合同到期日距数据观察基准日 0–30 天 | +10 |

风险等级：

- 低风险：0–29 分；
- 中风险：30–59 分；
- 高风险：60–100 分。

规则实现要求：

- 页面展示分数、等级和每一条已触发规则；
- 缺少对比基线时，不触发“活跃度下降”规则；
- 合同到期日已早于基准日的客户，不套用“未来 30 天到期”规则，应单独显示合同日期状态或不加分；
- 风险等级只是人工排查优先级，不应命名为“流失概率”；
- 在页面注明“规则型风险提示，不代表客户一定会流失”。

### 运营跟进记录功能

用户可以新增并查看以下字段：

- 客户；
- 跟进日期；
- 跟进类型；
- 触发原因；
- 采取的行动；
- 跟进状态；
- 跟进结果备注。

跟进类型：training、check_in、issue_resolution、product_guidance、renewal_communication。  
跟进原因：usage_decline、low_adoption、repeated_tickets、overdue_ticket、upcoming_renewal、manual。  
跟进状态：planned、completed、cancelled。

### 效果追踪

- 对已完成的跟进记录，允许选择跟进前后观察窗口；
- 至少展示前后平均 active_days、core_feature_uses 或未解决工单数中的一到两个指标；
- 明确显示观察窗口起止日期；
- 只描述“跟进前后指标变化”，不能自动生成“措施导致改善”的因果结论；
- 如果跟进后数据不足，显示“后续数据不足，暂无法比较”。

### 验收标准

- 风险规则计算有单元测试；
- 新增跟进记录后数据库中确实有记录；
- 无效 customer_id、日期或枚举值应被阻止；
- 效果对比能够正确区分前后窗口；
- 重启应用后已保存的跟进记录仍然存在。

---

## 4. 数据库设计

### 4.1 数据库方案

- 数据库：SQLite；
- 文件建议：`data/app.db`；
- 主键：客户使用 TEXT ID；其他事实表使用 INTEGER 自增 ID 或 TEXT ID；
- 日期格式：`YYYY-MM-DD`；
- 日期时间格式：ISO 8601，例如 `2026-10-12T09:30:00`；
- 金额和时长使用数值字段；本项目不做真实财务结算。
- 每次连接数据库时启用 `PRAGMA foreign_keys = ON`。

### 4.2 实体关系

- customers 1 对多 usage_weekly；
- customers 1 对多 support_tickets；
- customers 1 对多 followup_records。

每个客户每周最多一条 usage_weekly 记录。四张表不需要额外引入复杂的用户表或产品埋点明细表。

### 4.3 表一：customers（企业客户表）

| 字段 | 类型 | 约束 / 示例 | 说明 |
|---|---|---|---|
| customer_id | TEXT | PK，如 `CUST0001` | 客户唯一编号 |
| company_name | TEXT | NOT NULL，如 `示例企业001` | 虚构企业名称 |
| industry | TEXT | NOT NULL | 行业 |
| company_size | TEXT | small / medium / large | 企业规模 |
| region | TEXT | NOT NULL | 区域，如华东、华南 |
| plan_type | TEXT | basic / professional / enterprise | 软件套餐 |
| licensed_users | INTEGER | > 0 | 合同授权用户数 |
| signup_date | TEXT | YYYY-MM-DD | 客户注册日期 |
| contract_start_date | TEXT | YYYY-MM-DD | 合同开始日期 |
| contract_end_date | TEXT | YYYY-MM-DD | 合同到期日期 |
| monthly_fee | REAL | >= 0 | 模拟月费，单位元 |
| account_owner | TEXT | NOT NULL | 虚构客户负责人，如运营专员A |
| created_at | TEXT | ISO datetime | 数据记录创建时间 |

建议检查：contract_end_date >= contract_start_date；licensed_users >= 1；monthly_fee >= 0。

### 4.4 表二：usage_weekly（客户每周产品使用汇总表）

| 字段 | 类型 | 约束 / 示例 | 说明 |
|---|---|---|---|
| usage_id | INTEGER | PK AUTOINCREMENT | 记录 ID |
| customer_id | TEXT | FK -> customers.customer_id | 企业客户 |
| week_start | TEXT | YYYY-MM-DD | 周一日期 |
| login_count | INTEGER | >= 0 | 当周登录次数 |
| active_days | INTEGER | 0–7 | 当周至少发生一次有效使用的天数 |
| active_users | INTEGER | >= 0 | 当周活跃用户数 |
| core_feature_users | INTEGER | >= 0 | 使用过核心功能的用户数 |
| core_feature_uses | INTEGER | >= 0 | 核心功能使用次数 |
| usage_minutes | INTEGER | >= 0 | 总使用时长（分钟） |

约束：

- UNIQUE(customer_id, week_start)；
- active_days BETWEEN 0 AND 7；
- active_users <= customers.licensed_users（由数据生成器和校验逻辑保证）；
- core_feature_users <= active_users；
- 所有次数和时长不得为负数。

### 4.5 表三：support_tickets（客户支持工单表）

| 字段 | 类型 | 约束 / 示例 | 说明 |
|---|---|---|---|
| ticket_id | TEXT | PK，如 `TKT00001` | 工单唯一编号 |
| customer_id | TEXT | FK -> customers.customer_id | 所属客户 |
| created_at | TEXT | ISO datetime | 工单创建时间 |
| category | TEXT | 见枚举 | 问题类别 |
| priority | TEXT | low / medium / high / urgent | 优先级 |
| status | TEXT | open / in_progress / resolved / closed | 当前状态 |
| channel | TEXT | email / chat / phone / portal | 提交渠道 |
| subject | TEXT | NOT NULL | 简短虚构问题标题 |
| first_response_at | TEXT | nullable ISO datetime | 首次响应时间 |
| resolved_at | TEXT | nullable ISO datetime | 解决时间 |
| satisfaction_score | INTEGER | nullable，1–5 | 满意度评分 |

category 枚举建议：

- login_access：登录与账号权限；
- integration_api：系统集成与 API；
- feature_usage：功能使用咨询；
- data_issue：数据导入或数据异常；
- billing：订阅或账单咨询；
- performance：性能或响应速度；
- other：其他问题。

约束：

- resolved_at 不得早于 created_at；
- first_response_at 不得早于 created_at；
- satisfaction_score 只能为 NULL 或 1–5；
- status 为 open / in_progress 时 resolved_at 必须为 NULL；
- 工单未首次响应时 first_response_at 可以为 NULL；
- 满意度通常只在 resolved / closed 时生成。

### 4.6 表四：followup_records（客户运营跟进记录表）

| 字段 | 类型 | 约束 / 示例 | 说明 |
|---|---|---|---|
| followup_id | INTEGER | PK AUTOINCREMENT | 跟进记录 ID |
| customer_id | TEXT | FK -> customers.customer_id | 跟进客户 |
| followup_date | TEXT | YYYY-MM-DD | 跟进日期 |
| followup_type | TEXT | 见枚举 | 跟进方式 |
| trigger_reason | TEXT | 见枚举 | 跟进触发原因 |
| action_description | TEXT | NOT NULL | 采取的具体措施 |
| result_status | TEXT | planned / completed / cancelled | 跟进状态 |
| result_note | TEXT | nullable | 跟进结果备注 |
| created_at | TEXT | ISO datetime | 记录创建时间 |

### 4.7 索引建议

只创建有实际查询价值的索引：

- usage_weekly(customer_id, week_start)；
- usage_weekly(week_start)；
- support_tickets(customer_id, created_at)；
- support_tickets(status, created_at)；
- followup_records(customer_id, followup_date)。

如果 customer_id + week_start 已有 UNIQUE 约束，该唯一约束本身通常已创建对应索引，不要重复创建完全相同的索引。

---

## 5. 模拟数据生成规则

## 5.1 总体要求

- 全部数据由本地 Python 脚本生成；
- 使用固定随机种子 `SEED = 42`，保证相同配置下可重复生成；
- 不调用外部 API，不依赖真实公司或个人信息；
- 使用虚构公司名，例如“示例企业001”；
- 生成后写入 SQLite；
- 初始化脚本应支持清空并重新生成 Demo 数据，但必须显式执行，不得应用每次启动时自动覆盖用户数据；
- 默认时间窗口为连续 12 周：2026-08-10（周一）至 2026-11-01（周日）；将开始日期、周数和随机种子集中配置，方便以后修改。

### 5.2 数据量目标

| 数据表 | 目标数据量 | 规则 |
|---|---:|---|
| customers | 100 | 100 家虚构企业客户 |
| usage_weekly | 1,200 | 100 客户 × 12 周，每客户每周一条 |
| support_tickets | 300–500 | 建议约 400 条 |
| followup_records | 40–60 | 建议约 50 条 |

实际生成数量应写入初始化日志或 README，不能只写目标数量。

### 5.3 客户基础数据分布

- 行业：制造业、零售、物流、教育、专业服务、互联网等；
- 区域：华东、华南、华北、华中、西南、西北、东北；
- 企业规模：small、medium、large；
- 套餐：basic、professional、enterprise；
- 授权用户数：根据套餐和规模生成，例如 5–200；
- monthly_fee：按套餐和授权规模设置合理模拟范围，单位元；
- 客户注册日期早于或落在观察窗口内；
- 合同到期日期分布：一部分在观察基准日后 0–30 天，一部分在 31–90 天，其余更晚；不要让全部客户都集中在同一到期月份；
- 所有公司名和负责人名称均为虚构。

### 5.4 内部行为场景分组

数据生成器内部将 100 家客户分为以下行为画像。画像标签用于控制数据生成，不要求直接暴露为数据库字段或页面字段。

| 内部画像 | 占比目标 | 行为特征 |
|---|---:|---|
| healthy | 60% | 活跃度稳定，核心功能使用正常，工单相对较少 |
| declining_usage | 18% | 前期使用正常，后 4 周活跃度逐步下降 |
| low_adoption | 12% | 登录和核心功能使用偏少，长期活跃水平低 |
| service_friction | 10% | 产品使用不一定低，但工单数量较多、响应或解决时间偏长 |

要求：

- 场景组由固定随机种子生成；
- 场景组仅是模拟数据生成机制，不作为真实标签或模型训练标签；
- 不要让页面直接用画像标签“泄露答案”，风险识别必须从实际指标和规则计算得出；
- 不同画像之间允许自然波动，不要把所有同组客户生成成完全相同的数据。

### 5.5 usage_weekly 生成规则

每个客户每周必须有一条记录，合计 1,200 条。

基本约束：

- active_days 为 0–7 的整数；
- active_users 为 0 到 licensed_users 之间的整数；
- core_feature_users 为 0 到 active_users 之间的整数；
- login_count、core_feature_uses、usage_minutes 均为非负整数；
- active_days = 0 时，active_users、login_count、core_feature_uses、usage_minutes 应为 0；
- active_users = 0 时，core_feature_users 必须为 0。

建议行为分布：

- healthy：active_days 通常为 4–6；活跃用户占授权用户约 35%–80%；核心功能使用稳定；
- declining_usage：前 4 周接近 healthy，最后 4 周逐步下降，最后 4 周平均 active_days 相比前 4 周下降约 30%–60%；
- low_adoption：active_days 通常为 0–2；core_feature_users 占 active_users 比例较低；
- service_friction：使用情况中等或较高，但后续工单更多、问题更复杂。

每周数据需要带少量随机波动，不可只使用固定常数。下降场景应逐周变化，而不是只把最后一周突然设为 0。

### 5.6 support_tickets 生成规则

目标生成约 400 条工单，按客户画像设置不同工单倾向：

- healthy：每客户约 2–4 条；
- declining_usage：每客户约 3–6 条；
- low_adoption：每客户约 2–4 条；
- service_friction：每客户约 5–8 条。

类别分布建议：

- feature_usage、login_access 占比较高；
- integration_api、data_issue、performance 占一定比例；
- billing、other 占比较低比例。

优先级：

- low、medium 为主；
- high、urgent 占较少比例；
- service_friction 组高优先级比例略高。

状态：

- resolved、closed 为主；
- open、in_progress 保留一定数量，建议合计约 10%–20%；
- 未解决工单的 resolved_at 必须为空；
- 一部分 in_progress 可以已有 first_response_at；
- 创建时间位于 12 周观察窗口内；
- 首次响应和解决时间必须晚于创建时间；
- 如果工单创建时间接近观察期结束，生成的响应 / 解决时间不得无故超出模拟数据基准日期；可将其设置为尚未解决。

满意度：

- 仅对 resolved / closed 工单抽样生成 1–5 分；
- service_friction 组评分总体偏低，但要保留随机波动；
- 未解决工单满意度为 NULL；
- 不得把未评分当作 0 分。

### 5.7 followup_records 生成规则

目标约 50 条，优先分配给 declining_usage、low_adoption、service_friction 客户，也保留少量普通客户的常规回访。

跟进类型：

- training：产品培训；
- check_in：日常回访；
- issue_resolution：问题处理；
- product_guidance：功能使用指导；
- renewal_communication：续费沟通。

触发原因：

- usage_decline：使用活跃度下降；
- low_adoption：核心功能采用不足；
- repeated_tickets：重复工单较多；
- overdue_ticket：工单处理超时；
- upcoming_renewal：合同即将到期；
- manual：人工安排。

跟进状态：planned、completed、cancelled；completed 为主，planned 和 cancelled 保留少量。

要求：

- followup_date 必须在模拟观察窗口内；
- action_description 使用具体、可信、简短的中文描述；
- result_note 可为空；
- 不要伪造“续费成功”或“客户挽回”等确定性结果；
- 如模拟部分客户跟进后使用指标改善，应在 README 说明这是为了演示前后对比而设计的模拟场景，不代表真实因果关系。

### 5.8 数据质量校验

数据生成完成后执行以下校验，并将结果输出到控制台：

1. customers.customer_id 不重复；
2. usage_weekly 每个 customer_id + week_start 组合唯一；
3. usage_weekly 应恰好为 1,200 条（按默认参数）；
4. usage_weekly 的 customer_id 均能在 customers 中找到；
5. 工单、跟进记录的 customer_id 均能在 customers 中找到；
6. active_days 在 0–7 范围；
7. active_users <= licensed_users；
8. core_feature_users <= active_users；
9. 计数、时长和月费均非负；
10. 日期时间先后关系正确；
11. 未解决工单 resolved_at 为空；
12. 满意度为 NULL 或 1–5；
13. SQLite `PRAGMA foreign_key_check` 无结果；
14. 固定随机种子下，重复生成应产生一致的数据分布和记录数量。

如校验失败，初始化流程应明确失败并指出原因，不能静默继续。

---

## 6. 指标口径与分析规则

所有指标都要在代码或文档中集中定义，避免页面各自实现、口径不一致。

### 6.1 基础指标

- 客户总数 = customers 行数；
- 活跃客户数 = 所选期间至少一周 active_users > 0 的不同客户数；
- 客户活跃率 = 活跃客户数 / 客户总数；
- 核心功能采用客户数 = 所选期间 core_feature_uses 总和 > 0 的不同客户数；
- 核心功能采用率 = 核心功能采用客户数 / 客户总数；
- 工单总量 = 所选期间 created_at 落入范围的工单数；
- 未解决工单数 = 所选期间创建且 status 为 open / in_progress 的工单数；
- 工单解决率 = 所选期间创建且 status 为 resolved / closed 的工单数 / 所选期间创建工单总量；
- 平均首次响应小时数 = 对有 first_response_at 的工单，AVG((first_response_at - created_at) 小时)；
- 平均解决小时数 = 对有 resolved_at 的工单，AVG((resolved_at - created_at) 小时)；
- 平均满意度 = 有 satisfaction_score 的工单评分平均值。

分母为 0 时返回 NULL 或显示“暂无数据”，不要抛出异常，也不要随意返回 100%。

### 6.2 周趋势

- 使用 week_start 作为横轴；
- 周序列应按日期升序；
- 缺失周可在展示层补 0，但需要明确这是无记录 / 无活动，不得伪造原始记录；
- 比较前 4 周与后 4 周时，两个窗口长度必须相同。

### 6.3 风险提示

风险分数只使用第 3.5 节定义的规则。将规则计算封装为独立函数，返回：

- customer_id；
- risk_score；
- risk_level；
- triggered_rules（触发规则列表）；
- supporting_values（用于解释规则的实际值）。

页面应允许按风险等级筛选，并能查看每个风险提示的证据。

---

## 7. 技术实现与目录建议

### 7.1 技术栈

- Python 3.10+（优先兼容当前环境）；
- SQLite（Python 标准库 sqlite3）；
- Pandas；
- Streamlit；
- Plotly；
- pytest（测试开发依赖）。

尽可能使用 Python 标准库完成随机数据生成、日期计算和数据库操作。除非确有必要，不新增 Faker、NumPy、SQLAlchemy、FastAPI 等依赖。

### 7.2 建议目录

```text
project-root/
├── PROJECT_MEMORY.md
├── README.md
├── requirements.txt
├── app.py
├── data/
│   ├── .gitkeep
│   └── app.db              # 初始化脚本生成，不提交真实用户数据
├── src/
│   ├── __init__.py
│   ├── config.py           # 数据时间窗口、随机种子、枚举
│   ├── database.py         # SQLite 连接、建表、查询辅助
│   ├── data_generator.py   # 模拟数据生成
│   ├── data_validation.py  # 数据质量校验
│   ├── metrics.py          # 指标计算
│   └── risk_rules.py       # 客户风险规则
├── scripts/
│   └── init_demo_data.py   # 建库并生成模拟数据
├── tests/
│   ├── test_data_generator.py
│   ├── test_metrics.py
│   └── test_risk_rules.py
└── pages/                  # 如采用 Streamlit 多页面，可按需使用
```

目录可根据现有项目结构做小幅调整，但不要为了遵循目录而大规模重构。

### 7.3 页面组织建议

使用 Streamlit sidebar 或导航组件组织四个模块：

1. 客户经营总览；
2. 客户使用分析；
3. 服务工单分析；
4. 客户风险与运营跟进。

优先保持 UI 简洁、清晰、中文可读。交互筛选必须真实影响分析结果，不要制作无实际作用的装饰控件。

### 7.4 初始化与运行

建议提供以下命令（最终按实际代码调整并写入 README）：

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
# source .venv/bin/activate

pip install -r requirements.txt
python scripts/init_demo_data.py
streamlit run app.py
```

初始化脚本必须明确提示将重建模拟数据。应用正常启动时不应无条件重置数据库。

---

## 8. 测试与验收标准

### 8.1 单元测试

至少覆盖：

- 固定种子下模拟数据数量稳定；
- 每客户每周唯一；
- 活跃率、核心功能采用率、工单解决率计算正确；
- 平均响应 / 解决时长忽略 NULL 时间；
- 分母为 0 时处理正确；
- 风险分数按触发规则累加且最高不超过 100；
- 风险等级边界正确（29、30、59、60 分）；
- 缺失前期基线时不触发下降规则；
- 跟进记录前后窗口数据不足时返回可解释状态。

### 8.2 集成验证

- 能够从空数据库初始化表和数据；
- 外键检查无错误；
- Streamlit 页面能够正常启动；
- 四个模块均可打开；
- 日期和分类筛选不报错；
- 新增跟进记录后能够重新查询到；
- 重启应用后跟进记录仍保留；
- 数据库文件缺失时能给出“请先运行初始化脚本”的明确提示，或按项目选定方案安全初始化空结构，但不得在不提示的情况下覆盖数据。

### 8.3 求职展示验收

项目完成后，应能够在 3–5 分钟内向面试官演示：

1. 客户整体活跃情况；
2. 一个活跃度下降客户的分析过程；
3. 一个工单积压 / 响应较慢的服务问题；
4. 风险分数和触发规则如何得出；
5. 新增一次客户跟进记录；
6. 查看跟进前后指标变化，并解释不能仅凭前后变化证明因果关系。

README 必须包含项目背景、业务问题、技术栈、数据字典 / 表关系、关键指标口径、模拟数据说明、启动方式、测试方式和截图位置。

---

## 9. 推荐开发阶段

Cline 必须分阶段实施，不要一次性生成全部代码后不做验证。

### Phase 0：工作区检查与实现计划

- 阅读本文件；
- 检查工作区、Git 状态和现有文件；
- 输出简短实现计划与可能冲突；
- 不做大规模修改。

### Phase 1：数据库和模拟数据

- 建立 schema；
- 实现 SQLite 初始化；
- 实现固定种子的模拟数据生成；
- 实现数据质量校验；
- 运行生成器和相关测试；
- 检查默认数据量和外键。

**Phase 1 验收后再进入 Phase 2。**

### Phase 2：指标分析和风险规则

- 编写集中式指标函数；
- 编写客户风险规则；
- 编写工单统计和周趋势函数；
- 编写单元测试；
- 用模拟数据库验证指标合理性。

### Phase 3：Streamlit 页面

- 完成客户经营总览；
- 完成客户使用分析；
- 完成服务工单分析；
- 完成客户风险与跟进页面；
- 验证筛选器、图表和新增记录。

### Phase 4：交付整理

- 完善 README；
- 整理截图；
- 检查空数据和异常输入；
- 运行全部测试；
- 给出准确的完成报告和遗留问题。

---

## 10. 给 Cline 的启动任务模板

将下面内容作为 Cline 的首条任务提示：

```text
请先完整阅读项目根目录的 PROJECT_MEMORY.md，并严格遵守其中的项目边界、数据规则和开发阶段。

第一步只做工作区检查：
1. 检查当前目录、文件结构、README、依赖文件和 Git 状态；
2. 判断是否已有代码或文件，禁止未经确认覆盖或删除；
3. 对照 PROJECT_MEMORY.md，指出当前项目状态与目标之间的差距；
4. 给出 Phase 0 检查结果和 Phase 1 的具体文件级实施计划。

在我确认 Phase 1 计划前，不要批量创建或修改文件。不要增加本文未要求的技术栈或功能。后续按 Phase 1 → Phase 2 → Phase 3 → Phase 4 顺序推进；每个阶段完成后先运行测试，并报告实际修改文件、执行命令、测试结果和未解决问题。

项目是使用模拟数据的求职作品，所有页面和文档都必须如实注明模拟数据，不得声称使用真实企业数据或真实运营效果。
```

---

## 11. 当前项目决策记录

- 求职方向：数据分析与数据运营兼顾；
- 开发难度偏好：简单、轻量，优先快速做出可展示成果；
- 最终项目：B2B SaaS 客户使用与服务运营分析平台；
- 数据范围：100 家虚构企业客户、连续 12 周模拟数据；
- 核心数据表：customers、usage_weekly、support_tickets、followup_records；
- 技术方案：Python + SQLite + SQL + Pandas + Streamlit + Plotly + pytest；
- 风险识别：透明规则，不做机器学习预测；
- 运营闭环：客户使用 / 服务问题识别 → 跟进记录 → 指标前后观察；
- 交付重点：真实可运行、指标口径清楚、分析过程可解释、模拟数据标注诚实。

