from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_TICK_LABEL_POSITION

BG = RGBColor(0x0B, 0x10, 0x20)
CARD = RGBColor(0x14, 0x1B, 0x33)
BORDER = RGBColor(0x2A, 0x34, 0x5C)
TXT = RGBColor(0xE8, 0xEC, 0xF8)
MUTED = RGBColor(0x9A, 0xA6, 0xC8)
TEAL = RGBColor(0x2D, 0xD4, 0xBF)
VIOLET = RGBColor(0x8B, 0x7C, 0xF6)
AMBER = RGBColor(0xF5, 0xB3, 0x42)
ROSE = RGBColor(0xF4, 0x72, 0x8F)
FONT = 'Segoe UI'

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank = prs.slide_layouts[6]


def bg(slide):
    f = slide.background.fill
    f.solid()
    f.fore_color.rgb = BG


def rect(slide, x, y, w, h, fill=CARD, line=BORDER, radius=0.06):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.adjustments[0] = radius
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(0.75)
    s.shadow.inherit = False
    return s


def text(slide, x, y, w, h, runs, size=12, color=TXT, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, spacing=None):
    """runs: str, or list of paragraphs; each paragraph is str or list of (text, {opts})."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.04)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = anchor
    paras = runs if isinstance(runs, list) else [runs]
    for i, p in enumerate(paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        if spacing:
            para.space_after = Pt(spacing)
        segs = p if isinstance(p, list) else [(p, {})]
        for seg, o in segs:
            r = para.add_run()
            r.text = seg
            r.font.name = FONT
            r.font.size = Pt(o.get('size', size))
            r.font.bold = o.get('bold', bold)
            r.font.color.rgb = o.get('color', color)
    return tb


def header(slide, title, subtitle, n):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.12), Inches(7.5))
    bar.fill.solid(); bar.fill.fore_color.rgb = TEAL; bar.line.fill.background()
    text(slide, 0.5, 0.28, 10.5, 0.55, title, size=26, bold=True)
    text(slide, 0.5, 0.82, 10.5, 0.3, subtitle, size=12, color=MUTED)
    text(slide, 10.8, 0.36, 2.1, 0.3, 'REFER & EARN  |  %d / 2' % n, size=10, color=MUTED, align=PP_ALIGN.RIGHT)


def insight(slide, x, y, w, h, accent, title, body):
    rect(slide, x, y, w, h)
    strip = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y + 0.12), Inches(0.06), Inches(h - 0.24))
    strip.fill.solid(); strip.fill.fore_color.rgb = accent; strip.line.fill.background()
    text(slide, x + 0.16, y + 0.07, w - 0.25, 0.3, title, size=13, bold=True, color=accent)
    text(slide, x + 0.16, y + 0.38, w - 0.25, h - 0.42, body, size=12, color=TXT, spacing=3)


def style_chart(chart, color, label_fmt, size=9):
    chart.has_legend = False
    chart.has_title = False
    chart.font.size = Pt(size)
    chart.font.name = FONT
    chart.font.color.rgb = MUTED
    plot = chart.plots[0]
    plot.gap_width = 45
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format = label_fmt
    dl.number_format_is_linked = False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size = Pt(size)
    dl.font.color.rgb = TXT
    ser = plot.series[0]
    ser.format.fill.solid()
    ser.format.fill.fore_color.rgb = color
    chart.value_axis.visible = False
    chart.value_axis.has_major_gridlines = False
    chart.value_axis.tick_label_position = XL_TICK_LABEL_POSITION.NONE
    chart.value_axis.format.line.fill.background()
    chart.category_axis.format.line.color.rgb = BORDER
    chart.category_axis.tick_labels.font.size = Pt(size)
    chart.category_axis.tick_labels.font.color.rgb = MUTED


# ===================== SLIDE 1 =====================
s1 = prs.slides.add_slide(blank)
bg(s1)
header(s1, 'Programme Performance & Customer Value',
       'Live data from ClickHouse  |  Programme start 16 Jan 2026  to  5 Oct 2026', 1)

kpis = [
    ('99,796', 'Participants', TEAL),
    ('28,407', 'Buyers  (28.5% of participants)', VIOLET),
    ('17.1M', 'Points issued', AMBER),
    ('10.9M', 'Points redeemed  (64%)', TEAL),
    ('₹71.9 cr', 'Redeemed-purchase revenue', VIOLET),
    ('1.52%', 'Effective discount', ROSE),
]
cw, gap, x0 = 1.98, 0.1, 0.5
for i, (v, l, c) in enumerate(kpis):
    x = x0 + i * (cw + gap)
    rect(s1, x, 1.3, cw, 1.15)
    text(s1, x, 1.38, cw, 0.55, v, size=24, bold=True, color=c, align=PP_ALIGN.CENTER)
    text(s1, x + 0.05, 1.95, cw - 0.1, 0.45, l, size=10, color=MUTED, align=PP_ALIGN.CENTER)

# insights 2x2 (left)
iw, ih = 3.95, 2.1
insight(s1, 0.5, 2.7, iw, ih, TEAL, '1  Repeat buyers drive revenue', [
    [('56% of buyers, ~84% of revenue ', {'bold': True}), ('(₹60.1 cr of ₹71.9 cr).', {})],
    'Avg purchase ₹53.9k vs ₹15.8k for new (3.4x).',
    'Redeem rate 70% vs 60%; discount cost 1.31% vs 2.55%.',
    [('Action: ', {'bold': True, 'color': TEAL}), ('push the 2nd purchase.', {})],
])
insight(s1, 4.55, 2.7, iw, ih, AMBER, '2  Points sit with non-buyers', [
    [('~9.8M of 17.1M points (57%) ', {'bold': True}), ('are held by the 71.5% of participants with no matched purchase.', {})],
    'Large unredeemed liability and the biggest conversion opportunity.',
    [('Action: ', {'bold': True, 'color': AMBER}), ('"points waiting" nudges, expiry rule.', {})],
])
insight(s1, 0.5, 4.95, iw, ih, ROSE, '3  Retention cliff after month 1', [
    [('Only 12-23% return in month 1 ', {'bold': True}), ('(Jan 22.7%, Feb-Aug 12-16%), then flat at ~9-20%.', {})],
    'About 1 in 5 buyers sticks around.',
    [('Action: ', {'bold': True, 'color': ROSE}), ('day 20-30 re-engagement offer after first purchase.', {})],
])
insight(s1, 4.55, 4.95, iw, ih, VIOLET, '4  Bigger baskets, lighter redemption', [
    [('First-month avg purchase: ', {}), ('₹11.5k (Jan) to ₹30-35k (May-Aug).', {'bold': True})],
    'Points redeemed vs revenue: 4.2% (Jan) to 0.15% (Jun).',
    'Retained users also grow: Jan cohort ₹11.5k to ₹27.6k by month 8.',
])

# retention chart (right)
rect(s1, 8.7, 2.7, 4.13, 4.35)
text(s1, 8.85, 2.78, 3.9, 0.3, 'Month-1 retention by cohort', size=13, bold=True)
text(s1, 8.85, 3.08, 3.9, 0.3, '% of first-purchase cohort buying again next month', size=9.5, color=MUTED)
cd = CategoryChartData()
cd.categories = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug']
cd.add_series('Month-1 retention %', (22.7, 14.3, 12.0, 13.0, 15.5, 12.8, 16.4, 13.1))
gf = s1.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(8.8), Inches(3.4), Inches(3.95), Inches(3.55), cd)
style_chart(gf.chart, TEAL, '0.0"%"')
gf.chart.value_axis.maximum_scale = 28
gf.chart.value_axis.minimum_scale = 0

# ===================== SLIDE 2 =====================
s2 = prs.slides.add_slide(blank)
bg(s2)
header(s2, 'Audience, Growth & Next Actions',
       'Who the customers are, where growth stands, what to fix and what to do next', 2)

# col 1: charts
rect(s2, 0.5, 1.3, 4.1, 2.8)
text(s2, 0.65, 1.36, 3.8, 0.3, 'Top districts (% of customers)', size=13, bold=True)
cd = CategoryChartData()
cd.categories = ['Thiruvananthapuram', 'Palakkad', 'Ernakulam', 'Kannur', 'Malappuram', 'Kozhikode']
cd.add_series('Share %', (3.1, 3.5, 3.6, 6.9, 11.7, 54.3))
gf = s2.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.55), Inches(1.65), Inches(4.0), Inches(2.4), cd)
style_chart(gf.chart, VIOLET, '0.0"%"')
gf.chart.value_axis.maximum_scale = 68
gf.chart.value_axis.minimum_scale = 0

rect(s2, 0.5, 4.25, 4.1, 2.8)
text(s2, 0.65, 4.31, 3.8, 0.3, 'Age distribution (% of users)', size=13, bold=True)
cd = CategoryChartData()
cd.categories = ['0-16', '17-20', '21-25', '26-30', '31-40', '41-50', '51+']
cd.add_series('Share %', (4.6, 20.1, 27.3, 16.6, 15.3, 9.2, 6.8))
gf = s2.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.55), Inches(4.6), Inches(4.0), Inches(2.4), cd)
style_chart(gf.chart, AMBER, '0.0"%"')
gf.chart.value_axis.maximum_scale = 34
gf.chart.value_axis.minimum_scale = 0

# col 2: audience & growth
insight(s2, 4.8, 1.3, 4.05, 2.15, TEAL, 'Sign-ups: spike, then campaign-led', [
    'Jan-Feb = ~61% of all sign-ups (17 Jan alone: 9,527).',
    'May low ~48/day; Aug rebound ~203/day (4x) with campaigns.',
    [('Oct ~120/day and drifting down ', {'bold': True}), ('(last 3 days 100-117).', {})],
])
insight(s2, 4.8, 3.6, 4.05, 1.7, VIOLET, 'Young, North-Kerala audience', [
    '17-30 yrs = ~64% of users; 21-25 is the largest band (27.3%).',
    'Kozhikode + Malappuram + Kannur = ~73%; out-of-state ~0.5%.',
])
insight(s2, 4.8, 5.45, 4.05, 1.6, AMBER, 'Expansion opportunity', [
    'Ernakulam (3.6%) and Thiruvananthapuram (3.1%) are under-penetrated.',
    [('Action: ', {'bold': True, 'color': AMBER}), ('pilot a campaign in both districts.', {})],
])

# col 3: data quality + quick wins
insight(s2, 9.05, 1.3, 3.78, 3.0, ROSE, 'Data quality issues', [
    [('Default DOBs: ', {'bold': True}), ('Jan = 21% of birthdays, 23% of anniversaries (expected ~8%); May also high.', {})],
    [('Missing sales: ', {'bold': True}), ('22-29 Sep gap; Sep cohort partial, so Sep/Oct conversion is understated.', {})],
    [('Jan gap: ', {'bold': True}), ('19-22 Jan sign-ups only 2-9/day.', {})],
    [('Age: ', {'bold': True}), ('2,865 users in 0-10 band (invalid DOBs).', {})],
])
insight(s2, 9.05, 4.45, 3.78, 2.6, TEAL, 'Quick wins', [
    '1.  Oct birthday offers (7,286) and anniversary offers (2,327), excluding placeholder dates.',
    '2.  Day 20-30 re-engagement for every new buyer.',
    '3.  Target 9.8M points held by non-buyers.',
    '4.  Pilot Ernakulam and Thiruvananthapuram.',
])

out = r'C:\Users\SHAHIN\Desktop\Refer & Earn Dashboard\Refer_Earn_Insights.pptx'
prs.save(out)
print('saved', out)
