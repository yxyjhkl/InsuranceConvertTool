# -*- coding: utf-8 -*-
"""
金尊分红保险利益演示系统 - Android版 (Kivy)
入口文件
"""
import os, sys, traceback, tempfile, logging
from datetime import datetime

__version__ = '2.0.0'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('main')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, ListProperty, BooleanProperty

from src.calculator import (
    InsuranceCalculator, CalcInput, HEADERS, calculate_from_pdf, calculate_from_db
)
from src.db_lookup import (
    load_db, get_data_summary, get_available_ages, get_available_premiums,
    get_available_payments, interpolate_age_data, clear_db_cache
)
from src.quote import get_random_quote
from src.exporter import ExcelExporter, ImageExporter, export_table_to_image, find_font
from controllers.pdf_controller import (
    extract_pdf_text_and_tables, detect_dividend_type,
    parse_all_tables_to_records, extract_pdf_info, parse_filename
)
from controllers.export_controller import generate_filename as gen_export_filename

Window.clearcolor = (0.96, 0.96, 0.98, 1)

COLOR_PRIMARY = (0.12, 0.56, 1.0, 1)       # #1890ff
COLOR_SUCCESS = (0.32, 0.77, 0.10, 1)       # #52c41a
COLOR_WARNING = (0.98, 0.55, 0.09, 1)       # #fa8c16
COLOR_DANGER = (1.0, 0.30, 0.31, 1)         # #ff4d4f
COLOR_PURPLE = (0.45, 0.18, 0.82, 1)        # #722ed1
COLOR_CYAN = (0.07, 0.76, 0.76, 1)          # #13c2c2
COLOR_GOLD = (0.98, 0.68, 0.08, 1)          # #faad14
COLOR_DARK = (0.18, 0.31, 0.59, 1)          # #2F5496

TOTAL_COLUMNS = 14
DEFAULT_PAYMENT = 8
DEFAULT_PREMIUM = 100000


class ColoredButton(Button):
    """带颜色的按钮"""
    def __init__(self, bg_color=None, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(44)
        self.font_size = sp(14)
        self.bold = True
        self.color = (1, 1, 1, 1)
        self.background_normal = ''
        if bg_color:
            self.background_color = bg_color
        else:
            self.background_color = COLOR_PRIMARY


class WelcomeScreen(Screen):
    """欢迎页面"""
    quote_text = StringProperty('')
    db_info_text = StringProperty('')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        root.add_widget(Label(size_hint_y=None, height=dp(30)))

        title = Label(
            text='金尊分红保险\n利益演示系统',
            font_size=sp(22), bold=True,
            color=(0.12, 0.31, 0.59, 1),
            halign='center', size_hint_y=None, height=dp(70)
        )
        title.bind(size=title.setter('text_size'))
        root.add_widget(title)

        ver = Label(
            text=f'v{__version__} | Android版',
            font_size=sp(12), color=(0.5, 0.5, 0.5, 1),
            halign='center', size_hint_y=None, height=dp(24)
        )
        root.add_widget(ver)

        quote_box = BoxLayout(
            orientation='vertical',
            size_hint_y=None, height=dp(80),
            padding=dp(12), spacing=dp(4)
        )
        self.quote_label = Label(
            text='', font_size=sp(13), color=(0.25, 0.25, 0.35, 1),
            halign='left', valign='middle', text_size=(Window.width - dp(64), None)
        )
        self.quote_label.bind(size=self.quote_label.setter('text_size'))
        quote_box.add_widget(self.quote_label)
        root.add_widget(quote_box)

        self.db_label = Label(
            text='', font_size=sp(11), color=(0.6, 0.6, 0.6, 1),
            halign='center', size_hint_y=None, height=dp(20)
        )
        root.add_widget(self.db_label)

        root.add_widget(Label(size_hint_y=None, height=dp(10)))

        btn_import = ColoredButton(bg_color=COLOR_PRIMARY, text='📄 导入PDF建议书')
        btn_import.bind(on_release=self.go_import)
        root.add_widget(btn_import)

        btn_demo = ColoredButton(bg_color=COLOR_PURPLE, text='📊 离线演示（数据库）')
        btn_demo.bind(on_release=self.go_demo)
        root.add_widget(btn_demo)

        btn_about = ColoredButton(bg_color=COLOR_GOLD, text='ℹ️ 关于')
        btn_about.bind(on_release=self.show_about)
        root.add_widget(btn_about)

        root.add_widget(Label())

        self.add_widget(root)

    def on_enter(self, *args):
        self.quote_label.text = get_random_quote()
        try:
            summary = get_data_summary()
            if summary:
                self.db_label.text = (
                    f"离线数据库: {summary.get('source_count', 0)}份数据 | "
                    f"男女 {summary.get('max_age_male', '?')}/{summary.get('max_age_female', '?')}岁"
                )
            else:
                self.db_label.text = '离线数据库: 未加载'
        except Exception:
            self.db_label.text = '离线数据库: 未加载'

    def go_import(self, inst):
        self.manager.current = 'import_screen'

    def go_demo(self, inst):
        self.manager.current = 'demo_screen'

    def show_about(self, inst):
        popup = Popup(
            title='关于',
            content=Label(
                text=f'金尊分红保险利益演示系统\n版本 {__version__}\n\n'
                     '功能: PDF建议书解析\n分红利益计算\nExcel/图片导出\n\n'
                     '© 2026 保险科技',
                font_size=sp(14), halign='center'
            ),
            size_hint=(0.8, 0.4)
        )
        popup.open()


class ImportScreen(Screen):
    """PDF导入页面"""
    status_text = StringProperty('选择PDF文件开始导入')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parsed_records = []
        self.parsed_info = {}
        self.parsed_dtype = ''
        self.pdf_filename = ''
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))

        toolbar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        back_btn = Button(
            text='◀ 返回', size_hint_x=None, width=dp(80),
            background_color=COLOR_DARK, background_normal='', color=(1,1,1,1),
            font_size=sp(13), bold=True
        )
        back_btn.bind(on_release=lambda x: setattr(self.manager, 'current', 'welcome'))
        toolbar.add_widget(back_btn)

        self.title_label = Label(
            text='导入PDF建议书', font_size=sp(16), bold=True,
            color=(0.12, 0.31, 0.59, 1), size_hint_x=1, halign='left',
            valign='middle'
        )
        self.title_label.bind(size=self.title_label.setter('text_size'))
        toolbar.add_widget(self.title_label)
        root.add_widget(toolbar)

        self.status = Label(
            text=self.status_text, font_size=sp(13),
            color=(0.4, 0.4, 0.4, 1), size_hint_y=None, height=dp(36),
            halign='center', valign='middle'
        )
        self.status.bind(size=self.status.setter('text_size'))
        root.add_widget(self.status)

        btn_choose = ColoredButton(bg_color=COLOR_PRIMARY, text='📁 选择PDF文件')
        btn_choose.bind(on_release=self.show_filechooser)
        root.add_widget(btn_choose)

        self.preview_box = BoxLayout(
            orientation='vertical', size_hint_y=1, padding=dp(4)
        )
        self.preview_label = Label(
            text='导入后在下方查看数据预览',
            font_size=sp(12), color=(0.5, 0.5, 0.5, 1),
            halign='left', valign='top'
        )
        self.preview_label.bind(size=self.preview_label.setter('text_size'))
        self.preview_box.add_widget(self.preview_label)
        root.add_widget(self.preview_box)

        bottom_bar = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        btn_view = ColoredButton(bg_color=COLOR_SUCCESS, text='📋 查看数据')
        btn_view.bind(on_release=self.go_detail)
        bottom_bar.add_widget(btn_view)
        root.add_widget(bottom_bar)

        self.add_widget(root)

    def show_filechooser(self, inst):
        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(8))
        filechooser = FileChooserListView(
            filters=['*.pdf'], path='/storage/emulated/0' if os.path.exists('/storage/emulated/0') else os.path.expanduser('~')
        )
        content.add_widget(filechooser)

        btn_box = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        btn_cancel = ColoredButton(bg_color=COLOR_DANGER, text='取消')
        btn_ok = ColoredButton(bg_color=COLOR_PRIMARY, text='导入此文件')
        btn_box.add_widget(btn_cancel)
        btn_box.add_widget(btn_ok)
        content.add_widget(btn_box)

        popup = Popup(title='选择PDF文件', content=content, size_hint=(0.9, 0.8))

        def do_import(btn):
            popup.dismiss()
            if filechooser.selection:
                self.process_pdf(filechooser.selection[0])

        btn_ok.bind(on_release=do_import)
        btn_cancel.bind(on_release=popup.dismiss)
        popup.open()

    def process_pdf(self, pdf_path):
        try:
            self.status.text = '正在解析PDF...'

            def _parse(dt):
                try:
                    path = pdf_path
                    pdf_text, all_tables = extract_pdf_text_and_tables(path)
                    dtype = detect_dividend_type(all_tables)
                    records = parse_all_tables_to_records(all_tables, dtype or '')
                    info = extract_pdf_info(pdf_text)
                    fname = os.path.basename(path)
                    finfo = parse_filename(fname)
                    for k in ['age', 'sex', 'premium', 'years']:
                        if info.get(k) is None and finfo.get(k) is not None:
                            info[k] = finfo[k]

                    self.parsed_records = records
                    self.parsed_info = info
                    self.parsed_dtype = dtype or ''
                    self.pdf_filename = fname

                    if records:
                        preview = (
                            f"文件: {fname or '未知'}\n"
                            f"客户: {info.get('customer_name') or '未知'}\n"
                            f"产品: {info.get('product_name') or '未知'}\n"
                            f"分红类型: {dtype or '未知'}\n"
                            f"数据行数: {len(records)} 条\n"
                            f"首行: 年度{records[0].get('year','?')} "
                            f"年龄{records[0].get('age','?')} "
                            f"期交{records[0].get('premium',0):,.0f}元\n"
                            f"末行: 年度{records[-1].get('year','?')} "
                            f"年龄{records[-1].get('age','?')}"
                        )
                        self.preview_label.text = preview
                        self.status.text = f'解析完成! {len(records)} 条数据'
                    else:
                        self.preview_label.text = '未提取到数据，请检查PDF格式'
                        self.status.text = '解析失败: 无数据'
                except Exception as e:
                    self.status.text = f'错误: {str(e)[:50]}'
                    self.preview_label.text = f'解析失败:\n{traceback.format_exc()[:500]}'

            Clock.schedule_once(_parse, 0.1)
        except Exception as e:
            self.status.text = f'错误: {e}'

    def go_detail(self, inst):
        if not self.parsed_records:
            Popup(
                title='提示',
                content=Label(text='请先选择PDF文件并成功导入数据', font_size=sp(14)),
                size_hint=(0.7, 0.3)
            ).open()
            return
        ds = self.manager.get_screen('detail_screen')
        ds.set_data(self.parsed_records, self.parsed_info, self.parsed_dtype)
        self.manager.current = 'detail_screen'


class DemoScreen(Screen):
    """离线演示页面——数据库查询"""
    gender = StringProperty('M')
    age = NumericProperty(30)
    premium = NumericProperty(100000)
    payment = NumericProperty(8)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))

        toolbar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        back_btn = Button(
            text='◀ 返回', size_hint_x=None, width=dp(80),
            background_color=COLOR_DARK, background_normal='', color=(1,1,1,1),
            font_size=sp(13), bold=True
        )
        back_btn.bind(on_release=lambda x: setattr(self.manager, 'current', 'welcome'))
        toolbar.add_widget(back_btn)
        toolbar.add_widget(Label(
            text='离线演示', font_size=sp(16), bold=True,
            color=(0.12, 0.31, 0.59, 1), size_hint_x=1, halign='left', valign='middle'
        ))
        root.add_widget(toolbar)

        form = GridLayout(cols=2, size_hint_y=None, height=dp(200),
                          spacing=dp(8), padding=dp(4))
        form.row_default_height = dp(44)

        form.add_widget(Label(text='性别:', font_size=sp(13), halign='right', valign='middle'))
        gender_box = BoxLayout(spacing=dp(4))
        btn_m = Button(
            text='男', background_color=COLOR_PRIMARY, background_normal='',
            color=(1,1,1,1), font_size=sp(13)
        )
        btn_m.bind(on_release=lambda x: self.set_gender('M'))
        btn_f = Button(
            text='女', background_color=(0.8,0.8,0.8,1), background_normal='',
            color=(0.3,0.3,0.3,1), font_size=sp(13)
        )
        btn_f.bind(on_release=lambda x: self.set_gender('F'))
        gender_box.add_widget(btn_m)
        gender_box.add_widget(btn_f)
        form.add_widget(gender_box)

        form.add_widget(Label(text='年龄:', font_size=sp(13), halign='right', valign='middle'))
        age_input = TextInput(text='30', multiline=False, input_filter='int',
                              font_size=sp(14), size_hint_y=None, height=dp(40),
                              halign='center')
        age_input.bind(text=self.on_age_change)
        form.add_widget(age_input)

        form.add_widget(Label(text='年交保费(万):', font_size=sp(13), halign='right', valign='middle'))
        prem_input = TextInput(text='10', multiline=False, input_filter='int',
                               font_size=sp(14), size_hint_y=None, height=dp(40),
                               halign='center')
        prem_input.bind(text=self.on_premium_change)
        form.add_widget(prem_input)

        form.add_widget(Label(text='缴费年限:', font_size=sp(13), halign='right', valign='middle'))
        pymt_spinner = Spinner(
            text='8年', values=('3年', '5年', '8年', '10年', '15年', '20年'),
            size_hint_y=None, height=dp(40)
        )
        pymt_spinner.bind(text=self.on_payment_change)
        form.add_widget(pymt_spinner)

        root.add_widget(form)

        btn_gen = ColoredButton(bg_color=COLOR_SUCCESS, text='⚡ 生成利益演示')
        btn_gen.bind(on_release=self.do_demo)
        root.add_widget(btn_gen)

        self.result_label = Label(
            text='点击"生成利益演示"查看结果',
            font_size=sp(12), color=(0.5,0.5,0.5,1),
            halign='left', valign='top'
        )
        self.result_label.bind(size=self.result_label.setter('text_size'))
        root.add_widget(self.result_label)

        root.add_widget(Label())
        self.add_widget(root)

    def set_gender(self, g):
        self.gender = g

    def on_age_change(self, inst, value):
        try:
            self.age = int(value)
        except Exception:
            pass

    def on_premium_change(self, inst, value):
        try:
            self.premium = int(value) * 10000
        except Exception:
            pass

    def on_payment_change(self, inst, value):
        try:
            self.payment = int(value.replace('年', ''))
        except Exception:
            pass

    def do_demo(self, inst):
        try:
            self.result_label.text = '正在查询数据库...'
            data = interpolate_age_data(
                int(self.age), self.gender, int(self.premium), 1.0
            )
            if data:
                ds = self.manager.get_screen('detail_screen')
                info = {
                    'customer_name': f'{self.age}岁{"男" if self.gender=="M" else "女"}',
                    'product_name': '数据库演示',
                    'age': int(self.age),
                    'sex': '男' if self.gender == 'M' else '女',
                    'premium': int(self.premium) // 10000,
                    'years': int(self.payment),
                }
                ds.set_data(data, info, '数据库', source='db',
                           age=int(self.age), premium=int(self.premium),
                           payment=int(self.payment))
                self.manager.current = 'detail_screen'
            else:
                self.result_label.text = '未找到匹配数据，请调整参数重试'
        except Exception as e:
            self.result_label.text = f'查询失败: {str(e)[:100]}'


class DetailScreen(Screen):
    """数据表格+分红率调整+导出页面"""
    rate_value = NumericProperty(100)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.raw_records = []
        self.info = {}
        self.dtype = ''
        self.source = 'pdf'
        self.calc_age = 30
        self.calc_premium = 100000
        self.calc_payment = 8
        self.current_display = []
        self.build_ui()

    def build_ui(self):
        self.root_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(6))

        toolbar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        back_btn = Button(
            text='◀ 返回', size_hint_x=None, width=dp(80),
            background_color=COLOR_DARK, background_normal='', color=(1,1,1,1),
            font_size=sp(13), bold=True
        )
        back_btn.bind(on_release=lambda x: setattr(self.manager, 'current', 'welcome'))
        toolbar.add_widget(back_btn)

        self.info_label = Label(
            text='', font_size=sp(12), color=(0.12, 0.31, 0.59, 1),
            halign='left', valign='middle', bold=True
        )
        self.info_label.bind(size=self.info_label.setter('text_size'))
        toolbar.add_widget(self.info_label)
        self.root_layout.add_widget(toolbar)

        rate_bar = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8), padding=[dp(4), dp(0)])
        rate_bar.add_widget(Label(
            text='分红实现率:', font_size=sp(13), size_hint_x=None, width=dp(90),
            halign='right', valign='middle'
        ))
        self.rate_slider = Slider(min=50, max=200, value=100, step=1)
        self.rate_slider.bind(value=self.on_rate_change)
        rate_bar.add_widget(self.rate_slider)
        self.rate_label = Label(
            text='100%', font_size=sp(14), bold=True,
            color=(0.12, 0.31, 0.59, 1), size_hint_x=None, width=dp(50),
            halign='center', valign='middle'
        )
        rate_bar.add_widget(self.rate_label)
        self.root_layout.add_widget(rate_bar)

        self.table_header = GridLayout(cols=14, size_hint_y=None, height=dp(32),
                                        spacing=dp(1), padding=[dp(2), dp(0)])
        short_headers = ['年度', '年龄', '期交', '累计保费', '身故', '现价', '现价率',
                          '当年分红', '累计分红', '演示生存', '演示率', '预期生存', '预期率', '单利']
        for h in short_headers:
            lbl = Label(
                text=h, font_size=sp(8), bold=True,
                color=(1,1,1,1), size_hint_x=None, width=dp(60),
                halign='center', valign='middle', shorten=True
            )
            lbl.canvas.before.clear()
            from kivy.graphics import Color, Rectangle
            with lbl.canvas.before:
                Color(*COLOR_DARK)
                Rectangle(pos=lbl.pos, size=lbl.size)
            lbl.bind(
                pos=lambda inst, val, l=lbl: self._update_header_bg(l, val),
                size=lambda inst, val, l=lbl: self._update_header_bg(l, val)
            )
            self.table_header.add_widget(lbl)
        self.root_layout.add_widget(self.table_header)

        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=True, do_scroll_y=True)
        self.data_grid = GridLayout(cols=14, size_hint_y=None, spacing=dp(1))
        self.data_grid.bind(minimum_height=self.data_grid.setter('height'))
        scroll.add_widget(self.data_grid)
        self.root_layout.add_widget(scroll)

        export_bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        btn_excel = ColoredButton(bg_color=COLOR_WARNING, text='导出Excel')
        btn_excel.bind(on_release=self.do_export_excel)
        export_bar.add_widget(btn_excel)

        btn_img = ColoredButton(bg_color=COLOR_WARNING, text='导出图片')
        btn_img.bind(on_release=self.do_export_image)
        export_bar.add_widget(btn_img)

        btn_a4 = ColoredButton(bg_color=COLOR_CYAN, text='A4导出')
        btn_a4.bind(on_release=self.do_export_a4)
        export_bar.add_widget(btn_a4)

        self.root_layout.add_widget(export_bar)
        self.add_widget(self.root_layout)

    def _update_header_bg(self, lbl, val):
        pass

    def set_data(self, records, info, dtype, source='pdf',
                 age=30, premium=100000, payment=8):
        self.raw_records = records
        self.info = info or {}
        self.dtype = dtype
        self.source = source
        self.calc_age = int(age)
        self.calc_premium = int(premium)
        self.calc_payment = int(payment)

        name = info.get('customer_name') or ''
        prod = info.get('product_name') or ''
        if name and prod:
            self.info_label.text = f'{name} | {prod}'
        elif name:
            self.info_label.text = f'{name}'
        elif prod:
            self.info_label.text = f'{prod}'
        elif source == 'db':
            self.info_label.text = f'{age}岁{"男" if info.get("sex")=="男" else "女"} {premium//10000}万 {payment}年'
        else:
            self.info_label.text = '数据已加载'

        self.rate_slider.value = 100
        self.rate_label.text = '100%'
        self.refresh_table()

    def on_rate_change(self, inst, value):
        self.rate_label.text = f'{int(value)}%'
        self.refresh_table()

    def refresh_table(self):
        self.data_grid.clear_widgets()
        if not self.raw_records:
            return

        rate = self.rate_slider.value / 100.0

        try:
            if self.source == 'db':
                result = calculate_from_db(
                    self.raw_records, self.calc_age, self.calc_premium,
                    self.calc_payment, rate, self.info.get('customer_name', '')
                )
            else:
                result = calculate_from_pdf(
                    self.raw_records, rate, self.info.get('customer_name', '')
                )

            calc_data = result.get('data', [])
            self.current_display = calc_data

            for idx, row in enumerate(calc_data):
                bg = (0.95, 0.95, 0.95, 1) if idx % 2 == 0 else (1, 1, 1, 1)

                ordered_keys = [
                    'policy_year', 'age', 'premium', 'total_premium',
                    'death_benefit', 'cash_value', 'growth_rate',
                    'current_dividend_cash', 'accum_dividend_cash',
                    'demo_survival', 'demo_rate',
                    'expected_survival', 'expected_rate',
                    'expected_simple_rate'
                ]

                for key in ordered_keys:
                    val = row.get(key, '')

                    if val is None:
                        text = '--'
                    elif key in ('growth_rate', 'demo_rate', 'expected_rate', 'expected_simple_rate'):
                        try:
                            text = f'{float(val)*100:.2f}%'
                        except Exception:
                            text = str(val)
                    elif key in ('policy_year', 'age'):
                        text = str(int(val)) if val is not None and val != '' else ''
                    else:
                        try:
                            text = f'{int(round(float(val))):,}'
                        except Exception:
                            text = str(val)

                    lbl = Label(
                        text=text,
                        font_size=sp(8), color=(0.1, 0.1, 0.1, 1),
                        size_hint_x=None, width=dp(60), halign='center',
                        valign='middle', shorten=True
                    )
                    from kivy.graphics import Color as KvColor, Rectangle
                    with lbl.canvas.before:
                        KvColor(*bg)
                        Rectangle(pos=lbl.pos, size=lbl.size)
                    lbl._bg = bg
                    self.data_grid.add_widget(lbl)

        except Exception as e:
            logger.error(f"刷新表格失败: {e}\n{traceback.format_exc()}")

    def _row_bg(self, lbl):
        bg = getattr(lbl, '_bg', (1, 1, 1, 1))
        from kivy.graphics import Color, Rectangle
        lbl.canvas.before.clear()
        with lbl.canvas.before:
            Color(*bg)
            Rectangle(pos=lbl.pos, size=lbl.size)

    def do_export_excel(self, inst):
        self._export('xlsx')

    def do_export_image(self, inst):
        self._export('png')

    def do_export_a4(self, inst):
        self._export('a4')

    def _export(self, fmt):
        if not self.current_display:
            Popup(title='提示', content=Label(text='没有数据可导出', font_size=sp(14)),
                  size_hint=(0.7, 0.3)).open()
            return

        try:
            display_rows = []
            for row in self.current_display:
                def fmt_n(v):
                    if v is None: return ''
                    try: return f"{int(round(float(v))):,}"
                    except: return str(v)
                def fmt_r(v):
                    if v is None: return ''
                    try: return f"{float(v):.2%}"
                    except: return str(v)
                display_rows.append([
                    str(row.get('policy_year', '')),
                    str(row.get('age', '')),
                    fmt_n(row.get('premium')),
                    fmt_n(row.get('total_premium')),
                    fmt_n(row.get('death_benefit')),
                    fmt_n(row.get('cash_value')),
                    fmt_r(row.get('growth_rate')),
                    fmt_n(row.get('current_dividend_cash')),
                    fmt_n(row.get('accum_dividend_cash')),
                    fmt_n(row.get('demo_survival')),
                    fmt_r(row.get('demo_rate')),
                    fmt_n(row.get('expected_survival')),
                    fmt_r(row.get('expected_rate')),
                    fmt_r(row.get('expected_simple_rate')),
                ])

            headers = HEADERS
            output_dir = tempfile.gettempdir()
            prefix = f"Insurance_{self.info.get('customer_name', '')}"
            fname = gen_export_filename(output_dir, prefix, fmt if fmt != 'a4' else 'png')

            if fmt == 'xlsx':
                exporter = ExcelExporter(headers, display_rows,
                                        self.info.get('customer_name', ''))
                exporter.export(fname)
            else:
                exporter = ImageExporter(headers, display_rows,
                                        self.info.get('customer_name', ''))
                if fmt == 'a4':
                    exporter.export_a4(fname)
                else:
                    exporter.export_image(fname)

            Popup(
                title='导出成功',
                content=Label(
                    text=f'文件已保存到:\n{fname}',
                    font_size=sp(13), halign='center'
                ),
                size_hint=(0.8, 0.35)
            ).open()
            logger.info("导出成功: %s", fname)
        except Exception as e:
            Popup(
                title='导出失败',
                content=Label(text=f'错误: {e}', font_size=sp(13)),
                size_hint=(0.8, 0.3)
            ).open()
            logger.error(f"导出失败: {e}\n{traceback.format_exc()}")


class InsuranceApp(App):
    title = '金尊分红保险演示'
    icon = 'icon.png'

    def build(self):
        sm = ScreenManager(transition=SlideTransition())

        sm.add_widget(WelcomeScreen(name='welcome'))
        sm.add_widget(ImportScreen(name='import_screen'))
        sm.add_widget(DemoScreen(name='demo_screen'))
        sm.add_widget(DetailScreen(name='detail_screen'))

        sm.current = 'welcome'
        return sm

    def on_start(self):
        logger.info("金尊分红Android版 v%s 启动", __version__)


if __name__ == '__main__':
    InsuranceApp().run()