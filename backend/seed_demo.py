"""
AI CFO — Demo Seed Script
Creates the "Luna Bakery" demo workspace with realistic financial data.
Run: python seed_demo.py
"""
import asyncio
import uuid
from datetime import datetime, timedelta
import random

from database import engine, Base, AsyncSessionLocal
from models import (
    Workspace, User, Transaction, Budget, Alert, Goal,
    IndustryBenchmark, AlertRule,
    TransactionType, AlertSeverity, UserRole, GoalStatus,
)

# ── Luna Bakery Demo Data ─────────────────────────────────────────

CATEGORIES_INCOME = ["Product Sales", "Catering", "Online Orders", "Wholesale"]
CATEGORIES_EXPENSE = [
    "Ingredients", "Rent", "Salaries", "Utilities",
    "Marketing", "Equipment", "Insurance", "Supplies",
]
VENDORS = {
    "Ingredients": ["Flour Co.", "Sugar Supply", "Dairy Fresh", "Costal Farms"],
    "Rent": ["City Property Mgmt"],
    "Salaries": ["Payroll"],
    "Utilities": ["City Electric", "Water Co."],
    "Marketing": ["Meta Ads", "Google Ads", "Local Print"],
    "Equipment": ["Baker's Supply", "Restaurant Depot"],
    "Insurance": ["SafeGuard Insurance"],
    "Supplies": ["PackCo", "CleanPro"],
}


async def seed():
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # ── Workspace ─────────────────────────────────────────────
        ws = Workspace(
            name="Luna Bakery & Café",
            industry="food_and_beverage",
            currency="USD",
            is_demo=True,
        )
        db.add(ws)
        await db.flush()

        # ── Owner user ────────────────────────────────────────────
        owner = User(
            workspace_id=ws.id,
            email="luna@lunabakery.com",
            full_name="Luna Martinez",
            role=UserRole.owner,
        )
        db.add(owner)
        await db.flush()

        # ── 12 months of transactions ─────────────────────────────
        now = datetime.utcnow()
        transactions = []

        for month_offset in range(12):
            month_date = now - timedelta(days=month_offset * 30)

            # Income: 15-25 transactions per month
            for _ in range(random.randint(15, 25)):
                cat = random.choice(CATEGORIES_INCOME)
                base = {
                    "Product Sales": random.uniform(200, 800),
                    "Catering": random.uniform(500, 2500),
                    "Online Orders": random.uniform(50, 300),
                    "Wholesale": random.uniform(1000, 3000),
                }[cat]
                # Slight growth trend
                amount = base * (1 + month_offset * 0.01)

                txn = Transaction(
                    workspace_id=ws.id,
                    user_id=owner.id,
                    date=month_date - timedelta(days=random.randint(0, 28)),
                    description=f"{cat} - Day {random.randint(1, 28)}",
                    amount=round(amount, 2),
                    category=cat,
                    type=TransactionType.income,
                    account="Business Checking",
                    source="seed",
                )
                transactions.append(txn)

            # Expenses: 10-20 transactions per month
            for _ in range(random.randint(10, 20)):
                cat = random.choice(CATEGORIES_EXPENSE)
                base = {
                    "Ingredients": random.uniform(200, 1200),
                    "Rent": 3500.0,
                    "Salaries": random.uniform(2000, 4500),
                    "Utilities": random.uniform(150, 400),
                    "Marketing": random.uniform(100, 800),
                    "Equipment": random.uniform(50, 500),
                    "Insurance": 450.0,
                    "Supplies": random.uniform(30, 200),
                }[cat]

                vendor_list = VENDORS.get(cat, ["Generic Vendor"])
                vendor = random.choice(vendor_list)

                txn = Transaction(
                    workspace_id=ws.id,
                    user_id=owner.id,
                    date=month_date - timedelta(days=random.randint(0, 28)),
                    description=f"{cat} - {vendor}",
                    amount=round(base, 2),
                    category=cat,
                    type=TransactionType.expense,
                    account="Business Checking",
                    vendor=vendor,
                    source="seed",
                )
                transactions.append(txn)

        db.add_all(transactions)

        # ── Budgets ───────────────────────────────────────────────
        current_month = now.strftime("%Y-%m")
        for cat, limit in [
            ("Ingredients", 8000), ("Rent", 3600), ("Salaries", 15000),
            ("Utilities", 600), ("Marketing", 2000), ("Equipment", 1500),
            ("Insurance", 500), ("Supplies", 800),
        ]:
            db.add(Budget(
                workspace_id=ws.id,
                user_id=owner.id,
                category=cat,
                monthly_limit=limit,
                alert_threshold=0.8,
                month=current_month,
            ))

        # ── Goals ─────────────────────────────────────────────────
        db.add(Goal(
            workspace_id=ws.id,
            user_id=owner.id,
            title="Reach $50K Monthly Revenue",
            target_value=50000,
            current_value=38500,
            metric_type="revenue",
            deadline=now + timedelta(days=90),
            status=GoalStatus.active,
        ))
        db.add(Goal(
            workspace_id=ws.id,
            user_id=owner.id,
            title="Reduce Food Cost to 28%",
            target_value=28,
            current_value=32,
            metric_type="expense_reduction",
            deadline=now + timedelta(days=180),
            status=GoalStatus.active,
        ))

        # ── Alerts ────────────────────────────────────────────────
        db.add(Alert(
            workspace_id=ws.id,
            user_id=owner.id,
            title="Ingredients budget at 85%",
            message="You've spent $6,800 of your $8,000 ingredients budget this month.",
            severity=AlertSeverity.warning,
            category="Ingredients",
        ))
        db.add(Alert(
            workspace_id=ws.id,
            user_id=owner.id,
            title="Revenue milestone reached",
            message="Congratulations! Monthly revenue exceeded $35,000 for the first time.",
            severity=AlertSeverity.info,
            category="Product Sales",
        ))
        db.add(Alert(
            workspace_id=ws.id,
            user_id=owner.id,
            title="Unusual equipment expense",
            message="A $2,450 equipment purchase was flagged as unusual — 3.2x your category average.",
            severity=AlertSeverity.critical,
            category="Equipment",
        ))

        # ── Alert Rules ───────────────────────────────────────────
        db.add(AlertRule(
            workspace_id=ws.id,
            rule_type="overspend",
            threshold_value=0.8,
            is_enabled=True,
        ))

        # ── Industry Benchmarks ───────────────────────────────────
        for metric, value in [
            ("profit_margin", 12.5),
            ("expense_ratio", 82.0),
            ("revenue_growth", 8.5),
        ]:
            db.add(IndustryBenchmark(
                industry="food_and_beverage",
                metric_name=metric,
                metric_value=value,
                unit="percentage",
                source="Industry Average 2025",
                year=2025,
            ))

        await db.commit()
        print(f"✅ Seeded Luna Bakery workspace: {ws.id}")
        print(f"   Owner: {owner.email}")
        print(f"   Transactions: {len(transactions)}")
        print(f"   Budgets: 8 | Goals: 2 | Alerts: 3")


if __name__ == "__main__":
    asyncio.run(seed())
