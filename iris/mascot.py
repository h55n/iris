"""Hand-drawn plants for Iris: empty states, section accents, the 'meeting
saved' moment. No characters. A turbulence filter wobbles every stroke so
the lines look inked by hand; colour sits slightly off the outline like
marker. Moods keep the old names: happy = sprout, sleep = tucked-in seedling
at night, celebrate = in bloom. The flower uses the theme accent."""

INK = "var(--ink,#3b2a20)"
LEAF, LEAF2, LEAF3 = "#5f9a4a", "#86b968", "#3f7a3a"
POT, POT2, SOIL = "#c9683f", "#e0865a", "#6b4a35"

def _s(w=2.6):
    return f'stroke="{INK}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"'

def _leaf(x, y, dx, dy, fill, droop=0):
    # leaf from (x,y) pointing (dx,dy); drawn as a pointed almond with a vein
    mx, my = x + dx / 2, y + dy / 2
    nx, ny = -dy * 0.32, dx * 0.32
    d = f"M{x} {y} Q{mx+nx} {my+ny+droop} {x+dx} {y+dy+droop} Q{mx-nx} {my-ny+droop} {x} {y}z"
    return (f'<path d="{d}" fill="{fill}" transform="translate(1.5 1.5)" opacity=".9"/>'
            f'<path d="{d}" fill="none" {_s(2.2)}/>'
            f'<path d="M{x} {y} L{x+dx*0.7} {y+dy*0.7+droop*0.7}" fill="none" stroke="{INK}" stroke-width="1.3" stroke-linecap="round" opacity=".6"/>')

def _pot(cx=100, top=150):
    return (f'<path d="M{cx-26} {top} L{cx-21} {top+36} Q{cx} {top+42} {cx+21} {top+36} L{cx+26} {top}z" fill="{POT}" transform="translate(2 2)"/>'
            f'<path d="M{cx-26} {top} L{cx-21} {top+36} Q{cx} {top+42} {cx+21} {top+36} L{cx+26} {top}z" fill="none" {_s(2.8)}/>'
            f'<path d="M{cx-30} {top-8} h60 v10 h-60z" fill="{POT2}" {_s(2.8)}/>'
            f'<path d="M{cx-14} {top+14} q6 3 12 0" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" opacity=".5"/>'
            f'<path d="M{cx-24} {top-8} q24 -9 48 0" fill="{SOIL}" {_s(2)}/>')

def _sparkles(c):
    return ''.join(f'<path d="M{x} {y-5} v10 M{x-5} {y} h10" stroke="{c}" stroke-width="2.6" stroke-linecap="round"/>'
                   for x, y in ((38, 60), (166, 52), (28, 120), (176, 118)))

def mascot(size: int = 96, mood: str = "happy", plants: int = 0) -> str:
    stem = f'<path d="M100 142 Q98 110 101 {84 if mood!="celebrate" else 70}" fill="none" stroke="{LEAF3}" stroke-width="4.4" stroke-linecap="round"/>' \
           f'<path d="M100 142 Q98 110 101 {84 if mood!="celebrate" else 70}" fill="none" {_s(1.4)} opacity=".5"/>'
    body = ''
    if mood == "sleep":
        # leaves folded down for the night, tiny moon and stars
        body = (_leaf(100, 108, -30, 4, LEAF2, 16) + _leaf(100, 96, 30, 2, LEAF, 16)
                + _leaf(101, 86, -3, -12, LEAF2)
                + f'<path d="M158 44 a14 14 0 1 0 12 20 a11 11 0 1 1 -12 -20z" fill="#f2cf63" {_s(2.2)}/>'
                + f'<path d="M40 52 l2 5 5 2 -5 2 -2 5 -2 -5 -5 -2 5 -2z M60 84 l1.5 3.5 3.5 1.5 -3.5 1.5 -1.5 3.5 -1.5 -3.5 -3.5 -1.5 3.5 -1.5z" fill="#f2cf63"/>')
    elif mood == "celebrate":
        body = (_leaf(100, 118, -40, -12, LEAF2) + _leaf(100, 104, 42, -14, LEAF)
                + _leaf(100, 92, -30, -18, LEAF)
                + ''.join(f'<ellipse cx="101" cy="52" rx="9" ry="17" fill="var(--accent)" transform="rotate({a} 101 70) translate(1.5 1.5)" opacity=".9"/>'
                          f'<ellipse cx="101" cy="52" rx="9" ry="17" fill="none" {_s(2.4)} transform="rotate({a} 101 70)"/>'
                          for a in (0, 72, 144, 216, 288))
                + f'<circle cx="101" cy="70" r="9" fill="#f2cf63" {_s(2.6)}/>'
                + _sparkles("var(--accent)"))
    else:
        body = (_leaf(100, 112, -38, -10, LEAF2) + _leaf(100, 98, 38, -16, LEAF)
                + _leaf(101, 84, -6, -26, LEAF2) + _leaf(101, 84, 26, -18, LEAF))
    return (f'<svg class=mascot width="{size}" height="{size}" viewBox="0 0 200 200" fill="none" aria-hidden="true">'
            '<defs><filter id="wob" x="-5%" y="-5%" width="110%" height="110%">'
            '<feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="4" result="n"/>'
            '<feDisplacementMap in="SourceGraphic" in2="n" scale="3.2"/></filter></defs>'
            '<g filter="url(#wob)">'
            f'<path d="M52 196 Q100 191 148 196" {_s(2.2)} opacity=".35"/>'
            + stem + body + _pot() + '</g></svg>')
