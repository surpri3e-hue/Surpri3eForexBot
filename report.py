from database import get_statistics
from users import get_users_count

def create_report():
    stats = get_statistics()
    users = get_users_count()

    return f"""
📊 **گزارش عملکرد**

👥 **کاربران:** {users}
📈 **کل معاملات:** {stats['total']}
✅ **برنده:** {stats['wins']}
❌ **بازنده:** {stats['losses']}
🎯 **نرخ موفقیت:** {stats['winrate']}%
💰 **فاکتور سود:** {stats['profit_factor']}

**وضعیت:** 🟢 آنلاین
"""
