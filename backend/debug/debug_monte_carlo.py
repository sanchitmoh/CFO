"""Verify: simulate what the FIXED baseline returns for the active workspace."""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(__file__))

WS_ID = "b61bbd4d-37ed-4e73-a059-085e3e478827"

async def main():
    from database import AsyncSessionLocal
    from sqlalchemy import text

    async with AsyncSessionLocal() as session:
        # Reproduce the new median-based baseline logic
        r = await session.execute(text(f"""
            SELECT to_char(date, 'YYYY-MM') as month,
                   type,
                   sum(amount) as total
            FROM transactions
            WHERE workspace_id = '{WS_ID}'
            GROUP BY to_char(date, 'YYYY-MM'), type
            ORDER BY month
        """))
        rows = list(r)
        month_data = {}
        for row in rows:
            m, t, total = row[0], row[1], float(row[2] or 0)
            if m not in month_data:
                month_data[m] = {"income": 0.0, "expense": 0.0}
            month_data[m][t] = total

        monthly_income = [month_data[m].get("income", 0) for m in sorted(month_data.keys())]
        monthly_expense = [month_data[m].get("expense", 0) for m in sorted(month_data.keys())]

        def median(vals):
            s = sorted(vals)
            n = len(s)
            if n == 0: return 0.0
            mid = n // 2
            return (s[mid] + s[mid - 1]) / 2 if n % 2 == 0 else s[mid]

        med_inc = median(monthly_income)
        med_exp = median(monthly_expense)

        recent_inc = monthly_income[-3:]
        recent_exp = monthly_expense[-3:]
        recent_net = sum(recent_inc) - sum(recent_exp)
        starting_cash = max(recent_net, 0)

        print("=== NEW MEDIAN BASELINE ===")
        print(f"Months of data: {len(monthly_income)}")
        print(f"Median income/mo:  {med_inc:>14,.0f}")
        print(f"Median expense/mo: {med_exp:>14,.0f}")
        print(f"Monthly net:       {med_inc - med_exp:>14,.0f}")
        print(f"Recent 3mo net:    {recent_net:>14,.0f}")
        print(f"Starting cash:     {starting_cash:>14,.0f}")

        # Compare with old MEAN baseline
        n_months = len(monthly_income)
        mean_inc = sum(monthly_income) / n_months
        mean_exp = sum(monthly_expense) / n_months
        print(f"\n=== OLD MEAN BASELINE (for comparison) ===")
        print(f"Mean income/mo:    {mean_inc:>14,.0f}")
        print(f"Mean expense/mo:   {mean_exp:>14,.0f}")
        print(f"Mean monthly net:  {mean_inc - mean_exp:>14,.0f}")

        print(f"\n=== IMPROVEMENT ===")
        print(f"Median filters out the outlier ₹5cr month:")
        print(f"  Old mean income:   {mean_inc:>12,.0f}  (inflated by funding event)")
        print(f"  New median income: {med_inc:>12,.0f}  (reflects typical month)")
        print(f"  Monthly burn is {'still negative' if med_inc < med_exp else 'now positive'}")

if __name__ == "__main__":
    asyncio.run(main())
