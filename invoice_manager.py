import csv
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict

from data_store import DataStore


class InvoiceManager:
    VALID_TYPES = ["交通费", "餐饮费", "住宿费", "办公用品", "通讯费", "医疗费", "其他"]
    VALID_STATUS = ["未报销", "已报销"]

    def __init__(self, data_store: Optional[DataStore] = None):
        self.store = data_store or DataStore()

    def add_invoice(
        self,
        title: str,
        amount: float,
        date: str,
        inv_type: str,
        remark: str = "",
        status: str = "未报销",
    ) -> Dict[str, Any]:
        if not title:
            raise ValueError("发票抬头不能为空")
        if amount <= 0:
            raise ValueError("金额必须大于 0")
        if inv_type not in self.VALID_TYPES:
            raise ValueError(f"类型必须是: {', '.join(self.VALID_TYPES)}")
        if status not in self.VALID_STATUS:
            raise ValueError(f"状态必须是: {', '.join(self.VALID_STATUS)}")
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("日期格式必须是 YYYY-MM-DD")

        invoice = {
            "id": self.store.get_next_id(),
            "title": title,
            "amount": round(float(amount), 2),
            "date": date,
            "type": inv_type,
            "status": status,
            "remark": remark,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.store.append(invoice)
        return invoice

    def update_status(self, invoice_id: str, status: str) -> bool:
        if status not in self.VALID_STATUS:
            raise ValueError(f"状态必须是: {', '.join(self.VALID_STATUS)}")
        return self.store.update(invoice_id, {"status": status})

    def list_all(self) -> List[Dict[str, Any]]:
        return self.store.load_all()

    def filter_by_status(self, status: str) -> List[Dict[str, Any]]:
        if status not in self.VALID_STATUS:
            raise ValueError(f"状态必须是: {', '.join(self.VALID_STATUS)}")
        return [inv for inv in self.store.load_all() if inv["status"] == status]

    def filter_by_month(self, year_month: str) -> List[Dict[str, Any]]:
        try:
            datetime.strptime(year_month, "%Y-%m")
        except ValueError:
            raise ValueError("月份格式必须是 YYYY-MM")
        return [inv for inv in self.store.load_all() if inv["date"].startswith(year_month)]

    def sum_by_month(self) -> Dict[str, Dict[str, Any]]:
        invoices = self.store.load_all()
        monthly = defaultdict(lambda: {"total": 0.0, "count": 0, "unreimbursed": 0.0})
        for inv in invoices:
            ym = inv["date"][:7]
            monthly[ym]["total"] += inv["amount"]
            monthly[ym]["count"] += 1
            if inv["status"] == "未报销":
                monthly[ym]["unreimbursed"] += inv["amount"]
        result = {}
        for ym in sorted(monthly.keys()):
            result[ym] = {
                "total": round(monthly[ym]["total"], 2),
                "count": monthly[ym]["count"],
                "unreimbursed": round(monthly[ym]["unreimbursed"], 2),
            }
        return result

    def export_csv(self, output_path: str, invoices: Optional[List[Dict[str, Any]]] = None) -> str:
        if invoices is None:
            invoices = self.store.load_all()
        if not invoices:
            raise ValueError("没有可导出的发票记录")

        fieldnames = ["id", "title", "amount", "date", "type", "status", "remark", "created_at"]
        headers = {
            "id": "发票编号",
            "title": "发票抬头",
            "amount": "金额(元)",
            "date": "开票日期",
            "type": "发票类型",
            "status": "报销状态",
            "remark": "备注",
            "created_at": "录入时间",
        }

        dir_name = os.path.dirname(output_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)

        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow(headers)
            for inv in invoices:
                writer.writerow({k: inv.get(k, "") for k in fieldnames})
        return os.path.abspath(output_path)

    def get_by_id(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        for inv in self.store.load_all():
            if inv["id"] == invoice_id:
                return inv
        return None
