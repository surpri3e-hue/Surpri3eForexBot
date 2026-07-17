# strategy_registry.py
import importlib
import os
import pkgutil
import logging

logger = logging.getLogger(__name__)

STRATEGIES_PACKAGE = "strategies"

# ============================================================
# 📁 strategy_registry.py
# 📌 وظیفه: مدیریت و اجرای استراتژی‌های مختلف
# 📅 2026-07-17 - معماری plugin-محور
#
# این فایل مثل یک «دفترچه راهنما» عمل میکنه که به ربات میگه
# هر استراتژی کجاست و چطور اجرا بشه
# ============================================================


def discover_strategies():
    """
    همه‌ی ماژول‌های معتبر تو پوشه‌ی strategies/ رو پیدا می‌کنه.
    خروجی: dict {strategy_id: module}
    فقط ماژول‌هایی که STRATEGY_INFO و analyze() دارن معتبر شناخته می‌شن؛
    اگه ماژولی خطا بده یا ناقص باشه، لاگ می‌شه و نادیده گرفته می‌شه
    (یه استراتژی خراب نباید کل ربات رو بخوابونه).
    """
    strategies = {}

    try:
        package = importlib.import_module(STRATEGIES_PACKAGE)
    except ImportError:
        logger.warning(f"پوشه‌ی {STRATEGIES_PACKAGE} پیدا نشد یا __init__.py نداره")
        return strategies

    package_path = os.path.dirname(package.__file__)

    for _, module_name, _ in pkgutil.iter_modules([package_path]):
        full_name = f"{STRATEGIES_PACKAGE}.{module_name}"
        try:
            module = importlib.import_module(full_name)
        except Exception as e:
            logger.error(f"❌ استراتژی {module_name} لود نشد: {e}")
            continue

        if not hasattr(module, "STRATEGY_INFO") or not hasattr(module, "analyze"):
            logger.warning(f"⚠️ {module_name} فرمت استاندارد استراتژی رو نداره (STRATEGY_INFO یا analyze غایبه) - نادیده گرفته شد")
            continue

        strategy_id = module.STRATEGY_INFO.get("id")
        if not strategy_id:
            logger.warning(f"⚠️ {module_name} فیلد 'id' رو تو STRATEGY_INFO نداره - نادیده گرفته شد")
            continue

        strategies[strategy_id] = module

    return strategies


# ===== کش سراسری - فقط یک‌بار موقع استارت ربات اسکن می‌شه =====
_STRATEGIES_CACHE = None


def get_all_strategies():
    """لیست کامل استراتژی‌های معتبر رو برمی‌گردونه (با کش)."""
    global _STRATEGIES_CACHE
    if _STRATEGIES_CACHE is None:
        _STRATEGIES_CACHE = discover_strategies()
    return _STRATEGIES_CACHE


def get_strategy(strategy_id):
    """یک استراتژی خاص رو با شناسه‌اش برمی‌گردونه، یا None اگه پیدا نشه."""
    return get_all_strategies().get(strategy_id)


def run_strategy(strategy_id, df):
    """
    تحلیل رو با استراتژی مشخص‌شده اجرا می‌کنه.
    خروجی: (signal, analysis) یا (None, None) اگه استراتژی پیدا نشه یا خطا بده.
    """
    module = get_strategy(strategy_id)
    if module is None:
        logger.warning(f"استراتژی '{strategy_id}' پیدا نشد")
        return None, None

    try:
        return module.analyze(df)
    except Exception as e:
        logger.exception(f"خطا در اجرای استراتژی '{strategy_id}': {e}")
        return None, None
