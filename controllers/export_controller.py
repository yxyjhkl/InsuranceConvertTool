# -*- coding: utf-8 -*-
"""
导出控制器
处理Excel、图片、A4纸张格式的导出
"""

from __future__ import annotations

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def generate_filename(output_dir: str, prefix: str, ext: str,
                      customer_name: str = '') -> str:
    """
    生成导出文件名

    Args:
        output_dir: 输出目录
        prefix: 文件名前缀
        ext: 文件扩展名（不含点）
        customer_name: 客户姓名

    Returns:
        完整文件路径
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if customer_name:
        filename = f"{prefix}_{customer_name}_{timestamp}.{ext}"
    else:
        filename = f"{prefix}_{timestamp}.{ext}"

    filepath = os.path.join(output_dir, filename)

    counter = 1
    while os.path.exists(filepath):
        if customer_name:
            filename = f"{prefix}_{customer_name}_{timestamp}_{counter}.{ext}"
        else:
            filename = f"{prefix}_{timestamp}_{counter}.{ext}"
        filepath = os.path.join(output_dir, filename)
        counter += 1

    return filepath


def export_to_excel(data: List[Dict], output_path: str, title: str = '') -> bool:
    """
    将数据导出为Excel文件

    Args:
        data: 数据列表
        output_path: 输出文件路径
        title: 表格标题

    Returns:
        是否成功
    """
    try:
        from src.exporter import ExcelExporter, HEADERS as headers14

        headers = headers14 if len(headers14) == 14 else [
            '保单年度', '年龄', '期交保费', '累计保费', '身故总利益',
            '主险现价', '现价增长率', '当年分红现价', '累计分红现价',
            '演示生存总利益', '演示增长率', '预期生存总利益',
            '预期增长率', '预期单利'
        ]

        display_data = []
        for row_data in data:
            display_data.append([
                row_data.get('policy_year', ''),
                row_data.get('age', ''),
                format_number(row_data.get('premium')),
                format_number(row_data.get('total_premium')),
                format_number(row_data.get('death_benefit')),
                format_number(row_data.get('cash_value')),
                format_rate(row_data.get('growth_rate')),
                format_number(row_data.get('current_dividend_cash')),
                format_number(row_data.get('accum_dividend_cash')),
                format_number(row_data.get('demo_survival')),
                format_rate(row_data.get('demo_rate')),
                format_number(row_data.get('expected_survival')),
                format_rate(row_data.get('expected_rate')),
                format_rate(row_data.get('expected_simple_rate')),
            ])

        exporter = ExcelExporter(headers, display_data,
                                 customer_name=title or '')
        exporter.export(output_path)
        logger.info("Excel导出成功: %s", output_path)
        return True
    except Exception as e:
        logger.error("Excel导出失败: %s", e, exc_info=True)
        return False


def format_number(value) -> str:
    """格式化数字为千分位字符串"""
    if value is None:
        return ''
    try:
        return f"{float(value):,.0f}"
    except (ValueError, TypeError):
        return str(value)


def format_rate(value) -> str:
    """格式化比率"""
    if value is None:
        return ''
    try:
        return f"{float(value):.2%}"
    except (ValueError, TypeError):
        return str(value)