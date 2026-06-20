import argparse
import sys
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

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
    headers = ["编号", "抬头", "金额", "日期", "类型", "状态", "备注"]
    rows = [
        [i["id"], i["title"], f"¥{i['amount']:.2f}", i["date"], i["type"], i["status"], i["remark"]]
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
    for ym, info in data.items():
        rows.append([ym, info["count"], f"¥{info['total']:.2f}", f"¥{info['unreimbursed']:.2f}"])
        grand_total += info["total"]
        grand_unreimbursed += info["unreimbursed"]
    rows.append(["合计", sum(r[1] for r in rows[:-1]), f"¥{grand_total:.2f}", f"¥{grand_unreimbursed:.2f}"])
    print_table(headers, rows)


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

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    manager = InvoiceManager()

    if args.command == "add":
        cmd_add(manager, args)
    elif args.command == "status":
        cmd_status(manager, args)
    elif args.command == "export":
        cmd_export(manager, args)
    elif args.command == "list":
        cmd_list(manager, args)
    elif args.command == "summary":
        cmd_summary(manager, args)


if __name__ == "__main__":
    main()
