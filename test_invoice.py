import os
import sys
import json
import tempfile
import shutil

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_store import DataStore, GenericJsonStore
from invoice_manager import InvoiceManager


def run_tests():
    tmpdir = tempfile.mkdtemp(prefix="invoice_test_")
    json_path = os.path.join(tmpdir, "test_invoices.json")
    batch_path = os.path.join(tmpdir, "test_batches.json")
    budget_path = os.path.join(tmpdir, "test_budgets.json")
    csv_path = os.path.join(tmpdir, "test_export.csv")

    try:
        print("=" * 60)
        print("个人发票报销整理器 - 功能验证测试")
        print("=" * 60)

        store = DataStore(json_path)
        batch_store = GenericJsonStore(batch_path)
        budget_store = GenericJsonStore(budget_path)
        manager = InvoiceManager(store, batch_store, budget_store)

        print("\n[测试 1] 新增发票功能")
        print("-" * 60)

        inv1 = manager.add_invoice(
            title="滴滴出行科技有限公司",
            amount=128.50,
            date="2026-05-12",
            inv_type="交通费",
            remark="出差打车",
        )
        print(f"✓ 新增发票1: {inv1['id']} - {inv1['title']} ¥{inv1['amount']}")

        inv2 = manager.add_invoice(
            title="北京肯德基有限公司",
            amount=89.00,
            date="2026-05-20",
            inv_type="餐饮费",
            remark="午餐",
        )
        print(f"✓ 新增发票2: {inv2['id']} - {inv2['title']} ¥{inv2['amount']}")

        inv3 = manager.add_invoice(
            title="上海如家酒店",
            amount=458.00,
            date="2026-06-03",
            inv_type="住宿费",
            remark="培训住宿",
        )
        print(f"✓ 新增发票3: {inv3['id']} - {inv3['title']} ¥{inv3['amount']}")

        inv4 = manager.add_invoice(
            title="京东商城",
            amount=256.80,
            date="2026-06-15",
            inv_type="办公用品",
            status="已报销",
            remark="打印纸",
        )
        print(f"✓ 新增发票4: {inv4['id']} - {inv4['title']} ¥{inv4['amount']} (已报销)")

        all_invoices = manager.list_all()
        assert len(all_invoices) == 4, f"发票数量应为 4, 实际 {len(all_invoices)}"
        print(f"✓ 数据持久化验证通过, JSON 文件中共有 {len(all_invoices)} 条记录")

        print("\n[测试 2] 修改报销状态功能")
        print("-" * 60)

        result = manager.update_status(inv1["id"], "已报销")
        assert result == True, "状态更新应返回 True"
        updated = manager.get_by_id(inv1["id"])
        assert updated["status"] == "已报销", f"状态应为已报销, 实际 {updated['status']}"
        print(f"✓ {inv1['id']} 状态已更新为: {updated['status']}")

        result_bad = manager.update_status("INV-9999", "已报销")
        assert result_bad == False, "不存在的发票应返回 False"
        print("✓ 不存在发票编号的错误处理验证通过")

        print("\n[测试 3] 按月份汇总金额")
        print("-" * 60)

        summary = manager.sum_by_month()
        assert "2026-05" in summary, "应包含 2026-05 月份汇总"
        assert "2026-06" in summary, "应包含 2026-06 月份汇总"
        may_total = summary["2026-05"]["total"]
        assert abs(may_total - 217.50) < 0.01, f"5月总金额应为 217.50, 实际 {may_total}"
        may_count = summary["2026-05"]["count"]
        assert may_count == 2, f"5月发票数应为 2, 实际 {may_count}"
        print(f"✓ 2026-05 汇总: {summary['2026-05']['count']} 张, ¥{summary['2026-05']['total']}, 未报销 ¥{summary['2026-05']['unreimbursed']}")
        print(f"✓ 2026-06 汇总: {summary['2026-06']['count']} 张, ¥{summary['2026-06']['total']}, 未报销 ¥{summary['2026-06']['unreimbursed']}")

        print("\n[测试 4] 筛选未报销发票")
        print("-" * 60)

        unreimbursed = manager.filter_by_status("未报销")
        assert len(unreimbursed) == 2, f"未报销发票应为 2 张, 实际 {len(unreimbursed)}"
        for inv in unreimbursed:
            print(f"  - {inv['id']}: {inv['title']} ¥{inv['amount']} [{inv['type']}]")
        print(f"✓ 未报销发票筛选通过, 共 {len(unreimbursed)} 张")

        may_invoices = manager.filter_by_month("2026-05")
        assert len(may_invoices) == 2, f"5月发票应为 2 张, 实际 {len(may_invoices)}"
        print(f"✓ 按月份筛选通过 (2026-05 共 {len(may_invoices)} 张)")

        print("\n[测试 5] 导出报销清单 CSV")
        print("-" * 60)

        exported_path = manager.export_csv(csv_path)
        assert os.path.exists(exported_path), "CSV 文件应已创建"
        file_size = os.path.getsize(exported_path)
        assert file_size > 0, "CSV 文件不应为空"
        print(f"✓ CSV 导出成功: {exported_path}")
        print(f"  文件大小: {file_size} 字节")

        with open(exported_path, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
        assert len(lines) == 5, f"CSV 应含 1 行表头 + 4 行数据 = 5 行, 实际 {len(lines)}"
        print(f"  CSV 行数验证: {len(lines)} 行 (表头 + {len(lines)-1} 条数据)")
        print(f"  表头: {lines[0].strip()}")

        unreimbursed_csv = os.path.join(tmpdir, "unreimbursed.csv")
        exported_unreimbursed = manager.export_csv(unreimbursed_csv, manager.filter_by_status("未报销"))
        with open(exported_unreimbursed, "r", encoding="utf-8-sig") as f:
            lines_unr = f.readlines()
        assert len(lines_unr) == 3, f"未报销 CSV 应为 3 行, 实际 {len(lines_unr)}"
        print(f"✓ 只导出未报销发票 CSV 验证通过 ({len(lines_unr)-1} 条记录)")

        print("\n[测试 6] 预算控制功能")
        print("-" * 60)

        budget1 = manager.set_budget("2026-05", "交通费", 100.0)
        assert budget1["year_month"] == "2026-05"
        assert budget1["type"] == "交通费"
        assert abs(budget1["amount"] - 100.0) < 0.01
        print(f"✓ 设置预算: {budget1['year_month']} {budget1['type']} ¥{budget1['amount']}")

        budget2 = manager.set_budget("2026-05", "餐饮费", 50.0)
        print(f"✓ 设置预算: {budget2['year_month']} {budget2['type']} ¥{budget2['amount']}")

        budget_val = manager.get_budget("2026-05", "交通费")
        assert abs(budget_val - 100.0) < 0.01
        print(f"✓ 读取预算: 2026-05 交通费 ¥{budget_val}")

        inv5 = manager.add_invoice(
            title="北京出租车公司",
            amount=50.00,
            date="2026-05-25",
            inv_type="交通费",
            remark="机场打车",
        )
        assert "_budget_warning" in inv5, "应触发预算超额警告"
        print(f"✓ 预算超额警告触发: {inv5['id']}")
        print(f"  {inv5['_budget_warning']}")

        budget_val2 = manager.get_budget("2026-05", "交通费")
        used = manager._get_used_amount("2026-05", "交通费")
        print(f"  预算 ¥{budget_val2}, 已用 ¥{used}, 超额 ¥{used - budget_val2:.2f}")

        budget_list = manager.list_budgets()
        assert len(budget_list) == 2
        print(f"✓ 预算列表: 共 {len(budget_list)} 条")

        print("\n[测试 7] 批次管理功能")
        print("-" * 60)

        manager.update_status(inv1["id"], "未报销")

        batch = manager.create_batch(
            name="2026年5月差旅费报销",
            applicant="张三",
            submit_date="2026-06-01",
            remark="5月出差费用",
        )
        assert batch["status"] == "草稿"
        assert batch["name"] == "2026年5月差旅费报销"
        print(f"✓ 创建批次: {batch['id']} - {batch['name']}")
        print(f"  申请人: {batch['applicant']}, 状态: {batch['status']}")
        assert len(batch["status_log"]) == 1
        assert batch["status_log"][0]["status"] == "草稿"
        print(f"✓ 状态日志记录正常")

        result_add = manager.add_invoices_to_batch(batch["id"], [inv1["id"], inv2["id"]])
        assert len(result_add["added"]) == 2, f"应成功添加 2 张, 实际 {len(result_add['added'])}"
        print(f"✓ 批量添加发票: 成功 {len(result_add['added'])} 张")
        for inv_id in result_add["added"]:
            inv = manager.get_by_id(inv_id)
            assert inv["batch_id"] == batch["id"]
        print("✓ 发票 batch_id 关联正确")

        batch_updated = manager.get_batch_by_id(batch["id"])
        assert len(batch_updated["invoice_ids"]) == 2
        print(f"✓ 批次发票数: {len(batch_updated['invoice_ids'])} 张")

        batch_invoices = manager.get_batch_invoices(batch["id"])
        assert len(batch_invoices) == 2
        print(f"✓ 读取批次发票: {len(batch_invoices)} 张")

        budget_warnings = manager.check_batch_budget(batch["id"])
        assert len(budget_warnings) > 0, "批次应有预算超额警告"
        print(f"✓ 批次预算检查: 发现 {len(budget_warnings)} 个警告")
        for w in budget_warnings:
            print(f"  ⚠ {w}")

        print("\n[测试 8] 批次状态流转")
        print("-" * 60)

        result_status = manager.update_batch_status(batch["id"], "已提交", remark="财务请审核")
        assert result_status["old_status"] == "草稿"
        assert result_status["new_status"] == "已提交"
        print(f"✓ 状态流转: 草稿 → 已提交")

        batch_after = manager.get_batch_by_id(batch["id"])
        assert len(batch_after["status_log"]) == 2
        assert batch_after["status_log"][1]["remark"] == "财务请审核"
        print(f"✓ 状态日志已记录备注")

        try:
            manager.update_batch_status(batch["id"], "已打款")
            assert False, "非法状态流转应抛出异常"
        except ValueError as e:
            print(f"✓ 非法状态流转拦截: {e}")

        result_status2 = manager.update_batch_status(batch["id"], "已审核", remark="审核通过")
        assert result_status2["new_status"] == "已审核"
        print(f"✓ 状态流转: 已提交 → 已审核")

        result_status3 = manager.update_batch_status(batch["id"], "已打款")
        assert result_status3["new_status"] == "已打款"
        print(f"✓ 状态流转: 已审核 → 已打款")

        for inv_id in batch_after["invoice_ids"]:
            inv = manager.get_by_id(inv_id)
            assert inv["status"] == "已报销", f"发票 {inv_id} 状态应为已报销"
        print("✓ 批次已打款后，发票状态自动更新为已报销")

        print("\n[测试 9] 批次驳回功能")
        print("-" * 60)

        batch2 = manager.create_batch(
            name="测试驳回批次",
            applicant="李四",
            submit_date="2026-06-10",
        )
        inv6 = manager.add_invoice(
            title="测试发票",
            amount=100.0,
            date="2026-06-05",
            inv_type="其他",
        )
        manager.add_invoices_to_batch(batch2["id"], [inv6["id"]])

        manager.update_batch_status(batch2["id"], "已提交")
        result_reject = manager.update_batch_status(batch2["id"], "已驳回", remark="发票不合规")
        assert result_reject["new_status"] == "已驳回"
        print(f"✓ 状态流转: 已提交 → 已驳回")

        batch2_after = manager.get_batch_by_id(batch2["id"])
        assert len(batch2_after["invoice_ids"]) == 0, "驳回后批次应清空发票"
        inv6_after = manager.get_by_id(inv6["id"])
        assert inv6_after["batch_id"] is None, "驳回后发票应解除批次关联"
        print("✓ 驳回后批次发票已清空，发票已解除关联")

        print("\n[测试 10] 按批次导出 CSV")
        print("-" * 60)

        batch_csv = os.path.join(tmpdir, "batch_export.csv")
        exported_batch = manager.export_batch_csv(batch["id"], batch_csv)
        assert os.path.exists(exported_batch), "批次 CSV 应已创建"
        with open(exported_batch, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
        assert len(lines) == 3, f"批次 CSV 应含 1 行表头 + 2 行数据 = 3 行, 实际 {len(lines)}"
        print(f"✓ 批次导出 CSV 验证通过 ({len(lines)-1} 条记录)")
        print(f"  表头: {lines[0].strip()}")
        assert "预算超额" in lines[0], "导出应包含预算超额列"
        assert "审核备注" in lines[0], "导出应包含审核备注列"
        print("✓ 导出字段包含批次信息、预算提示、审核备注")

        print("\n[测试 11] 数据修复功能")
        print("-" * 60)

        bad_invoices = [
            {
                "id": "INV-BAD01",
                "title": "å¼ ä¸é¥­é¦",
                "amount": -50.0,
                "date": "2026/05/01",
                "type": "车费",
                "status": "报销中",
                "remark": "",
                "created_at": "2026-06-01 10:00:00",
                "batch_id": None,
            },
            {
                "id": "INV-BAD01",
                "title": None,
                "amount": "abc",
                "date": "20260515",
                "type": "餐饮费",
                "status": "已报销",
                "remark": "正常发票",
                "created_at": "2026-06-01 10:00:00",
                "batch_id": None,
            },
            {
                "id": "INV-GOOD",
                "title": "正常发票公司",
                "amount": 200.0,
                "date": "2026-05-20",
                "type": "交通费",
                "status": "未报销",
                "remark": "正常数据",
                "created_at": "2026-06-01 10:00:00",
                "batch_id": None,
            },
        ]

        bad_json_path = os.path.join(tmpdir, "bad_invoices.json")
        with open(bad_json_path, "w", encoding="utf-8") as f:
            json.dump(bad_invoices, f, ensure_ascii=False, indent=2)

        bad_store = DataStore(bad_json_path)
        bad_manager = InvoiceManager(data_store=bad_store)

        report_dry = bad_manager.repair_data(dry_run=True)
        assert report_dry["total_invoices"] == 3
        assert report_dry["dry_run"] == True
        assert len(report_dry["issues"]) == 2, f"应发现 2 条问题记录, 实际 {len(report_dry['issues'])}"
        print(f"✓ DRY-RUN 扫描: 共 {report_dry['total_invoices']} 条, 发现问题 {len(report_dry['issues'])} 条")

        for item in report_dry["issues"]:
            print(f"  [{item['index']}] 发票 {item['invoice_id']}:")
            for issue in item["issues"]:
                print(f"    ✗ {issue}")
            for k, v in item["fixes"].items():
                print(f"    → 修复 {k}: {v!r}")

        report_fix = bad_manager.repair_data(dry_run=False)
        assert report_fix["fixed"] == 2
        assert report_fix["dry_run"] == False
        print(f"✓ 实际修复完成: 修复 {report_fix['fixed']} 条数据")

        fixed_data = bad_store.load_all()
        assert len(fixed_data) == 3
        assert fixed_data[0]["amount"] > 0, "金额应被修正为正数"
        assert fixed_data[0]["type"] == "其他", "非法类型应被修正为其他"
        assert fixed_data[0]["status"] == "未报销", "非法状态应被修正"
        assert fixed_data[0]["date"] == "2026-05-01", "日期格式应被修正"
        assert fixed_data[1]["id"] != fixed_data[0]["id"], "重复ID应被修正"
        assert fixed_data[1]["title"] == "未知抬头", "缺失字段应被填补"
        assert fixed_data[1]["date"] == "2026-05-15", "日期格式应被修正"
        assert fixed_data[1]["amount"] > 0, "非法金额应被修正"
        assert fixed_data[2]["id"] == "INV-GOOD", "正常数据不应被修改"
        print("✓ 修复验证: 乱码、缺失字段、非法金额、非法日期、非法状态、重复ID均已修复")

        report_final = bad_manager.repair_data(dry_run=True)
        assert len(report_final["issues"]) == 0, "修复后不应再有问题"
        print("✓ 修复后再次扫描无问题")

        print("\n[测试 12] 批次列表功能")
        print("-" * 60)

        batches = manager.list_batches()
        assert len(batches) == 2, f"应有 2 个批次, 实际 {len(batches)}"
        print(f"✓ 批次列表: 共 {len(batches)} 个批次")
        for b in batches:
            print(f"  - {b['id']}: {b['name']} [{b['status']}] 发票数: {len(b['invoice_ids'])}")

        print("\n" + "=" * 60)
        print("全部 12 项测试通过 ✓")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ 发生异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
