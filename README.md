# 个人发票报销整理器

一个基于 Python 的命令行工具，用于管理个人发票报销流程。支持发票录入、批次管理、预算控制、数据修复和 CSV 导出。

## 功能特性

### 核心功能
- **发票管理**: 新增、查询、修改状态、按月份汇总
- **报销批次管理**: 创建批次、添加发票、状态流转（草稿→已提交→已审核→已打款/已驳回）
- **预算控制**: 按月度按发票类型设置预算，超预算自动提示
- **数据修复**: 扫描并修复 JSON 数据中的乱码、缺失字段、非法数据
- **CSV 导出**: 支持全量导出、按状态导出、按月份导出、按批次导出

## 环境要求

- Python >= 3.7
- 仅使用 Python 标准库，无需安装额外依赖

## 快速开始

### 查看帮助
```bash
python main.py --help
```

### 查看子命令帮助
```bash
python main.py add --help
python main.py batch-create --help
```

---

## 命令用法

### 1. 发票管理命令

#### 新增发票
```bash
python main.py add -t "滴滴出行科技有限公司" -a 128.50 -d 2026-05-12 -y 交通费 -r "出差打车"
```
参数说明:
- `-t, --title`: 发票抬头 (必填)
- `-a, --amount`: 金额 (必填，必须大于0)
- `-d, --date`: 开票日期，格式 YYYY-MM-DD (必填)
- `-y, --type`: 发票类型 (必填)，可选值：交通费、餐饮费、住宿费、办公用品、通讯费、医疗费、其他
- `-r, --remark`: 备注 (可选)
- `-s, --status`: 状态 (可选)，可选值：未报销、已报销，默认：未报销

#### 修改发票状态
```bash
python main.py status -i INV-0001 -s 已报销
```

#### 列出发票
```bash
# 列出全部
python main.py list

# 按状态筛选
python main.py list -s 未报销

# 按月份筛选
python main.py list -m 2026-05
```

#### 按月份汇总
```bash
python main.py summary
```

#### 导出 CSV
```bash
# 导出全部
python main.py export -o 报销清单.csv

# 只导出未报销
python main.py export -u

# 只导出指定月份
python main.py export -m 2026-05
```

---

### 2. 报销批次管理命令

#### 创建报销批次
```bash
python main.py batch-create -n "2026年5月差旅费报销" -p 张三 -d 2026-06-01 -r "5月出差费用"
```
参数说明:
- `-n, --name`: 批次名称 (必填)
- `-p, --applicant`: 申请人 (必填)
- `-d, --submit-date`: 提交日期，格式 YYYY-MM-DD (必填)
- `-r, --remark`: 备注 (可选)

#### 添加发票到批次
```bash
# 单个发票
python main.py batch-add -b BAT-0001 -i INV-0001

# 多个发票 (逗号分隔)
python main.py batch-add -b BAT-0001 -i "INV-0001,INV-0002,INV-0003"

# 多个发票 (空格分隔)
python main.py batch-add -b BAT-0001 -i "INV-0001 INV-0002 INV-0003"
```

> **注意**: 仅草稿状态的批次可以添加发票；已报销或已在其他批次的发票无法添加

#### 更新批次状态
```bash
# 草稿 → 已提交
python main.py batch-status -b BAT-0001 -s 已提交 -r "请财务审核"

# 已提交 → 已审核
python main.py batch-status -b BAT-0001 -s 已审核 -r "审核通过，发票齐全"

# 已审核 → 已打款
python main.py batch-status -b BAT-0001 -s 已打款

# 已提交 → 已驳回
python main.py batch-status -b BAT-0001 -s 已驳回 -r "缺少餐饮发票明细"
```

**状态流转规则**:
| 当前状态 | 可流转到 |
|---------|---------|
| 草稿 | 已提交 |
| 已提交 | 已审核、已驳回 |
| 已审核 | 已打款、已驳回 |
| 已打款 | - (终态) |
| 已驳回 | 已提交 |

**状态变更副作用**:
- 批次状态变为 `已打款` 时，批次内所有发票状态自动更新为 `已报销`
- 批次状态变为 `已驳回` 时，批次内所有发票自动解除批次关联

#### 列出所有批次
```bash
# 简要列表
python main.py batch-list

# 详细信息（含状态日志和发票明细）
python main.py batch-list --detail
```

#### 按批次导出 CSV
```bash
python main.py batch-export -b BAT-0001 -o 批次报销_202605.csv
```

导出字段包含:
- 批次信息：批次编号、批次名称、申请人、批次状态
- 发票信息：发票编号、发票抬头、金额、开票日期、发票类型、发票状态、发票备注
- 预算信息：月度预算、月度已用、是否超额
- 审核信息：审核备注

---

### 3. 预算控制命令

#### 设置月度预算
```bash
# 设置 2026年5月 交通费 预算 1000元
python main.py budget-set -m 2026-05 -y 交通费 -a 1000.00

# 设置 2026年5月 餐饮费 预算 500元
python main.py budget-set -m 2026-05 -y 餐饮费 -a 500.00
```

#### 查看所有预算
```bash
python main.py budget-list
```

**预算提示触发时机**:
1. 新增发票时，若该月份该类型已用金额 + 新增金额 > 预算，自动提示
2. 添加发票到批次时，若该月份该类型已超预算，自动提示
3. 按批次导出 CSV 时，包含预算超额标志列

---

### 4. 数据修复命令

#### 扫描数据（仅查看问题，不修改）
```bash
python main.py repair
```

#### 实际修复数据
```bash
python main.py repair --fix
```

**可检测和修复的问题**:
| 问题类型 | 修复方式 |
|---------|---------|
| 中文乱码 | 清理无效字符，标记为"已修复_"前缀 |
| 缺失必填字段 | 填充默认值 (id自动生成，title="未知抬头"，type="其他"，status="未报销"等) |
| 非法金额 (≤0 或非数字) | 修正为 0.01 |
| 非法日期格式 | 尝试解析并转换为 YYYY-MM-DD，失败则设为 1970-01-01 |
| 非法发票类型 | 修正为 "其他" |
| 非法发票状态 | 智能映射 (报销中→未报销，已支付→已报销，其他→未报销) |
| 重复ID | 自动生成新的唯一ID |

---

## 数据文件结构

项目数据存储在当前工作目录的 JSON 文件中：

### 1. invoices.json - 发票数据
```json
[
  {
    "id": "INV-0001",
    "title": "滴滴出行科技有限公司",
    "amount": 128.50,
    "date": "2026-05-12",
    "type": "交通费",
    "status": "未报销",
    "remark": "出差打车",
    "created_at": "2026-06-01 10:30:00",
    "batch_id": "BAT-0001"
  }
]
```

### 2. batches.json - 批次数据
```json
[
  {
    "id": "BAT-0001",
    "name": "2026年5月差旅费报销",
    "applicant": "张三",
    "submit_date": "2026-06-01",
    "remark": "5月出差费用",
    "status": "已审核",
    "invoice_ids": ["INV-0001", "INV-0002"],
    "status_log": [
      {"status": "草稿", "time": "2026-06-01 10:00:00", "remark": "创建批次"},
      {"status": "已提交", "time": "2026-06-01 11:00:00", "remark": "请财务审核"},
      {"status": "已审核", "time": "2026-06-02 09:00:00", "remark": "审核通过"}
    ],
    "created_at": "2026-06-01 10:00:00"
  }
]
```

### 3. budgets.json - 预算数据
```json
[
  {
    "id": "BGT-0001",
    "year_month": "2026-05",
    "type": "交通费",
    "amount": 1000.00,
    "created_at": "2026-05-01 00:00:00",
    "updated_at": "2026-05-01 00:00:00"
  }
]
```

---

## 验证步骤

### 运行单元测试
```bash
python test_invoice.py
```

### 三组可运行验证命令

#### 验证组 1: 批次创建与状态流转验证
```bash
# 1. 清理旧数据 (可选)
del invoices.json batches.json budgets.json

# 2. 新增 3 张未报销发票
python main.py add -t "滴滴出行" -a 128.50 -d 2026-05-12 -y 交通费 -r "出差打车"
python main.py add -t "北京肯德基" -a 89.00 -d 2026-05-20 -y 餐饮费 -r "午餐"
python main.py add -t "上海如家酒店" -a 458.00 -d 2026-06-03 -y 住宿费 -r "培训住宿"

# 3. 创建报销批次
python main.py batch-create -n "2026年5月差旅费" -p 张三 -d 2026-06-20 -r "5月出差费用报销"

# 4. 添加发票到批次
python main.py batch-add -b BAT-0001 -i "INV-0001 INV-0002"

# 5. 查看批次列表（详细模式）
python main.py batch-list --detail

# 6. 状态流转: 草稿 → 已提交 → 已审核 → 已打款
python main.py batch-status -b BAT-0001 -s 已提交 -r "财务请审核"
python main.py batch-status -b BAT-0001 -s 已审核 -r "审核通过，票据齐全"
python main.py batch-status -b BAT-0001 -s 已打款

# 7. 验证发票状态已自动更新
python main.py list -s 已报销
```

**预期结果**:
- 批次状态从 "草稿" → "已提交" → "已审核" → "已打款"
- 状态日志包含每条流转记录和备注
- 批次内的 INV-0001 和 INV-0002 状态自动变为 "已报销"

---

#### 验证组 2: 预算超额提示验证
```bash
# 1. 清理旧数据 (可选)
del invoices.json batches.json budgets.json

# 2. 设置 2026年6月 交通费预算 200元
python main.py budget-set -m 2026-06 -y 交通费 -a 200.00

# 3. 查看预算
python main.py budget-list

# 4. 新增第1张交通费发票 (150元，未超额)
python main.py add -t "滴滴出行" -a 150.00 -d 2026-06-05 -y 交通费 -r "市内打车"

# 5. 新增第2张交通费发票 (100元，合计250元，应触发超额警告)
python main.py add -t "首汽约车" -a 100.00 -d 2026-06-10 -y 交通费 -r "机场接送"

# 6. 创建批次并添加发票
python main.py batch-create -n "6月交通费报销" -p 李四 -d 2026-06-20
python main.py batch-add -b BAT-0001 -i "INV-0001 INV-0002"

# 7. 查看预算列表，确认剩余预算为负数
python main.py budget-list
```

**预期结果**:
- 新增第2张发票时显示 "预算超额警告"
- 添加发票到批次时再次显示预算警告
- budget-list 中 2026-06 交通费的"剩余"显示为 -50.00

---

#### 验证组 3: 数据修复与批次导出验证
```bash
# 1. 清理旧数据
del invoices.json batches.json budgets.json

# 2. 手动创建有问题的 invoices.json (通过Python脚本)
python -c "
import json
bad_data = [
    {'id': 'INV-BAD01', 'title': 'å¼ ä¸é¥­é¦', 'amount': -50.0, 'date': '2026/05/01', 'type': '车费', 'status': '报销中', 'remark': '', 'created_at': '2026-06-01 10:00:00', 'batch_id': None},
    {'id': 'INV-BAD01', 'title': None, 'amount': 'abc', 'date': '20260515', 'type': '餐饮费', 'status': '已报销', 'remark': '正常发票', 'created_at': '2026-06-01 10:00:00', 'batch_id': None},
    {'id': 'INV-GOOD', 'title': '正常发票公司', 'amount': 200.0, 'date': '2026-05-20', 'type': '交通费', 'status': '未报销', 'remark': '正常数据', 'created_at': '2026-06-01 10:00:00', 'batch_id': None}
]
with open('invoices.json', 'w', encoding='utf-8') as f:
    json.dump(bad_data, f, ensure_ascii=False, indent=2)
print('已创建测试数据')
"

# 3. DRY-RUN 扫描，查看问题
python main.py repair

# 4. 实际修复数据
python main.py repair --fix

# 5. 再次扫描，确认无问题
python main.py repair

# 6. 查看修复后的数据
python main.py list

# 7. 设置预算并创建批次
python main.py budget-set -m 2026-05 -y 交通费 -a 150.00
python main.py batch-create -n "修复数据测试批次" -p 王五 -d 2026-06-20
python main.py batch-add -b BAT-0001 -i "INV-0001 INV-0002 INV-0003"

# 8. 提交并审核批次
python main.py batch-status -b BAT-0001 -s 已提交
python main.py batch-status -b BAT-0001 -s 已审核 -r "修复数据审核通过"

# 9. 按批次导出 CSV (包含预算超额提示和审核备注)
python main.py batch-export -b BAT-0001 -o 批次导出_修复验证.csv

# 10. 查看导出的 CSV 文件内容
type 批次导出_修复验证.csv
```

**预期结果**:
- 第1次 repair 扫描发现 2 条问题记录，列出具体问题和修复方案
- 第2次 repair --fix 实际修复 2 条数据
- 第3次 repair 扫描显示 "未发现任何问题，数据正常"
- 修复后的数据中：
  - 第1条：title 被清理，amount 变为 0.01，date 变为 2026-05-01，type 变为其他，status 变为未报销
  - 第2条：id 被重新生成，title 变为"未知抬头"，amount 变为 0.01，date 变为 2026-05-15
  - 第3条：保持不变
- 批次导出 CSV 包含"预算超额"和"审核备注"列，其中交通费显示为超额

---

## 已修复的 Bug

1. **CLI 中文参数乱码**: 在 Windows 平台增加 `sys.stdin.reconfigure(encoding="utf-8")`，确保中文参数正确解析
2. **summary 合计行发票数错误**: 原代码使用 `sum(r[1] for r in rows[:-1])`，在只有1个月数据时会漏掉该月。改为使用独立的 `grand_count` 变量累加

## 项目文件说明

| 文件 | 说明 |
|------|------|
| [main.py](file:///c:/Users/lenovo/Documents/solo/项目/gsb-0010/main.py) | CLI 入口，命令行参数解析和调度 |
| [invoice_manager.py](file:///c:/Users/lenovo/Documents/solo/项目/gsb-0010/invoice_manager.py) | 核心业务逻辑，发票/批次/预算/修复管理 |
| [data_store.py](file:///c:/Users/lenovo/Documents/solo/项目/gsb-0010/data_store.py) | JSON 文件持久化层 |
| [test_invoice.py](file:///c:/Users/lenovo/Documents/solo/项目/gsb-0010/test_invoice.py) | 单元测试，12个测试用例 |
| [requirements.txt](file:///c:/Users/lenovo/Documents/solo/项目/gsb-0010/requirements.txt) | 依赖声明（仅标准库） |
