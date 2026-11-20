def srgb_to_lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def rel_lum(hex_str):
    hex_str = hex_str.lstrip('#')
    r, g, b = [int(hex_str[i:i+2], 16) for i in (0, 2, 4)]
    return 0.2126 * srgb_to_lin(r) + 0.7152 * srgb_to_lin(g) + 0.0722 * srgb_to_lin(b)

def contrast(c1, c2):
    l1 = rel_lum(c1)
    l2 = rel_lum(c2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)

pairs = [
    ('Dark Canvas', '#f8fafc', '#090d16', 'Dark Primary Text on Canvas'),
    ('Dark Canvas', '#cbd5e1', '#090d16', 'Dark Secondary Text on Canvas'),
    ('Dark Canvas', '#94a3b8', '#090d16', 'Dark Muted Text on Canvas'),
    ('Dark Surface', '#f8fafc', '#0f172a', 'Dark Primary Text on Surface'),
    ('Dark Surface', '#cbd5e1', '#0f172a', 'Dark Secondary Text on Surface'),
    ('Dark Surface', '#94a3b8', '#0f172a', 'Dark Muted Text on Surface'),
    ('Dark Surface Elevated', '#f8fafc', '#1e293b', 'Dark Primary Text on Card/Modal'),
    ('Dark Brand Accent', '#38bdf8', '#0f172a', 'Dark Brand Signal (700) on Surface'),
    ('Dark Status Online', '#34d399', '#0f172a', 'Dark Online Text on Surface'),
    ('Dark Status Warning', '#fbbf24', '#0f172a', 'Dark Warning Text on Surface'),
    ('Dark Status Critical', '#f87171', '#0f172a', 'Dark Critical Text on Surface'),
    ('Light Canvas', '#0f172a', '#f8fafc', 'Light Primary Text on Canvas'),
    ('Light Canvas', '#334155', '#f8fafc', 'Light Secondary Text on Canvas'),
    ('Light Canvas', '#64748b', '#f8fafc', 'Light Muted Text on Canvas'),
    ('Light Surface', '#0f172a', '#ffffff', 'Light Primary Text on Surface'),
    ('Light Surface', '#334155', '#ffffff', 'Light Secondary Text on Surface'),
    ('Light Surface', '#64748b', '#ffffff', 'Light Muted Text on Surface'),
    ('Light Brand Accent', '#0284c7', '#ffffff', 'Light Brand 500 on Surface'),
    ('Light Brand Accent', '#0369a1', '#ffffff', 'Light Brand 600 on Surface'),
    ('Light Status Online', '#065f46', '#ffffff', 'Light Online Text on Surface'),
    ('Light Status Warning', '#92400e', '#ffffff', 'Light Warning Text on Surface'),
    ('Light Status Critical', '#991b1b', '#ffffff', 'Light Critical Text on Surface'),
    ('Focus Ring', '#0284c7', '#ffffff', 'Focus border against light surface'),
    ('Focus Ring Dark', '#38bdf8', '#0f172a', 'Focus border against dark surface')
]

print(f"{'UI Element / Token Pair':<38} | {'FG':<7} | {'BG':<7} | {'Ratio':<7} | {'WCAG Level':<15}")
print('-' * 82)
for p, fg, bg, desc in pairs:
    r = contrast(fg, bg)
    passed = 'PASS (AAA)' if r >= 7.0 else ('PASS (AA)' if r >= 4.5 else ('PASS (3:1 Non-text)' if r >= 3.0 else 'FAIL'))
    print(f"{desc:<38} | {fg:<7} | {bg:<7} | {r:>5.2f}:1 | {passed:<15}")
