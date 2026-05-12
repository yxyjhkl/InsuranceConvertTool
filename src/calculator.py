"""
保险数据计算器
14列数据计算逻辑
"""

from typing import List, Dict, Optional
from dataclasses import dataclass


HEADERS = [
    '保单年度', '年龄', '期交保费', '累计保费', '身故总利益',
    '主险现价', '现价增长率', '当年分红现价', '累计分红现价',
    '演示生存总利益', '演示增长率', '预期生存总利益',
    '预期增长率', '预期单利'
]


@dataclass
class CalcInput:
    age: int
    premium: float
    payment_years: int = 8
    dividend_rate: float = 1.0
    customer_name: str = ''
    source: str = 'pdf'


@dataclass
class DataRow:
    policy_year: int
    age: int
    premium: float
    total_premium: float
    death_benefit: float
    cash_value: float
    growth_rate: Optional[float]
    current_dividend_cash: float
    accum_dividend_cash: float
    demo_survival: float
    demo_rate: Optional[float]
    expected_survival: float
    expected_rate: Optional[float]
    expected_simple_rate: Optional[float]


class InsuranceCalculator:
    """保险数据计算器"""

    def __init__(self, input_data: List[Dict], calc_input: CalcInput):
        self.input_data = input_data
        self.calc_input = calc_input
        self.result: List[DataRow] = []

    def calculate(self) -> List[Dict]:
        if not self.input_data:
            return []

        self.result = []
        payment_years = self.calc_input.payment_years
        dividend_rate = self.calc_input.dividend_rate
        multiplier = self.calc_input.premium / 100000
        source = self.calc_input.source or 'pdf'
        already_scaled = (source == 'db')

        prev_cash = 0.0
        prev_expected = 0.0

        for idx, row in enumerate(self.input_data):
            year = row.get('year') or row.get('policy_year') or idx + 1
            age = row.get('age', self.calc_input.age + idx)

            if year <= payment_years:
                premium = self.calc_input.premium
            else:
                premium = 0.0

            total_premium = row.get('total_premium', 0)
            if total_premium and not already_scaled:
                total_premium = total_premium * multiplier

            guaranteed = row.get('guaranteed_survival') or row.get('guaranteed') or row.get('low') or 0
            demo_survival = row.get('demo_survival') or row.get('mid') or 0
            death_base = row.get('death_benefit') or row.get('death_base') or row.get('death') or 0

            if not already_scaled:
                guaranteed = guaranteed * multiplier
                demo_survival = demo_survival * multiplier
                death_base = death_base * multiplier

            accum_div_raw = demo_survival - guaranteed
            accum_div_demo = accum_div_raw * dividend_rate
            current_div_demo = accum_div_demo / year if year > 0 else 0

            death_benefit = death_base + accum_div_demo
            cash_value = guaranteed
            current_dividend_cash = current_div_demo
            accum_dividend_cash = accum_div_demo
            demo_rate = row.get('demo_rate') or row.get('growth_rate')

            growth_rate = None
            if prev_cash > 0:
                growth_rate = (cash_value / prev_cash) - 1

            expected_survival = cash_value + accum_dividend_cash

            expected_rate = None
            if prev_expected > 0:
                expected_rate = (expected_survival / prev_expected) - 1

            expected_simple_rate = None
            if year > payment_years and total_premium > 0:
                years_factor = year - 3.5
                if expected_survival > total_premium:
                    expected_simple_rate = (expected_survival - total_premium) / total_premium / years_factor

            data_row = DataRow(
                policy_year=year,
                age=int(age),
                premium=premium,
                total_premium=total_premium,
                death_benefit=death_benefit,
                cash_value=cash_value,
                growth_rate=growth_rate,
                current_dividend_cash=current_dividend_cash,
                accum_dividend_cash=accum_dividend_cash,
                demo_survival=demo_survival,
                demo_rate=demo_rate,
                expected_survival=expected_survival,
                expected_rate=expected_rate,
                expected_simple_rate=expected_simple_rate,
            )
            self.result.append(data_row)

            prev_cash = cash_value
            prev_expected = expected_survival

        return self.to_dict_list()

    def to_dict_list(self) -> List[Dict]:
        return [
            {
                'policy_year': row.policy_year,
                'age': row.age,
                'premium': row.premium,
                'total_premium': row.total_premium,
                'death_benefit': row.death_benefit,
                'cash_value': row.cash_value,
                'growth_rate': row.growth_rate,
                'current_dividend_cash': row.current_dividend_cash,
                'accum_dividend_cash': row.accum_dividend_cash,
                'demo_survival': row.demo_survival,
                'demo_rate': row.demo_rate,
                'expected_survival': row.expected_survival,
                'expected_rate': row.expected_rate,
                'expected_simple_rate': row.expected_simple_rate,
            }
            for row in self.result
        ]

    def get_headers(self) -> List[str]:
        return HEADERS

    def get_display_data(self) -> List[List]:
        rows = []
        for row in self.result:
            rows.append([
                row.policy_year,
                row.age,
                f'{row.premium:,.0f}' if row.premium else '',
                f'{row.total_premium:,.0f}' if row.total_premium else '',
                f'{row.death_benefit:,.0f}' if row.death_benefit else '',
                f'{row.cash_value:,.0f}' if row.cash_value else '',
                f'{row.growth_rate:.2%}' if row.growth_rate is not None else '',
                f'{row.current_dividend_cash:,.0f}' if row.current_dividend_cash else '',
                f'{row.accum_dividend_cash:,.0f}' if row.accum_dividend_cash else '',
                f'{row.demo_survival:,.0f}' if row.demo_survival else '',
                f'{row.demo_rate:.2%}' if row.demo_rate is not None else '',
                f'{row.expected_survival:,.0f}' if row.expected_survival else '',
                f'{row.expected_rate:.2%}' if row.expected_rate is not None else '',
                f'{row.expected_simple_rate:.2%}' if row.expected_simple_rate is not None else '',
            ])
        return rows


def calculate_from_pdf(pdf_data: List[Dict], dividend_rate: float = 1.0, customer_name: str = '') -> Dict:
    if not pdf_data:
        return {'headers': HEADERS, 'data': [], 'display_data': [], 'customer_name': customer_name}

    first_row = pdf_data[0]
    calc_input = CalcInput(
        age=int(first_row.get('age', 0) or 0),
        premium=first_row.get('premium') or first_row.get('total_premium') or 100000,
        payment_years=8,
        dividend_rate=dividend_rate,
        customer_name=customer_name,
        source='pdf'
    )

    calculator = InsuranceCalculator(pdf_data, calc_input)
    calculator.calculate()

    return {
        'headers': calculator.get_headers(),
        'data': calculator.to_dict_list(),
        'display_data': calculator.get_display_data(),
        'customer_name': customer_name,
    }


def calculate_from_db(db_data: List[Dict], age: int, premium: float,
                      payment_years: int, dividend_rate: float = 1.0,
                      customer_name: str = '') -> Dict:
    if not db_data:
        return {'headers': HEADERS, 'data': [], 'display_data': [], 'customer_name': customer_name}

    calc_input = CalcInput(
        age=age,
        premium=premium,
        payment_years=payment_years,
        dividend_rate=dividend_rate,
        customer_name=customer_name,
        source='db'
    )

    calculator = InsuranceCalculator(db_data, calc_input)
    calculator.calculate()

    return {
        'headers': calculator.get_headers(),
        'data': calculator.to_dict_list(),
        'display_data': calculator.get_display_data(),
        'customer_name': customer_name,
    }