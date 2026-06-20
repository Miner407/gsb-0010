import argparse
import sys
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")

from invoice_manager import InvoiceManager


def print_table(headers, rows):
    if not rows:
        print("(无数据)")
        return
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    print(separator)
    print("|" + "|".join(f" {h:<{col_widths[i]}} " for i, h in enumerate(headers)) + "|")
    print(separator)
    for row in rows:
        print("|" + "|".join(f" {str(cell):<{col_widths[i]}} " for i, cell in enumerate(row)) + "|")
    print(separator)


def cmd_add(manager, args):
    try:
        inv = manager.add_invoice(
            title=args.title,
            amount=args.amount,
            date=args.date,
            inv_type=args.type,
            remark=args.remark or "",
            status=args.status or "未报销",
        )
        print(f"新增成功: {inv['id']} - {inv['title']} ¥{inv['amount']}")
        if "_budget_warning" in inv:
            print(f"⚠ {inv['_budget_warning']}")
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_status(manager, args):
    if args.status not in InvoiceManager.VALID_STATUS:
        print(f"错误: 状态必须是 {', '.join(InvoiceManager.VALID_STATUS)}", file=sys.stderr)
        sys.exit(1)
    ok = manager.update_status(args.id, args.status)
    if ok:
        print(f"已更新 {args.id} 的状态为 '{args.status}'")
    else:
        print(f"错误: 未找到发票编号 {args.id}", file=sys.stderr)
        sys.exit(1)


def cmd_export(manager, args):
    try:
        invoices = None
        if args.unreimbursed:
            invoices = manager.filter_by_status("未报销")
            print(f"筛选未报销发票: 共 {len(invoices)} 张")
        elif args.month:
            invoices = manager.filter_by_month(args.month)
            print(f"筛选 {args.month} 月份发票: 共 {len(invoices)} 张")
        path = manager.export_csv(args.output, invoices)
        print(f"导出成功: {path}")
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_list(manager, args):
    invoices = manager.list_all()
    if args.status:
        invoices = [i for i in invoices if i["status"] == args.status]
    if args.month:
        invoices = [i for i in invoices if i["date"].startswith(args.month)]
    headers = ["编号", "抬头", "金额", "日期", "类型", "状态", "批次", "备注"]
    rows = [
        [i["id"], i["title"], f"¥{i['amount']:.2f}", i["date"], i["type"], i["status"], i.get("batch_id", ""), i["remark"]]
        for i in invoices
    ]
    print(f"共 {len(invoices)} 条记录")
    print_table(headers, rows)


def cmd_summary(manager, args):
    data = manager.sum_by_month()
    if not data:
        print("暂无数据")
        return
    headers = ["月份", "发票数", "总金额", "未报销金额"]
    rows = []
    grand_total = 0.0
    grand_unreimbursed = 0.0
    grand_count = 0
    for ym, info in data.items():
        rows.append([ym, info["count"], f"¥{info['total']:.2f}", f"¥{info['unreimbursed']:.2f}"])
        grand_total += info["total"]
        grand_unreimbursed += info["unreimbursed"]
        grand_count += info["count"]
    rows.append(["合计", grand_count, f"¥{grand_total:.2f}", f"¥{grand_unreimbursed:.2f}"])
    print_table(headers, rows)


def cmd_batch_create(manager, args):
    try:
        batch = manager.create_batch(
            name=args.name,
            applicant=args.applicant,
            submit_date=args.submit_date,
            remark=args.remark or "",
        )
        print(f"批次创建成功: {batch['id']} - {batch['name']}")
        print(f"  申请人: {batch['applicant']}")
        print(f"  提交日期: {batch['submit_date']}")
        print(f"  状态: {batch['status']}")
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_batch_add(manager, args):
    try:
        invoice_ids = args.ids.split(",") if "," in args.ids else args.ids.split()
        invoice_ids = [s.strip() for s in invoice_ids if s.strip()]
        result = manager.add_invoices_to_batch(args.batch_id, invoice_ids)
        print(f"批次 {result['batch_id']} 处理结果:")
        print(f"  成功添加: {len(result['added'])} 张 {result['added']}")
        if result["already_in"]:
            print(f"  已在其他批次: {result['already_in']}")
        if result["not_found"]:
            print(f"  不存在: {result['not_found']}")
        if result["not_unreimbursed"]:
            print(f"  非未报销状态: {result['not_unreimbursed']}")
        if result["warnings"]:
            for w in result["warnings"]:
                print(f"  ⚠ {w}")
        budget_warnings = manager.check_batch_budget(args.batch_id)
        if budget_warnings:
            print("\n批次预算检查:")
            for w in budget_warnings:
                print(f"  ⚠ {w}")
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_batch_status(manager, args):
    try:
        result = manager.update_batch_status(
            batch_id=args.batch_id,
            new_status=args.status,
            remark=args.remark or "",
        )
        print(f"批次 {result['batch_id']} 状态已更新:")
        print(f"  {result['old_status']} → {result['new_status']}")
        if result["new_status"] == "已打款":
            batch = manager.get_batch_by_id(args.batch_id)
            print(f"  已将批次内 {len(batch['invoice_ids'])} 张发票状态更新为 '已报销'")
        if result["new_status"] == "已驳回":
            print(f"  已清空批次内发票并解除关联")
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_batch_list(manager, args):
    batches = manager.list_batches()
    if not batches:
        print("(暂无批次)")
        return
    headers = ["批次编号", "名称", "申请人", "提交日期", "状态", "发票数"]
    rows = []
    for b in batches:
        rows.append([b["id"], b["name"], b["applicant"], b["submit_date"], b["status"], len(b["invoice_ids"])])
    print(f"共 {len(batches)} 个批次")
    print_table(headers, rows)

    if args.detail:
        for b in batches:
            print(f"\n批次 {b['id']} - {b['name']} 详情:")
            print(f"  备注: {b.get('remark', '')}")
            print(f"  状态流转日志:")
            for log in b["status_log"]:
                print(f"    [{log['time']}] {log['status']} - {log['remark']}")
            invoices = manager.get_batch_invoices(b["id"])
            if invoices:
                print(f"  包含发票 ({len(invoices)} 张):")
                for inv in invoices:
                    print(f"    {inv['id']}: {inv['title']} ¥{inv['amount']:.2f} [{inv['type']}]")


def cmd_batch_export(manager, args):
    try:
        path = manager.export_batch_csv(args.batch_id, args.output)
        print(f"批次导出成功: {path}")
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_budget_set(manager, args):
    try:
        budget = manager.set_budget(args.month, args.type, args.amount)
        print(f"预算设置成功: {budget['year_month']} {budget['type']} ¥{budget['amount']:.2f}")
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_budget_list(manager, args):
    budgets = manager.list_budgets()
    if not budgets:
        print("(暂无预算设置)")
        return
    headers = ["预算编号", "月份", "类型", "预算金额", "已使用", "剩余", "更新时间"]
    rows = []
    for b in budgets:
        used = manager._get_used_amount(b["year_month"], b["type"])
        remaining = b["amount"] - used
        rows.append([
            b["id"],
            b["year_month"],
            b["type"],
            f"¥{b['amount']:.2f}",
            f"¥{used:.2f}",
            f"¥{remaining:.2f}",
            b["updated_at"],
        ])
    print(f"共 {len(budgets)} 条预算设置")
    print_table(headers, rows)


def cmd_repair(manager, args):
    dry_run = not args.fix
    report = manager.repair_data(dry_run=dry_run)

    if "error" in report:
        print(f"错误: {report['error']}", file=sys.stderr)
        sys.exit(1)

    mode = "DRY-RUN (仅扫描)" if report["dry_run"] else "实际修复"
    print("=" * 60)
    print(f"数据修复报告 [{mode}]")
    print("=" * 60)
    print(f"扫描发票总数: {report['total_invoices']}")
    print(f"发现问题条数: {len(report['issues'])}")
    print(f"可修复条数: {report['fixed']}")
    print()

    if not report["issues"]:
        print("✓ 未发现任何问题，数据正常")
        return

    for item in report["issues"]:
        idx = item.get("index", -1)
        inv_id = item.get("invoice_id", "未知")
        print(f"[{idx}] 发票 {inv_id}:")
        for issue in item["issues"]:
            print(f"  ✗ {issue}")
        if item["fixes"]:
            for k, v in item["fixes"].items():
                print(f"  → 修复 {k}: {v!r}")
        print()

    if report["dry_run"]:
        print("如需实际修复，请添加 --fix 参数重新运行")
    else:
        print(f"✓ 已修复 {report['fixed']} 条数据")


def main():
    parser = argparse.ArgumentParser(description="个人发票报销整理器")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    p_add = subparsers.add_parser("add", help="新增发票")
    p_add.add_argument("-t", "--title", required=True, help="发票抬头")
    p_add.add_argument("-a", "--amount", type=float, required=True, help="金额")
    p_add.add_argument("-d", "--date", required=True, help="开票日期 (YYYY-MM-DD)")
    p_add.add_argument("-y", "--type", required=True, help=f"类型: {', '.join(InvoiceManager.VALID_TYPES)}")
    p_add.add_argument("-r", "--remark", default="", help="备注")
    p_add.add_argument("-s", "--status", default="未报销", help="状态: 未报销/已报销")

    p_status = subparsers.add_parser("status", help="修改报销状态")
    p_status.add_argument("-i", "--id", required=True, help="发票编号")
    p_status.add_argument("-s", "--status", required=True, help="新状态: 未报销/已报销")

    p_export = subparsers.add_parser("export", help="导出 CSV")
    p_export.add_argument("-o", "--output", default=f"报销清单_{datetime.now().strftime('%Y%m%d')}.csv", help="输出文件路径")
    p_export.add_argument("-u", "--unreimbursed", action="store_true", help="只导出未报销")
    p_export.add_argument("-m", "--month", help="只导出指定月份 (YYYY-MM)")

    p_list = subparsers.add_parser("list", help="列出发票")
    p_list.add_argument("-s", "--status", help="按状态筛选")
    p_list.add_argument("-m", "--month", help="按月份筛选 (YYYY-MM)")

    subparsers.add_parser("summary", help="按月份汇总金额")

    p_batch_create = subparsers.add_parser("batch-create", help="创建报销批次")
    p_batch_create.add_argument("-n", "--name", required=True, help="批次名称")
    p_batch_create.add_argument("-p", "--applicant", required=True, help="申请人")
    p_batch_create.add_argument("-d", "--submit-date", required=True, help="提交日期 (YYYY-MM-DD)")
    p_batch_create.add_argument("-r", "--remark", default="", help="备注")

    p_batch_add = subparsers.add_parser("batch-add", help="添加发票到批次")
    p_batch_add.add_argument("-b", "--batch-id", required=True, help="批次编号")
    p_batch_add.add_argument("-i", "--ids", required=True, help="发票编号列表，用逗号或空格分隔")

    p_batch_status = subparsers.add_parser("batch-status", help="更新批次状态")
    p_batch_status.add_argument("-b", "--batch-id", required=True, help="批次编号")
    p_batch_status.add_argument("-s", "--status", required=True, help=f"新状态: {', '.join(InvoiceManager.BATCH_STATUS)}")
    p_batch_status.add_argument("-r", "--remark", default="", help="状态变更备注")

    p_batch_list = subparsers.add_parser("batch-list", help="列出所有批次")
    p_batch_list.add_argument("--detail", action="store_true", help="显示详细信息")

    p_batch_export = subparsers.add_parser("batch-export", help="按批次导出 CSV")
    p_batch_export.add_argument("-b", "--batch-id", required=True, help="批次编号")
    p_batch_export.add_argument("-o", "--output", default=f"批次报销_{datetime.now().strftime('%Y%m%d')}.csv", help="输出文件路径")

    p_budget_set = subparsers.add_parser("budget-set", help="设置月度预算")
    p_budget_set.add_argument("-m", "--month", required=True, help="月份 (YYYY-MM)")
    p_budget_set.add_argument("-y", "--type", required=True, help=f"类型: {', '.join(InvoiceManager.VALID_TYPES)}")
    p_budget_set.add_argument("-a", "--amount", type=float, required=True, help="预算金额")

    subparsers.add_parser("budget-list", help="列出所有预算")

    p_repair = subparsers.add_parser("repair", help="数据修复命令")
    p_repair.add_argument("--fix", action="store_true", help="实际修复（默认仅扫描）")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    manager = InvoiceManager()

    commands = {
        "add": cmd_add,
        "status": cmd_status,
        "export": cmd_export,
        "list": cmd_list,
        "summary": cmd_summary,
        "batch-create": cmd_batch_create,
        "batch-add": cmd_batch_add,
        "batch-status": cmd_batch_status,
        "batch-list": cmd_batch_list,
        "batch-export": cmd_batch_export,
        "budget-set": cmd_budget_set,
        "budget-list": cmd_budget_list,
        "repair": cmd_repair,
    }

    if args.command in commands:
        commands[args.command](manager, args)


if __name__ == "__main__":
    main()
