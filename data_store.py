import json
import os
from typing import List, Dict, Any


class DataStore:
    def __init__(self, file_path: str = "invoices.json"):
        self.file_path = file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def load_all(self) -> List[Dict[str, Any]]:
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_all(self, invoices: List[Dict[str, Any]]) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(invoices, f, ensure_ascii=False, indent=2)

    def append(self, invoice: Dict[str, Any]) -> None:
        invoices = self.load_all()
        invoices.append(invoice)
        self.save_all(invoices)

    def update(self, invoice_id: str, updates: Dict[str, Any]) -> bool:
        invoices = self.load_all()
        for idx, inv in enumerate(invoices):
            if inv["id"] == invoice_id:
                invoices[idx].update(updates)
                self.save_all(invoices)
                return True
        return False

    def get_next_id(self) -> str:
        invoices = self.load_all()
        if not invoices:
            return "INV-0001"
        max_id = 0
        for inv in invoices:
            id_num = int(inv["id"].split("-")[1])
            if id_num > max_id:
                max_id = id_num
        return f"INV-{max_id + 1:04d}"
