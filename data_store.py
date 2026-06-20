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
            try:
                id_num = int(inv["id"].split("-")[1])
                if id_num > max_id:
                    max_id = id_num
            except (ValueError, IndexError):
                continue
        return f"INV-{max_id + 1:04d}"


class GenericJsonStore:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def load_all(self) -> List[Dict[str, Any]]:
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_all(self, items: List[Dict[str, Any]]) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

    def append(self, item: Dict[str, Any]) -> None:
        items = self.load_all()
        items.append(item)
        self.save_all(items)

    def update(self, item_id: str, updates: Dict[str, Any]) -> bool:
        items = self.load_all()
        for idx, it in enumerate(items):
            if it["id"] == item_id:
                items[idx].update(updates)
                self.save_all(items)
                return True
        return False

    def delete(self, item_id: str) -> bool:
        items = self.load_all()
        new_items = [it for it in items if it["id"] != item_id]
        if len(new_items) == len(items):
            return False
        self.save_all(new_items)
        return True

    def get_by_id(self, item_id: str) -> Any:
        for it in self.load_all():
            if it["id"] == item_id:
                return it
        return None

    def get_next_id(self, prefix: str) -> str:
        items = self.load_all()
        if not items:
            return f"{prefix}-0001"
        max_id = 0
        for it in items:
            try:
                id_num = int(it["id"].split("-")[1])
                if id_num > max_id:
                    max_id = id_num
            except (ValueError, IndexError):
                continue
        return f"{prefix}-{max_id + 1:04d}"
