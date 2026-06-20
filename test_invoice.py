import os
import sys
import json
import tempfile
import shutil

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_store import DataStore
from invoice_manager import InvoiceManager


def run_tests():
    tmpdir = tempfile.mkdtemp(prefix="invoice_test_")
    json_path = os.path.join(tmpdir, "test_invoices.json")
    csv_path = os.path.join(tmpdir, "test_export.csv")

    try:
        print("=" * 60)
        print("个人发票报销整理器 - 功能验证测试")
        print("=" * 60)

        store = DataStore(json_path)
        manager = InvoiceManager(store)

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

        print("\n" + "=" * 60)
        print("全部 5 项测试通过 ✓")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
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
