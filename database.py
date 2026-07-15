# ============ آمار هفتگی و ماهانه ============
def get_weekly_stats():
    """دریافت وین‌ریت هفته جاری"""
    conn = connect()
    cursor = conn.cursor()
    
    # شروع هفته (دوشنبه)
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_week_str = start_of_week.strftime('%Y-%m-%d')
    
    cursor.execute(
        "SELECT result FROM trades WHERE date(time) >= ?",
        (start_of_week_str,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    total = len(rows)
    wins = sum(1 for r in rows if r[0] == "TP")
    winrate = round((wins / total) * 100, 2) if total > 0 else 0
    return {'total': total, 'wins': wins, 'winrate': winrate}

def get_monthly_stats():
    """دریافت وین‌ریت ماه جاری"""
    conn = connect()
    cursor = conn.cursor()
    
    # شروع ماه
    today = datetime.now()
    start_of_month = today.replace(day=1)
    start_of_month_str = start_of_month.strftime('%Y-%m-%d')
    
    cursor.execute(
        "SELECT result FROM trades WHERE date(time) >= ?",
        (start_of_month_str,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    total = len(rows)
    wins = sum(1 for r in rows if r[0] == "TP")
    winrate = round((wins / total) * 100, 2) if total > 0 else 0
    return {'total': total, 'wins': wins, 'winrate': winrate}
