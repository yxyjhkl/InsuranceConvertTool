# -*- coding: utf-8 -*-
"""
PDF导入控制器
处理PDF文件解析、表格提取和数据转换
"""

from __future__ import annotations

import re
import logging
from typing import Dict, List, Optional, Tuple, Union

import pdfplumber

logger = logging.getLogger(__name__)

PDFInfo = Dict[str, Optional[Union[int, float, str]]]
TableRow = Dict[str, Union[int, float]]


def extract_pdf_text_and_tables(pdf_path: str) -> Tuple[str, List[Tuple[List, int]]]:
    pdf_text = ""
    all_tables: List[Tuple[List, int]] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            pdf_text += page_text

            for table in page.extract_tables():
                if table and len(table) >= 1 and len(table[0]) >= 7:
                    col_count = len(table[0])
                    all_tables.append((table, col_count))

    return pdf_text, all_tables


def detect_dividend_type(all_tables: List[Tuple[List, int]]) -> str:
    for table, col_count in all_tables:
        if not table or col_count < 7:
            continue
        all_rows_text = ""
        for row in table[:5]:
            all_rows_text += ' '.join([str(c).replace('\n', '') for c in row if c]) + ' '
        if '当年交清增额' in all_rows_text or '累积交清增额' in all_rows_text:
            return '交清增额'
        elif '当年红利' in all_rows_text or '累积红利' in all_rows_text:
            return '累积生息'
    return ''


def parse_all_tables_to_records(all_tables: List[Tuple[List, int]],
                                 dividend_type: str) -> List[TableRow]:
    records: List[TableRow] = []

    for table, col_count in all_tables:
        if not table or len(table) < 1 or len(table[0]) < 7:
            continue

        header = ' '.join([str(c) for c in table[0] if c])
        is_data_table = _is_data_table(table, col_count, header)
        if not is_data_table:
            continue

        if dividend_type == '交清增额':
            _parse_jiaoqing_table(table, col_count, records)
        else:
            _parse_leiji_table(table, col_count, records)

    records = _deduplicate_records(records)
    return records


def _is_data_table(table: List, col_count: int, header: str) -> bool:
    if col_count >= 10:
        for h_row in table[:3]:
            h_text = ' '.join([str(c) for c in h_row if c])
            if '年龄' in h_text or '被保险人' in h_text or '被保人' in h_text or '保单年度' in h_text:
                return True
        return False
    else:
        return '年龄' in header or '被保险人' in header or '被保人' in header


def _parse_jiaoqing_table(table: List, col_count: int, records: List[TableRow]) -> None:
    start_idx = 2 if col_count >= 10 else 2
    for i in range(start_idx, len(table)):
        row = table[i]
        if not row or not row[0] or not str(row[0]).strip().isdigit():
            continue
        try:
            year = int(str(row[0]).strip())
            age = int(str(row[1]).strip())
            if not (1 <= year <= 105 and age >= 0):
                continue

            if col_count >= 10:
                current_div = float(str(row[7]).replace(',', '')) if row[7] and row[7] != '--' else 0
                accum_div = 0.0
                if i + 1 < len(table):
                    next_row = table[i + 1]
                    if next_row and len(next_row) > 7 and next_row[7] and next_row[7] != '--':
                        try:
                            accum_div = float(str(next_row[7]).replace(',', ''))
                        except (ValueError, TypeError):
                            pass
                records.append({
                    'year': year, 'age': age,
                    'premium': float(str(row[2]).replace(',', '')) if row[2] and row[2] != '--' else 0,
                    'total_premium': float(str(row[3]).replace(',', '')) if row[3] and row[3] != '--' else 0,
                    'death': float(str(row[6]).replace(',', '')) if row[6] and row[6] != '--' else 0,
                    'low': float(str(row[9]).replace(',', '')) if row[9] and row[9] != '--' else 0,
                    'low_rate': float(str(row[10]).replace(',', '')) if row[10] and row[10] != '--' else 0,
                    'mid': float(str(row[4]).replace(',', '')) if row[4] and row[4] != '--' else 0,
                    'mid_rate': float(str(row[5]).replace(',', '')) if row[5] and row[5] != '--' else 0,
                    'high': float(str(row[11]).replace(',', '')) if row[11] and row[11] != '--' else 0,
                    'current_dividend': current_div,
                    'accum_dividend': accum_div,
                })
            else:
                records.append({
                    'year': year, 'age': age,
                    'premium': 0,
                    'total_premium': float(str(row[2]).replace(',', '')) if row[2] and row[2] != '--' else 0,
                    'death': float(str(row[5]).replace(',', '')) if row[5] and row[5] != '--' else 0,
                    'low': float(str(row[3]).replace(',', '')) if row[3] and row[3] != '--' else 0,
                    'low_rate': float(str(row[4]).replace(',', '')) if row[4] and row[4] != '--' else 0,
                    'mid': float(str(row[3]).replace(',', '')) if row[3] and row[3] != '--' else 0,
                    'mid_rate': float(str(row[4]).replace(',', '')) if row[4] and row[4] != '--' else 0,
                    'high': 0,
                    'current_dividend': 0,
                    'accum_dividend': 0,
                })
        except (ValueError, TypeError, IndexError) as e:
            logger.warning(f"PDF解析交清增额行数据异常(行{i}): {e}")


def _parse_leiji_table(table: List, col_count: int, records: List[TableRow]) -> None:
    start_idx = 2 if col_count >= 8 else 2
    for i in range(start_idx, len(table)):
        row = table[i]
        if not row or not row[0] or not str(row[0]).strip().isdigit():
            continue
        try:
            year = int(str(row[0]).strip())
            age = int(str(row[1]).strip())
            if not (1 <= year <= 105 and age >= 0):
                continue

            if col_count >= 8:
                records.append({
                    'year': year, 'age': age,
                    'premium': float(str(row[2]).replace(',', '')) if row[2] and row[2] != '--' else 0,
                    'total_premium': float(str(row[3]).replace(',', '')) if row[3] and row[3] != '--' else 0,
                    'death': float(str(row[6]).replace(',', '')) if row[6] and row[6] != '--' else 0,
                    'low': float(str(row[9]).replace(',', '')) if row[9] and row[9] != '--' else 0,
                    'low_rate': float(str(row[10]).replace(',', '')) if col_count > 10 and row[10] and row[10] != '--' else 0,
                    'mid': float(str(row[4]).replace(',', '')) if row[4] and row[4] != '--' else 0,
                    'mid_rate': float(str(row[5]).replace(',', '')) if row[5] and row[5] != '--' else 0,
                    'high': float(str(row[11]).replace(',', '')) if col_count > 11 and row[11] and row[11] != '--' else 0,
                    'current_dividend': float(str(row[7]).replace(',', '')) if row[7] and row[7] != '--' else 0,
                    'accum_dividend': float(str(row[8]).replace(',', '')) if col_count > 8 and row[8] and row[8] != '--' else 0,
                })
            else:
                records.append({
                    'year': year, 'age': age,
                    'premium': 0,
                    'total_premium': float(str(row[2]).replace(',', '')) if row[2] and row[2] != '--' else 0,
                    'death': float(str(row[5]).replace(',', '')) if row[5] and row[5] != '--' else 0,
                    'low': float(str(row[3]).replace(',', '')) if row[3] and row[3] != '--' else 0,
                    'low_rate': float(str(row[4]).replace(',', '')) if row[4] and row[4] != '--' else 0,
                    'mid': float(str(row[3]).replace(',', '')) if row[3] and row[3] != '--' else 0,
                    'mid_rate': float(str(row[4]).replace(',', '')) if row[4] and row[4] != '--' else 0,
                    'high': 0,
                    'current_dividend': 0,
                    'accum_dividend': 0,
                })
        except (ValueError, TypeError, IndexError) as e:
            logger.warning(f"PDF解析累积生息行数据异常(行{i}): {e}")


def _deduplicate_records(records: List[TableRow]) -> List[TableRow]:
    seen_years: Dict[int, TableRow] = {}
    for r in records:
        year = int(r['year'])
        existing = seen_years.get(year)
        if existing is None:
            seen_years[year] = r
        elif r.get('current_dividend', 0) > 0 and existing.get('current_dividend', 0) == 0:
            seen_years[year] = r
        elif r.get('accum_dividend', 0) > 0 and existing.get('accum_dividend', 0) == 0:
            seen_years[year] = r

    result = list(seen_years.values())
    result.sort(key=lambda x: x['year'])
    return result


def extract_pdf_info(text: str) -> PDFInfo:
    info: PDFInfo = {
        'customer_name': None, 'product_name': None,
        'age': None, 'sex': None, 'premium': None, 'years': None
    }

    for p in [
        r'姓\s*名[：:]\s*([^\s\d]{2,10})',
        r'客户[：:]\s*([^\s\d]{2,10})',
        r'被保人[：:]\s*([^\s\d]{2,10})',
    ]:
        m = re.search(p, text)
        if m:
            info['customer_name'] = m.group(1).strip()
            break

    m = re.search(r'(.+?)的利益演示表', text)
    if m:
        info['product_name'] = m.group(1).strip()
    else:
        for p in [
            r'产品名称[：:]\s*([^\n]{5,30})',
            r'保险产品[：:]\s*([^\n]{5,30})',
            r'的建议书[：:]\s*([^\n]{5,30})',
        ]:
            m = re.search(p, text)
            if m:
                info['product_name'] = m.group(1).strip()
                break

    m = re.search(r'投保年龄[：:]\s*(\d+)', text)
    if m:
        info['age'] = int(m.group(1))

    if '性别' in text:
        parts = text.split('性别')
        if len(parts) > 1:
            snippet = parts[1][:10]
            if '男' in snippet:
                info['sex'] = '男'
            elif '女' in snippet:
                info['sex'] = '女'

    m = re.search(r'年交保费[：:]\s*(\d+)', text)
    if m:
        info['premium'] = int(m.group(1))

    m = re.search(r'缴费年限[：:]\s*(\d+)', text)
    if m:
        info['years'] = int(m.group(1))

    return info


def parse_filename(filename: str) -> PDFInfo:
    info: PDFInfo = {'age': None, 'sex': None, 'premium': None, 'years': None}
    fname = filename.lower().replace('.pdf', '')

    m = re.search(r'(\d+)\s*岁', fname)
    if m:
        info['age'] = int(m.group(1))

    if '男' in fname or '男性' in fname:
        info['sex'] = '男'
    elif '女' in fname or '女性' in fname:
        info['sex'] = '女'

    m = re.search(r'(\d+)\s*[万w]\s*\d+\s*年', fname)
    if m:
        info['premium'] = int(m.group(1))
    else:
        m = re.search(r'(\d+)\s*[万w]', fname)
        if m:
            premium_candidate = int(m.group(1))
            if info.get('age') is None or premium_candidate != info['age']:
                info['premium'] = premium_candidate

    m = re.search(r'(\d+)\s*年', fname)
    if m:
        info['years'] = int(m.group(1))

    return info