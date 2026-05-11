"""
保险数据库查询模块
基于80份PDF建议书生成的数据库
"""
import json
import os
import sys
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _get_db_path():
    """获取数据库路径"""
    if getattr(sys, 'frozen', False):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    candidates = [
        os.path.join(base_dir, 'data', 'insurance_db_full.json'),
        os.path.join(base_dir, 'insurance_db_full.json'),
    ]
    for p in candidates:
        if os.path.exists(p):
            logger.info("使用数据库: %s", p)
            return p

    logger.error("数据库文件不存在")
    return None

DB_PATH = _get_db_path()
_db_cache = None

_DB_SCHEMA = {
    "type": "object",
    "required": ["M", "F", "meta"],
    "properties": {
        "M": {"type": "object"},
        "F": {"type": "object"},
        "meta": {
            "type": "object",
            "properties": {
                "source_count": {"type": "integer"},
                "premiums": {"type": "array"},
                "payments": {"type": "array"},
                "max_age_male": {"type": "integer"},
                "max_age_female": {"type": "integer"},
            }
        }
    }
}


def _validate_db_schema(data: dict) -> bool:
    try:
        if not isinstance(data, dict):
            logger.error("数据库根类型应为 object，实际为 %s", type(data).__name__)
            return False
        for key in ['M', 'F', 'meta']:
            if key not in data:
                logger.error("数据库缺少必需字段: %s", key)
                return False
            if not isinstance(data[key], dict) and key != 'meta':
                logger.error("字段 %s 应为 object，实际为 %s", key, type(data[key]).__name__)
                return False
        meta = data.get('meta', {})
        for field in ['source_count', 'premiums', 'payments']:
            if field not in meta:
                logger.warning("meta 缺少建议字段: %s", field)
        logger.info("数据库 Schema 验证通过")
        return True
    except Exception as e:
        logger.error("数据库 Schema 验证时发生异常: %s", e)
        return False


def load_db() -> Dict:
    global _db_cache
    if _db_cache is not None:
        return _db_cache

    db_path = DB_PATH
    if not db_path or not os.path.exists(db_path):
        logger.error("数据库文件不存在: %s", DB_PATH)
        return None

    try:
        with open(db_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not _validate_db_schema(data):
            logger.warning("数据库 Schema 验证失败，继续使用")
        _db_cache = data
        logger.info("数据库加载成功: %s (%d 条记录)", db_path, len(data.get('M', {})))
        return _db_cache
    except json.JSONDecodeError as e:
        logger.error("数据库 JSON 解析失败: %s, error=%s", db_path, e)
        return None
    except Exception as e:
        logger.error("数据库加载失败: %s, error=%s", db_path, e)
        return None


def clear_db_cache():
    global _db_cache
    _db_cache = None
    logger.info("数据库缓存已清除")


def get_available_ages(gender: str) -> List[int]:
    db = load_db()
    if not db or gender not in db:
        return []
    ages = set()
    for payment in db[gender]:
        for key in db[gender][payment]:
            try:
                age = int(key.split('_')[0])
                ages.add(age)
            except (ValueError, IndexError):
                logger.warning("无法解析年龄 key: %s", key)
    return sorted(ages)


def get_available_premiums(gender: str, payment: int) -> List[int]:
    db = load_db()
    payment_key = str(payment)
    if not db or gender not in db or payment_key not in db[gender]:
        return []
    premiums = set()
    for key in db[gender][payment_key]:
        try:
            parts = key.split('_')
            premium = int(parts[2].replace('W', '')) * 10000
            premiums.add(premium)
        except (ValueError, IndexError):
            logger.warning("无法解析保费 key: %s", key)
    return sorted(premiums)


def get_available_payments(gender: str) -> List[int]:
    db = load_db()
    if not db or gender not in db:
        return []
    return sorted([int(p) for p in db[gender].keys()])


def get_data(gender: str, payment: int, age: int, premium: int) -> Optional[List[Dict]]:
    db = load_db()
    if not db or gender not in db:
        return None

    payment_key = str(payment)
    if payment_key not in db[gender]:
        return None

    key = f"{age}_{gender}_{premium//10000}W_{payment}N"
    record = db[gender][payment_key].get(key)
    if record:
        return record['data']

    premiums = get_available_premiums(gender, payment)
    if not premiums:
        for p_key in db[gender]:
            if db[gender][p_key]:
                sample_key = list(db[gender][p_key].keys())[0]
                sample = db[gender][p_key][sample_key]
                base_premium = sample['premium']
                target_key = f"{age}_{gender}_{base_premium//10000}W_{p_key}N"
                if target_key in db[gender][p_key]:
                    record = db[gender][p_key][target_key]
                    ratio = premium / base_premium
                    return _scale_data(record['data'], ratio)
                break
        return None

    nearest = min(premiums, key=lambda x: abs(x - premium))
    key = f"{age}_{gender}_{nearest//10000}W_{payment}N"
    record = db[gender][payment_key].get(key)
    if record:
        ratio = premium / nearest
        return _scale_data(record['data'], ratio)

    for age_offset in range(1, 5):
        for delta in [-age_offset, age_offset]:
            target_age = age + delta
            key = f"{target_age}_{gender}_{nearest//10000}W_{payment}N"
            if key in db[gender][payment_key]:
                record = db[gender][payment_key][key]
                ratio = premium / nearest
                scaled = _scale_data(record['data'], ratio)
                for row in scaled:
                    row['age'] = age + (row.get('year', 0) - 1)
                return scaled

    return None


def _scale_data(data: List[Dict], ratio: float) -> List[Dict]:
    scaled_data = []
    for row in data:
        new_row = row.copy()
        for k in ['accum_premium', 'cash_value', 'demo_survival',
                  'current_dividend', 'accum_dividend', 'death_benefit']:
            if k in new_row and new_row[k]:
                new_row[k] = round(new_row[k] * ratio)
        scaled_data.append(new_row)
    return scaled_data


def interpolate_age_data(age: int, gender: str, premium: int, dividend_rate: float = 1.0) -> Optional[List[Dict]]:
    db = load_db()
    if not db:
        return None
    payments = get_available_payments(gender)
    if not payments:
        return None
    payment = 8 if 8 in payments else payments[0]
    data = get_data(gender, payment, age, premium)
    if not data:
        for p in payments:
            if p != payment:
                data = get_data(gender, p, age, premium)
                if data:
                    payment = p
                    break
    if not data:
        return None
    if dividend_rate != 1.0:
        for row in data:
            if 'accum_dividend' in row:
                row['accum_dividend'] = round(row['accum_dividend'] * dividend_rate)
    return data


def get_data_summary() -> Dict:
    db = load_db()
    if not db:
        return {}
    meta = db.get('meta', {})
    summary = {
        'source_count': meta.get('source_count', 0),
        'premiums': [p // 10000 for p in meta.get('premiums', [])],
        'payments': meta.get('payments', []),
        'max_age_male': meta.get('max_age_male', 62),
        'max_age_female': meta.get('max_age_female', 65),
        'male_count': sum(len(db['M'].get(p, {})) for p in db.get('M', {})),
        'female_count': sum(len(db['F'].get(p, {})) for p in db.get('F', {})),
    }
    return summary


def get_raw_data(age: int, gender: str, premium: int, payment_years: int) -> Optional[List[Dict]]:
    return get_data(gender, payment_years, age, premium)


if __name__ == '__main__':
    print("数据库查询模块测试")
    print("=" * 40)
    summary = get_data_summary()
    print(f"数据来源: {summary['source_count']}份PDF")
    print(f"保费档次: {summary['premiums']}万")
    print(f"缴费年限: {summary['payments']}")
    print(f"男性最大年龄: {summary['max_age_male']}")
    print(f"女性最大年龄: {summary['max_age_female']}")
    print()
    print("男性可用年龄:", get_available_ages('M'))
    print("女性可用年龄:", get_available_ages('F'))