import csv
import os
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from data_store import DataStore, GenericJsonStore


class InvoiceManager:
    VALID_TYPES = ["交通费", "餐饮费", "住宿费", "办公用品", "通讯费", "医疗费", "其他"]
    VALID_STATUS = ["未报销", "已报销"]
    BATCH_STATUS = ["草稿", "已提交", "已审核", "已打款", "已驳回"]
    BATCH_STATUS_FLOW = {
        "草稿": ["已提交"],
        "已提交": ["已审核", "已驳回"],
        "已审核": ["已打款", "已驳回"],
        "已打款": [],
        "已驳回": ["已提交"],
    }

    def __init__(
        self,
        data_store: Optional[DataStore] = None,
        batch_store: Optional[GenericJsonStore] = None,
        budget_store: Optional[GenericJsonStore] = None,
    ):
        self.store = data_store or DataStore()
        self.batch_store = batch_store or GenericJsonStore("batches.json")
        self.budget_store = budget_store or GenericJsonStore("budgets.json")

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

        budget_warning = self._check_budget(date[:7], inv_type, amount)

        invoice = {
            "id": self.store.get_next_id(),
            "title": title,
            "amount": round(float(amount), 2),
            "date": date,
            "type": inv_type,
            "status": status,
            "remark": remark,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "batch_id": None,
        }
        self.store.append(invoice)
        if budget_warning:
            invoice["_budget_warning"] = budget_warning
        return invoice

    def _check_budget(self, year_month: str, inv_type: str, amount: float) -> Optional[str]:
        budget = self.get_budget(year_month, inv_type)
        if budget is None:
            return None
        used = self._get_used_amount(year_month, inv_type)
        new_total = used + amount
        if new_total > budget:
            return (
                f"预算超额警告: {year_month} 月 {inv_type} 预算 ¥{budget:.2f}, "
                f"已使用 ¥{used:.2f}, 新增 ¥{amount:.2f} 后合计 ¥{new_total:.2f}, "
                f"超额 ¥{new_total - budget:.2f}"
            )
        return None

    def _get_used_amount(self, year_month: str, inv_type: str) -> float:
        invoices = self.store.load_all()
        total = 0.0
        for inv in invoices:
            if inv["date"].startswith(year_month) and inv["type"] == inv_type:
                total += inv["amount"]
        return round(total, 2)

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

        fieldnames = ["id", "title", "amount", "date", "type", "status", "remark", "created_at", "batch_id"]
        headers = {
            "id": "发票编号",
            "title": "发票抬头",
            "amount": "金额(元)",
            "date": "开票日期",
            "type": "发票类型",
            "status": "报销状态",
            "remark": "备注",
            "created_at": "录入时间",
            "batch_id": "所属批次",
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

    def create_batch(
        self,
        name: str,
        applicant: str,
        submit_date: str,
        remark: str = "",
    ) -> Dict[str, Any]:
        if not name:
            raise ValueError("批次名称不能为空")
        if not applicant:
            raise ValueError("申请人不能为空")
        try:
            datetime.strptime(submit_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("提交日期格式必须是 YYYY-MM-DD")

        batch = {
            "id": self.batch_store.get_next_id("BAT"),
            "name": name,
            "applicant": applicant,
            "submit_date": submit_date,
            "remark": remark,
            "status": "草稿",
            "invoice_ids": [],
            "status_log": [
                {
                    "status": "草稿",
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "remark": "创建批次",
                }
            ],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.batch_store.append(batch)
        return batch

    def add_invoices_to_batch(self, batch_id: str, invoice_ids: List[str]) -> Dict[str, Any]:
        batch = self.batch_store.get_by_id(batch_id)
        if batch is None:
            raise ValueError(f"批次不存在: {batch_id}")
        if batch["status"] != "草稿":
            raise ValueError(f"仅草稿状态的批次可以添加发票，当前状态: {batch['status']}")

        warnings = []
        added = []
        already_in = []
        not_found = []
        not_unreimbursed = []

        for inv_id in invoice_ids:
            inv = self.get_by_id(inv_id)
            if inv is None:
                not_found.append(inv_id)
                continue
            if inv["status"] != "未报销":
                not_unreimbursed.append(inv_id)
                continue
            if inv.get("batch_id") is not None:
                already_in.append(inv_id)
                continue

            budget_warning = self._check_budget(inv["date"][:7], inv["type"], 0)
            if budget_warning:
                warnings.append(f"{inv_id}: {budget_warning}")

            inv["batch_id"] = batch_id
            self.store.update(inv_id, {"batch_id": batch_id})
            batch["invoice_ids"].append(inv_id)
            added.append(inv_id)

        self.batch_store.update(batch_id, {"invoice_ids": batch["invoice_ids"]})

        return {
            "batch_id": batch_id,
            "added": added,
            "already_in": already_in,
            "not_found": not_found,
            "not_unreimbursed": not_unreimbursed,
            "warnings": warnings,
        }

    def update_batch_status(
        self,
        batch_id: str,
        new_status: str,
        remark: str = "",
    ) -> Dict[str, Any]:
        batch = self.batch_store.get_by_id(batch_id)
        if batch is None:
            raise ValueError(f"批次不存在: {batch_id}")
        if new_status not in self.BATCH_STATUS:
            raise ValueError(f"状态必须是: {', '.join(self.BATCH_STATUS)}")

        current_status = batch["status"]
        if new_status not in self.BATCH_STATUS_FLOW.get(current_status, []):
            raise ValueError(
                f"状态流转不合法: 从 {current_status} 不能直接转为 {new_status}。"
                f"允许的流转: {', '.join(self.BATCH_STATUS_FLOW.get(current_status, []))}"
            )

        batch["status"] = new_status
        log_entry = {
            "status": new_status,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "remark": remark or f"状态变更为 {new_status}",
        }
        batch["status_log"].append(log_entry)
        self.batch_store.update(batch_id, {"status": new_status, "status_log": batch["status_log"]})

        if new_status == "已打款":
            for inv_id in batch["invoice_ids"]:
                self.update_status(inv_id, "已报销")
        elif new_status == "已驳回":
            for inv_id in batch["invoice_ids"]:
                inv = self.get_by_id(inv_id)
                if inv:
                    inv["batch_id"] = None
                    self.store.update(inv_id, {"batch_id": None})
            batch["invoice_ids"] = []
            self.batch_store.update(batch_id, {"invoice_ids": []})

        return {"batch_id": batch_id, "old_status": current_status, "new_status": new_status}

    def list_batches(self) -> List[Dict[str, Any]]:
        return self.batch_store.load_all()

    def get_batch_by_id(self, batch_id: str) -> Optional[Dict[str, Any]]:
        return self.batch_store.get_by_id(batch_id)

    def get_batch_invoices(self, batch_id: str) -> List[Dict[str, Any]]:
        batch = self.batch_store.get_by_id(batch_id)
        if batch is None:
            raise ValueError(f"批次不存在: {batch_id}")
        result = []
        for inv_id in batch["invoice_ids"]:
            inv = self.get_by_id(inv_id)
            if inv:
                result.append(inv)
        return result

    def export_batch_csv(self, batch_id: str, output_path: str) -> str:
        batch = self.batch_store.get_by_id(batch_id)
        if batch is None:
            raise ValueError(f"批次不存在: {batch_id}")
        invoices = self.get_batch_invoices(batch_id)
        if not invoices:
            raise ValueError(f"批次 {batch_id} 没有发票记录")

        budget_map = {}
        for inv in invoices:
            ym = inv["date"][:7]
            inv_type = inv["type"]
            key = f"{ym}_{inv_type}"
            if key not in budget_map:
                budget = self.get_budget(ym, inv_type)
                used = self._get_used_amount(ym, inv_type)
                budget_map[key] = {
                    "budget": budget,
                    "used": used,
                    "over": budget is not None and used > budget,
                }

        fieldnames = [
            "batch_id", "batch_name", "applicant", "batch_status",
            "invoice_id", "title", "amount", "date", "type", "invoice_status",
            "budget", "used_amount", "budget_over", "audit_remark", "remark",
        ]
        headers = {
            "batch_id": "批次编号",
            "batch_name": "批次名称",
            "applicant": "申请人",
            "batch_status": "批次状态",
            "invoice_id": "发票编号",
            "title": "发票抬头",
            "amount": "金额(元)",
            "date": "开票日期",
            "type": "发票类型",
            "invoice_status": "发票状态",
            "budget": "月度预算",
            "used_amount": "月度已用",
            "budget_over": "预算超额",
            "audit_remark": "审核备注",
            "remark": "发票备注",
        }

        dir_name = os.path.dirname(output_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)

        audit_remark = ""
        for log in reversed(batch["status_log"]):
            if log["status"] in ["已审核", "已驳回"]:
                audit_remark = log["remark"]
                break

        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow(headers)
            for inv in invoices:
                key = f"{inv['date'][:7]}_{inv['type']}"
                binfo = budget_map.get(key, {})
                writer.writerow({
                    "batch_id": batch["id"],
                    "batch_name": batch["name"],
                    "applicant": batch["applicant"],
                    "batch_status": batch["status"],
                    "invoice_id": inv["id"],
                    "title": inv["title"],
                    "amount": f"{inv['amount']:.2f}",
                    "date": inv["date"],
                    "type": inv["type"],
                    "invoice_status": inv["status"],
                    "budget": f"{binfo.get('budget', ''):.2f}" if binfo.get("budget") else "未设置",
                    "used_amount": f"{binfo.get('used', 0):.2f}",
                    "budget_over": "是" if binfo.get("over") else "否",
                    "audit_remark": audit_remark,
                    "remark": inv.get("remark", ""),
                })
        return os.path.abspath(output_path)

    def set_budget(self, year_month: str, inv_type: str, amount: float) -> Dict[str, Any]:
        try:
            datetime.strptime(year_month, "%Y-%m")
        except ValueError:
            raise ValueError("月份格式必须是 YYYY-MM")
        if inv_type not in self.VALID_TYPES:
            raise ValueError(f"类型必须是: {', '.join(self.VALID_TYPES)}")
        if amount < 0:
            raise ValueError("预算金额不能为负")

        budgets = self.budget_store.load_all()
        for b in budgets:
            if b["year_month"] == year_month and b["type"] == inv_type:
                b["amount"] = round(float(amount), 2)
                b["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.budget_store.save_all(budgets)
                return b

        budget = {
            "id": self.budget_store.get_next_id("BGT"),
            "year_month": year_month,
            "type": inv_type,
            "amount": round(float(amount), 2),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.budget_store.append(budget)
        return budget

    def get_budget(self, year_month: str, inv_type: str) -> Optional[float]:
        budgets = self.budget_store.load_all()
        for b in budgets:
            if b["year_month"] == year_month and b["type"] == inv_type:
                return float(b["amount"])
        return None

    def list_budgets(self) -> List[Dict[str, Any]]:
        return self.budget_store.load_all()

    def check_batch_budget(self, batch_id: str) -> List[str]:
        batch = self.batch_store.get_by_id(batch_id)
        if batch is None:
            raise ValueError(f"批次不存在: {batch_id}")

        warnings = []
        monthly_type_totals = defaultdict(float)
        for inv_id in batch["invoice_ids"]:
            inv = self.get_by_id(inv_id)
            if inv:
                key = f"{inv['date'][:7]}_{inv['type']}"
                monthly_type_totals[key] += inv["amount"]

        for key, total in monthly_type_totals.items():
            ym, inv_type = key.split("_", 1)
            budget = self.get_budget(ym, inv_type)
            if budget is not None:
                used = self._get_used_amount(ym, inv_type)
                if used > budget:
                    warnings.append(
                        f"{ym} 月 {inv_type}: 预算 ¥{budget:.2f}, 已使用 ¥{used:.2f}, "
                        f"超额 ¥{used - budget:.2f}"
                    )
        return warnings

    @staticmethod
    def _is_garbled(text: str) -> bool:
        if not isinstance(text, str):
            return False
        if "\ufffd" in text:
            return True
        for ch in text:
            if 0xD800 <= ord(ch) <= 0xDFFF:
                return True
        if re.search(r"[ÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]", text):
            return True
        if re.search(r"^[\x00-\x7F]+$", text) is None and re.search(r"[\u4e00-\u9fff]", text) is None:
            if len(text) > 0 and re.search(r"[^\x00-\x7F\u4e00-\u9fff]", text):
                return True
        return False

    def repair_data(self, dry_run: bool = True) -> Dict[str, Any]:
        file_path = self.store.file_path
        if not os.path.exists(file_path):
            return {"error": f"文件不存在: {file_path}"}

        with open(file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()
            try:
                invoices = json.loads(raw_content)
            except json.JSONDecodeError as e:
                return {"error": f"JSON 解析失败: {e}"}

        if not isinstance(invoices, list):
            return {"error": "根节点必须是数组"}

        report = {
            "total_invoices": len(invoices),
            "fixed": 0,
            "issues": [],
            "dry_run": dry_run,
        }

        required_fields = ["id", "title", "amount", "date", "type", "status"]
        valid_types = set(self.VALID_TYPES)
        valid_status = set(self.VALID_STATUS)
        seen_ids = set()

        for idx, inv in enumerate(invoices):
            issues = []
            fixes = {}

            if not isinstance(inv, dict):
                issues.append(f"第 {idx} 项不是对象，已跳过")
                report["issues"].append({"index": idx, "issues": issues, "fixes": {}})
                continue

            inv_id = inv.get("id", f"缺失({idx})")

            for field in required_fields:
                if field not in inv or inv[field] is None or (isinstance(inv[field], str) and inv[field].strip() == ""):
                    issues.append(f"缺失字段: {field}")
                    if field == "id":
                        fixes[field] = self.store.get_next_id()
                    elif field == "title":
                        fixes[field] = "未知抬头"
                    elif field == "amount":
                        fixes[field] = 0.0
                    elif field == "date":
                        fixes[field] = "1970-01-01"
                    elif field == "type":
                        fixes[field] = "其他"
                    elif field == "status":
                        fixes[field] = "未报销"

            for field in ["title", "type", "status", "remark"]:
                val = inv.get(field, "")
                if isinstance(val, str) and self._is_garbled(val):
                    issues.append(f"字段 {field} 含乱码: {val!r}")
                    if field == "type":
                        fixes[field] = "其他"
                    elif field == "status":
                        fixes[field] = "未报销"
                    elif field == "title":
                        fixes[field] = "已修复_" + re.sub(r"[^\u4e00-\u9fffA-Za-z0-9\s]", "", val)[:20]

            amount = inv.get("amount")
            if amount is not None:
                try:
                    amt = float(amount)
                    if amt <= 0:
                        issues.append(f"非法金额: {amount}")
                        fixes["amount"] = 0.01
                    else:
                        fixes["amount"] = round(amt, 2)
                except (ValueError, TypeError):
                    issues.append(f"非法金额格式: {amount!r}")
                    fixes["amount"] = 0.01

            date_val = inv.get("date")
            if date_val is not None and isinstance(date_val, str) and date_val.strip() != "":
                try:
                    datetime.strptime(date_val, "%Y-%m-%d")
                except ValueError:
                    issues.append(f"非法日期格式: {date_val!r}")
                    m = re.search(r"(\d{4})[-/]?(\d{1,2})[-/]?(\d{1,2})", date_val)
                    if m:
                        fixes["date"] = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                    else:
                        fixes["date"] = "1970-01-01"

            type_val = inv.get("type")
            if type_val is not None and type_val not in valid_types:
                issues.append(f"非法类型: {type_val!r}")
                fixes["type"] = "其他"

            status_val = inv.get("status")
            if status_val is not None and status_val not in valid_status:
                issues.append(f"非法状态: {status_val!r}")
                if status_val == "报销中":
                    fixes["status"] = "未报销"
                elif status_val == "已支付":
                    fixes["status"] = "已报销"
                else:
                    fixes["status"] = "未报销"

            current_id = inv.get("id")
            if current_id in seen_ids and current_id is not None:
                issues.append(f"重复ID: {current_id}")
                fixes["id"] = self.store.get_next_id()
            seen_ids.add(fixes.get("id", current_id))

            if issues:
                report["issues"].append({
                    "index": idx,
                    "invoice_id": inv_id,
                    "issues": issues,
                    "fixes": fixes,
                })
                if fixes:
                    report["fixed"] += 1
                    if not dry_run:
                        for k, v in fixes.items():
                            inv[k] = v

        if not dry_run and report["fixed"] > 0:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(invoices, f, ensure_ascii=False, indent=2)

        return report
