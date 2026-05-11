"""
PDF解析模块（保留作为辅助解析）
主要解析逻辑已移至 controllers/pdf_controller.py
"""
import re
import logging
from typing import List, Dict, Optional, Tuple, Any

logger = logging.getLogger(__name__)


def num(s: Any) -> Optional[float]:
    """安全转换为浮点数"""
    if s is None or s == '' or s == '--':
        return None
    try:
        return float(str(s).replace(',', '').replace('%', '').strip())
    except (ValueError, TypeError):
        return None


def extract_customer_name(text: str) -> Optional[str]:
    """从PDF文本中提取客户姓名"""
    patterns = [
        r'姓\s*名[：:]\s*([^\s\d]{2,10})',
        r'客户[：:]\s*([^\s\d]{2,10})',
        r'被保人[：:]\s*([^\s\d]{2,10})',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1).strip()
    return None


def detect_age_column(header_text: str) -> Optional[int]:
    """检测年龄列的位置"""
    age_patterns = ['年龄', '被保险人年龄', '被保人年龄']
    for i, pat in enumerate(age_patterns):
        if pat in header_text:
            return i
    return None


def validate_age_consistency(data: List[Dict]) -> bool:
    """验证年龄数据一致性"""
    if not data or len(data) < 2:
        return True
    for i in range(1, len(data)):
        if data[i].get('age', 0) != data[i-1].get('age', 0) + 1:
            logger.warning(f"年龄跳跃: 第{i}行 age={data[i].get('age')} 第{i+1}行 age={data[i-1].get('age')}")
            return False
    return True


def extract_tables_from_pdf(pdf_path: str) -> Tuple[List[Dict], str]:
    """从PDF提取表格数据（兼容旧接口）"""
    from controllers.pdf_controller import extract_pdf_text_and_tables, parse_all_tables_to_records, detect_dividend_type
    pdf_text, all_tables = extract_pdf_text_and_tables(pdf_path)
    dtype = detect_dividend_type(all_tables)
    records = parse_all_tables_to_records(all_tables, dtype)
    return records, pdf_text


def detect_table_type(text: str) -> str:
    """检测表格类型"""
    if '交清增额' in text:
        return '交清增额'
    elif '红利' in text or '累积生息' in text:
        return '累积生息'
    return '未知'


def smart_column_mapping(header: List[str], table_type: str) -> Dict[str, int]:
    """智能列映射"""
    mapping = {}
    header_text = ' '.join([str(h).replace('\n', '') for h in header if h])
    for i, col in enumerate(header):
        col_text = str(col).replace('\n', '') if col else ''
        if '保单年度' in col_text or '年度' in col_text:
            mapping['year'] = i
        elif '年龄' in col_text:
            mapping['age'] = i
        elif '期交保费' in col_text or '年交保费' in col_text:
            mapping['premium'] = i
        elif '累计保费' in col_text or '总保费' in col_text:
            mapping['total_premium'] = i
        elif '身故总利益' in col_text or '身故保险金' in col_text:
            mapping['death'] = i
        elif '生存总利益' in col_text and '增长率' not in col_text:
            mapping['survival'] = i
        elif '增长率' in col_text:
            mapping['rate'] = i
    return mapping


def parse_table_rows(table: List[List], mapping: Dict[str, int], table_type: str) -> List[Dict]:
    """解析表格行数据"""
    records = []
    for row in table:
        if not row or not row[0] or not str(row[0]).strip().isdigit():
            continue
        try:
            year = int(str(row[mapping.get('year', 0)]).strip()) if mapping.get('year') is not None and row[mapping.get('year', 0)] else None
            if year is None:
                continue
            record = {'year': year}
            for key, col in mapping.items():
                if key != 'year' and col is not None and col < len(row):
                    val = num(row[col])
                    if val is not None:
                        record[key] = val
            records.append(record)
        except (ValueError, TypeError, IndexError) as e:
            logger.warning(f"解析行数据异常: {e}")
    return records