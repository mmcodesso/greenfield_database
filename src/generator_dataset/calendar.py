from __future__ import annotations

import pandas as pd


def build_calendar(start_date: str, end_date: str) -> pd.DataFrame:
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    calendar = pd.DataFrame({"Date": dates})
    calendar["FiscalYear"] = calendar["Date"].dt.year
    calendar["FiscalPeriod"] = calendar["Date"].dt.month
    calendar["Quarter"] = calendar["Date"].dt.quarter
    calendar["MonthName"] = calendar["Date"].dt.month_name()
    calendar["Weekday"] = calendar["Date"].dt.day_name()
    calendar["IsWeekend"] = calendar["Weekday"].isin(["Saturday", "Sunday"]).astype(int)
    calendar["Date"] = calendar["Date"].dt.strftime("%Y-%m-%d")
    return calendar
