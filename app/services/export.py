"""Report export service generating CSV and Excel files."""

import csv
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Optional, Tuple
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.repositories.sale_repo import SaleRepository
from app.database.repositories.order_repo import OrderRepository
from app.database.repositories.task_repo import TaskRepository
from app.utils.tz import now_tz, today_tz


class ExportService:
    """Service producing structured CSV and Excel report exports."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sale_repo = SaleRepository(session)
        self.order_repo = OrderRepository(session)
        self.task_repo = TaskRepository(session)
        self.export_dir: Path = settings.EXPORTS_DIR
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def _get_date_range(self, period: str) -> Tuple[date, date]:
        today = today_tz()
        if period == "weekly":
            start = today - timedelta(days=7)
            return start, today
        elif period == "monthly":
            start = today.replace(day=1)
            return start, today
        else:  # daily
            return today, today

    async def generate_csv_report(self, period: str = "daily") -> Path:
        """Generate a CSV export of sales and metrics for the given period."""
        start_date, end_date = self._get_date_range(period)
        sales = await self.sale_repo.list_sales(start_date=start_date, end_date=end_date, limit=5000)

        filename = f"business_report_{period}_{now_tz().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path = self.export_dir / filename

        with open(file_path, mode="w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["Sale ID", "Date", "Seller", "Product", "Quantity", "Unit Price", "Cost", "Revenue", "Gross Profit", "Notes"])

            for s in sales:
                seller_name = s.seller.full_name if s.seller else f"User {s.seller_id}"
                product_name = s.product.name if s.product else f"Prod {s.product_id}"
                writer.writerow([
                    s.id,
                    s.sale_date.strftime("%Y-%m-%d"),
                    seller_name,
                    product_name,
                    s.quantity,
                    f"{float(s.unit_price):.2f}",
                    f"{float(s.cost_price):.2f}",
                    f"{float(s.revenue):.2f}",
                    f"{float(s.gross_profit):.2f}",
                    s.notes or "",
                ])

        return file_path

    async def generate_excel_report(self, period: str = "monthly") -> Path:
        """Generate a multi-sheet Excel workbook with summary, sales, top rankings, and open tasks."""
        start_date, end_date = self._get_date_range(period)

        # 1. Sales data
        sales = await self.sale_repo.list_sales(start_date=start_date, end_date=end_date, limit=5000)
        sales_records = []
        for s in sales:
            sales_records.append({
                "Sale ID": s.id,
                "Date": s.sale_date.strftime("%Y-%m-%d"),
                "Seller": s.seller.full_name if s.seller else f"User {s.seller_id}",
                "Product": s.product.name if s.product else f"Prod {s.product_id}",
                "Quantity": s.quantity,
                "Unit Price": float(s.unit_price),
                "Cost Price": float(s.cost_price),
                "Revenue": float(s.revenue),
                "Gross Profit": float(s.gross_profit),
            })
        sales_df = pd.DataFrame(sales_records) if sales_records else pd.DataFrame(columns=["Sale ID", "Date", "Seller", "Product", "Quantity", "Unit Price", "Cost Price", "Revenue", "Gross Profit"])

        # 2. Summary
        summary = await self.sale_repo.get_summary(start_date=start_date, end_date=end_date)
        summary_records = [{
            "Report Period": f"{start_date} to {end_date}",
            "Total Revenue ($)": float(summary.get("revenue", 0.0)),
            "Total Cost ($)": float(summary.get("cost", 0.0)),
            "Gross Profit ($)": float(summary.get("gross_profit", 0.0)),
            "Total Units Sold": summary.get("units_sold", 0),
            "Total Sales Count": summary.get("sales_count", 0),
        }]
        summary_df = pd.DataFrame(summary_records)

        # 3. Top Products
        top_prods = await self.sale_repo.get_top_products(start_date=start_date, end_date=end_date, limit=10)
        top_prods_df = pd.DataFrame([
            {"Product": name, "Units Sold": units, "Revenue ($)": float(rev)}
            for name, units, rev in top_prods
        ]) if top_prods else pd.DataFrame(columns=["Product", "Units Sold", "Revenue ($)"])

        # 4. Top Sellers
        top_sellers = await self.sale_repo.get_top_sellers(start_date=start_date, end_date=end_date, limit=10)
        top_sellers_df = pd.DataFrame([
            {"Seller": name, "Revenue ($)": float(rev), "Units Sold": units}
            for name, rev, units in top_sellers
        ]) if top_sellers else pd.DataFrame(columns=["Seller", "Revenue ($)", "Units Sold"])

        # 5. Open Tasks
        tasks = await self.task_repo.list_tasks(limit=100)
        tasks_records = []
        for t in tasks:
            tasks_records.append({
                "Task ID": t.id,
                "Title": t.title,
                "Priority": t.priority.value,
                "Status": t.status.value,
                "Due Date": t.due_date.strftime("%Y-%m-%d %H:%M") if t.due_date else "None",
            })
        tasks_df = pd.DataFrame(tasks_records) if tasks_records else pd.DataFrame(columns=["Task ID", "Title", "Priority", "Status", "Due Date"])

        # Write Excel file
        filename = f"business_executive_report_{period}_{now_tz().strftime('%Y%m%d_%H%M%S')}.xlsx"
        file_path = self.export_dir / filename

        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            summary_df.to_excel(writer, sheet_name="Overview", index=False)
            sales_df.to_excel(writer, sheet_name="Sales Breakdown", index=False)
            top_prods_df.to_excel(writer, sheet_name="Top Products", index=False)
            top_sellers_df.to_excel(writer, sheet_name="Top Sellers", index=False)
            tasks_df.to_excel(writer, sheet_name="Outstanding Tasks", index=False)

        return file_path
