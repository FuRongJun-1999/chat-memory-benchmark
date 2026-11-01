"""Render reproducible SVG/PNG result sheets from public aggregate data only."""
import argparse
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'charts/2026-11-01/data.json'
W, H = 1800, 2200
C = {'paper': '#f4f8ff', 'ink': '#102b52', 'muted': '#506783', 'blue': '#2961f4',
     'teal': '#007f91', 'line': '#d6e3f2', 'white': '#ffffff'}
AUTHORS = {'qwen-rag': '嵌入召回＋重排，对照流程', 'dsh-soul': '糖霜Official',
           'archeon-hotcold': '原无奇变 · 按方案复现', 'dsh-rofm': '鄙人乃路人甲 · 测试阈值',
           'digital-life-core': '温水', 'seekmemory': 'BangBang在coding · 开启 Dream',
           'surfcore': '玛露Marrow'}
GROUPS = [
    ('基本信息与偏好', [
        ('用户的基本信息', '用户明确说过的资料，能否记对？'),
        ('生日', '能否记对生日，不乱补年份？'),
        ('职业', '能否记住工作信息？'),
        ('偏好', '能否记住喜欢什么，不随意扩大？'),
        ('称呼条件', '能否在约定的场合使用称呼？'),
        ('带条件或期限的偏好和边界', '能否记住限制的条件和期限？')]),
    ('约定、关系与线索', [
        ('约定和欠账', '谁答应了什么，哪些事还没完成？'),
        ('没说完要跟进的事', '能否记住待办，不编后续结果？'),
        ('第三方事实', '别人的事，会不会记到用户头上？'),
        ('助手自己说过的话', '能否区分自己的建议和用户的承诺？'),
        ('分散的线索', '分散在不同聊天里的信息，能否拼起来？')]),
    ('改口、变化与矛盾', [
        ('真实变化', '事实变了，能否使用新信息？'),
        ('改口', '用户改了主意，是否仍沿用旧安排？'),
        ('纠错', '明确纠正过的信息，还会不会记错？'),
        ('没解释的矛盾', '能否保留冲突，不擅自编原因？'),
        ('相似事件', '相近的人、地点和事件，能否分清？')]),
    ('计划、假设与现实', [
        ('计划假设梦转述猜测', '能否区分不同叙述与已经发生的事实？'),
        ('计划', '打算做，是否被记成已经做完？'),
        ('假设', '能否保留“如果”的前提？'),
        ('转述', '能否记住消息来源，不冒充亲身经历？'),
        ('共同编的故事', '共同创作的情节，会不会当成现实？')]),
    ('时间、保密与边界', [
        ('时间约定', '约定了什么时候，能否记对？'),
        ('相对日期', '能否按当时日期理解“昨天”“下周”？'),
        ('时间题', '能否记住时长、日期和先后关系？'),
        ('资料不足', '不知道的部分，能否不编造？'),
        ('敏感的事', '能否守住信息的使用限制？'),
        ('边界', '能否遵守用户明确设定的界限？')]),
]


def read_data():
    data = json.loads(DATA.read_text(encoding='utf-8'))
    topics = [t for _, group in GROUPS for t, _ in group]
    assert len(topics) == len(set(topics)) == 27
    assert data['comparison_count'] == 687 and len(data['systems']) == 7
    for s in data['systems'].values():
        assert s['total'] == 687 and 0 <= s['passed'] <= s['total']
        assert set(s['topics']) == set(topics)
        for t in s['topics'].values():
            assert [c['days'] for c in t['cells']] == [0, 3, 15, 45]
            assert sum(c['passed'] for c in t['cells']) == t['passed']
            assert sum(c['total'] for c in t['cells']) == t['total']
            assert all(0 <= c['passed'] <= c['total'] for c in t['cells'])
    return data


class Sheet:
    def __init__(self, title, subtitle, page):
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
                      '<style>text{font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif;font-variant-numeric:tabular-nums}</style>']
        self.rect(0, 0, W, H, C['paper'])
        self.rect(80, 72, 1640, 8, C['blue'])
        self.text(80, 173, title, 68, bold=True)
        self.text(84, 234, subtitle, 31, C['muted'])
        self.line(80, 2090, 1720, 2090)
        self.text(80, 2140, '大肥鱼 · 记忆系统评测', 30, bold=True)
        self.text(80, 2179, 'github.com/Ornn8/memory-system-benchmark', 23, C['muted'])
        self.text(1720, 2141, f'{page} / 7', 30, C['muted'], anchor='end')
        self.text(1720, 2179, '2026-11-01 · 固定版本实验', 23, C['muted'], anchor='end')

    def text(self, x, y, text, size=30, color=None, bold=False, anchor='start'):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color or C["ink"]}" font-weight="{700 if bold else 400}" text-anchor="{anchor}">{html.escape(str(text))}</text>')

    def rect(self, x, y, w, h, color, radius=0):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{color}"/>')

    def line(self, x1, y1, x2, y2, color=None):
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color or C["line"]}" stroke-width="2"/>')

    def save(self, path):
        path.write_text('\n'.join(self.parts) + '\n</svg>\n', encoding='utf-8', newline='\n')


def overall(data, order, destination):
    s = Sheet('同样的 687 题，谁记得更好？', '固定六个人物 · 最长半年 · 每天约两轮 · 所有系统使用相同题目集合', 2)
    s.text(80, 337, '整题通过数 / 共同已答题数', 36, bold=True)
    s.text(1720, 337, '柱长 = 通过率', 28, C['muted'], anchor='end')
    x0, width = 550, 860
    for tick in [0, 25, 50, 75, 100]:
        x = x0 + width * tick / 100
        s.line(x, 420, x, 1775)
        s.text(x, 393, str(tick) + '%', 25, C['muted'], anchor='middle')
    for i, key in enumerate(order):
        entry = data['systems'][key]
        y = 500 + i * 185
        color = C['teal'] if key == 'qwen-rag' else C['blue']
        s.text(80, y, entry['label'], 43, bold=True)
        s.text(82, y + 43, AUTHORS[key], 26, C['muted'])
        ratio = entry['passed'] / entry['total']
        s.rect(x0, y - 46, width, 66, '#e5edf8', 8)
        s.rect(x0, y - 46, width * ratio, 66, color, 8)
        s.text(1720, y + 1, f'{entry["passed"]} / {entry["total"]}', 46, color, bold=True, anchor='end')
        s.text(1720, y + 44, f'{ratio:.1%}', 28, C['muted'], anchor='end')
    s.rect(80, 1835, 1640, 212, '#e6eefb', 12)
    s.text(110, 1889, '本次共同题目中，六个项目／方案的通过量均未超过 Qwen 检索对照。', 33, bold=True)
    s.text(110, 1944, 'ROFM 未答的 27 题从七路一起排除；不是把未答题判成错误。', 28, C['muted'])
    s.text(110, 1990, 'dsh-world 仅完成旧卷部分试跑，不进入本图。结论仅适用于本次配置。', 28, C['muted'])
    s.save(destination / '02-overall.svg')


def costs(data, order, destination):
    s = Sheet('这轮测试调用，花了多少钱？', '单位：人民币元 · 只计当前成绩对应批次 · 按官方单价折算已记录用量', 1)
    s.text(80, 337, '维护、检索与作答：本批次合计', 36, bold=True)
    s.text(1720, 337, '完成量不同，不作为等量成本排名', 27, C['muted'], anchor='end')
    x0, width = 550, 860
    maximum = max(v['cost']['cny'] for v in data['systems'].values())
    axis_max = (int(maximum / 10) + 1) * 10
    for tick in range(0, axis_max + 1, 10):
        x = x0 + width * tick / axis_max
        s.line(x, 420, x, 1775)
        s.text(x, 393, str(tick), 25, C['muted'], anchor='middle')
    for i, key in enumerate(order):
        entry = data['systems'][key]
        cost = entry['cost']
        y = 500 + i * 185
        color = C['teal'] if key == 'qwen-rag' else C['blue']
        s.text(80, y, entry['label'], 43, bold=True)
        suffix = ' · 中断保留' if key == 'dsh-rofm' else ''
        s.text(82, y + 43, f'{cost["completed_answers"]} 题已完成{suffix}', 27, C['muted'])
        s.rect(x0, y - 46, width, 66, '#e5edf8', 8)
        s.rect(x0, y - 46, width * cost['cny'] / axis_max, 66, color, 8)
        s.text(1720, y + 3, f'¥ {cost["cny"]:.2f}', 59, color, bold=True, anchor='end')
    s.rect(80, 1835, 1640, 212, '#e6eefb', 12)
    s.text(110, 1880, '包括本批次已记录的失败尝试；不含此前撤回的试跑、重跑费用。', 29, bold=True)
    s.text(110, 1925, '按实际缓存命中计价；沿用已有状态和缓存，不是从零建库成本或订阅账单。', 27, C['muted'])
    s.text(110, 1970, 'DeepSeek 命中 / 未命中 / 输出：0.02 / 1 / 4 元 / 百万 token。', 26, C['muted'])
    s.text(110, 2013, 'Qwen 嵌入与重排：各 0.5 元 / 百万 token。价格核对：2026-11-01。', 26, C['muted'])
    s.save(destination / '01-cost.svg')


def heat_color(ratio):
    start, end = (239, 245, 254), (174, 204, 248)
    return '#' + ''.join(f'{round(a + (b-a)*ratio):02x}' for a, b in zip(start, end))


def topic_sheet(data, order, title, group, page, destination):
    s = Sheet(title, '每格显示：通过题数 / 该格实际题数；时间从相关事实最后一次提及开始算', page)
    x0, col = 250, 210
    s.text(82, 311, '提问间隔', 27, C['muted'])
    for i, key in enumerate(order):
        label = data['systems'][key]['label']
        s.text(x0 + i * col + col / 2, 311, label, 25 if len(label) > 12 else 28,
               C['teal'] if key == 'qwen-rag' else C['ink'], bold=True, anchor='middle')
    s.line(80, 330, 1720, 330)
    block = 269 if len(group) == 6 else 316
    for j, (topic, description) in enumerate(group):
        top = 378 + j * block
        s.text(82, top, f'{topic}  ·  {description}', 31, bold=True)
        for row in range(5):
            y = top + 53 + row * 39
            is_total = row == 4
            label = ['当天', '3 天', '15 天', '45 天', '四档合计'][row]
            s.text(95, y, label, 27, C['ink'] if is_total else C['muted'], bold=is_total)
            for i, key in enumerate(order):
                t = data['systems'][key]['topics'][topic]
                counts = t if is_total else t['cells'][row]
                p, n = counts['passed'], counts['total']
                x = x0 + i * col
                s.rect(x + 4, y - 29, col - 8, 35, '#dbe6f5' if is_total else heat_color(p / n if n else 0), 4)
                s.text(x + col / 2, y, f'{p} / {n}' if n else '未测', 29, bold=is_total, anchor='middle')
        if j < len(group) - 1:
            s.line(80, top + block - 26, 1720, top + block - 26)
    s.text(80, 2026, '颜色越深，通过率越高。考点互有重叠，不能把各考点题数相加。', 26, C['muted'])
    s.text(80, 2067, '基于七路共同的 687 题；ROFM 中断后，部分时间格不足原定十组。', 26, C['muted'])
    s.save(destination / f'{page:02d}-topics.svg')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--channel', help='Installed Chromium browser, for example msedge or chrome')
    parser.add_argument('--svg-only', action='store_true')
    args = parser.parse_args()
    data = read_data()
    order = sorted(data['systems'], key=lambda k: -data['systems'][k]['passed'])
    destination = DATA.parent
    costs(data, order, destination)
    overall(data, order, destination)
    for page, (title, group) in enumerate(GROUPS, 3):
        topic_sheet(data, order, title, group, page, destination)
    if args.svg_only:
        return
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        try:
            page = browser.new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
            checks = []
            for svg in sorted(destination.glob('*.svg')):
                page.set_content('<html><head><meta charset="utf-8"></head><body style="margin:0">' + svg.read_text(encoding='utf-8') + '</body></html>')
                page.evaluate('document.fonts.ready')
                bounds = page.evaluate('''() => {
                    const boxes = [...document.querySelectorAll('svg text')].map(e => {
                        const b = e.getBBox(); return {text: e.textContent, x:b.x, y:b.y, w:b.width, h:b.height};
                    });
                    const outside = boxes.filter(b => b.x < 0 || b.y < 0 || b.x+b.w > 1800 || b.y+b.h > 2200);
                    const overlaps=[];
                    for(let i=0;i<boxes.length;i++) for(let j=i+1;j<boxes.length;j++) {
                        const a=boxes[i],b=boxes[j];
                        if(Math.min(a.x+a.w,b.x+b.w)-Math.max(a.x,b.x)>2 && Math.min(a.y+a.h,b.y+b.h)-Math.max(a.y,b.y)>2)
                            overlaps.push([a.text,b.text]);
                    }
                    return {text_count: boxes.length, outside, overlaps};
                }''')
                assert not bounds['outside'], (svg.name, bounds['outside'])
                assert not bounds['overlaps'], (svg.name, bounds['overlaps'])
                target = svg.with_suffix('.png')
                page.screenshot(path=str(target), full_page=False)
                checks.append({'image': target.name, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                               'width': W, 'height': H, **bounds})
                print('Rendered', target.name)
            check_path = ROOT / 'outputs/chart-layout-check.json'
            check_path.parent.mkdir(exist_ok=True)
            check_path.write_text(json.dumps(checks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        finally:
            browser.close()


if __name__ == '__main__':
    main()
