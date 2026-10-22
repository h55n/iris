"""Hand-drawn plants for Iris: empty states, section accents, the 'meeting
saved' moment. No characters. The art is loose black line work with flat
spot colour printed slightly off the outline, like a risograph sketch: every
shape is an ink stroke (drawn twice, a little scratchy) over a fill that sits
a few pixels to the side. A turbulence filter wobbles the strokes. Moods keep
the old names: happy = sprout, sleep = seedling at night, celebrate = in
bloom. The flower uses the theme accent. Parts carry classes so the page CSS
can grow them in order: stem draws up, leaves unfurl, the bloom pops."""

INK = "var(--ink,#1f2430)"
LEAF, LEAF2 = "#9fd3a0", "#c7b8ee"      # sage and lavender spot colours
POT, SOIL, SUN, FIRE, SKY = "#ff9d8a", "#7a5a46", "#ffd75e", "#ff6a3d", "#2f6bff"

def _ink(d, w=2.6):
    # two passes: a bold line and a thin, shifted echo for the scratchy look
    return (f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{w*0.4:.2f}" stroke-linecap="round" transform="translate(.9 -.8)" opacity=".55"/>')

def _fill(d, color, dx=4, dy=3, op=1):
    return f'<path d="{d}" fill="{color}" transform="translate({dx} {dy})" opacity="{op}"/>'

def _leaf(x, y, dx, dy, color, droop=0, cls="", delay=0.0):
    mx, my = x + dx / 2, y + dy / 2
    nx, ny = -dy * 0.34, dx * 0.34
    d = f"M{x} {y} Q{mx+nx:.1f} {my+ny+droop:.1f} {x+dx} {y+dy+droop} Q{mx-nx:.1f} {my-ny+droop:.1f} {x} {y}"
    vein = f"M{x} {y} L{x+dx*0.72:.1f} {y+dy*0.72+droop*0.72:.1f}"
    return (f'<g class="leaf {cls}" style="transform-origin:{x}px {y}px;--d:{delay}s">'
            + _fill(d + "z", color) + _ink(d, 2.4) + _ink(vein, 1.4) + '</g>')

def _pot(cx=100, top=150):
    body = f"M{cx-26} {top} L{cx-21} {top+36} Q{cx} {top+42} {cx+21} {top+36} L{cx+25} {top-1}"
    rim = f"M{cx-31} {top-9} L{cx+31} {top-8} M{cx-30} {top-9} L{cx-29} {top+1} M{cx+31} {top-8} L{cx+30} {top+2}"
    return (_fill(f"M{cx-28} {top-6} h58 L{cx+23} {top+39} Q{cx} {top+45} {cx-19} {top+39}z", POT, 5, 4)
            + _ink(body, 2.8) + _ink(rim, 2.6)
            + f'<path d="M{cx-24} {top-8} q24 -8 48 0" fill="{SOIL}" stroke="{INK}" stroke-width="2" stroke-linecap="round"/>')

def _ground():
    # hatch lines fanning out under the pot, plus a tuft of grass
    lines = "".join(f"M{x} 196 L{x+dx} 205" for x, dx in ((44, -10), (62, -5), (80, -2), (100, 0), (120, 3), (138, 6), (156, 11)))
    return (_ink("M34 196 Q100 190 166 196", 2.2) + _ink(lines, 1.4)
            + _ink("M160 196 q-2 -9 -6 -13 M160 196 q2 -10 7 -12 M160 196 q0 -8 1 -14", 1.8))

def _dashes(c, pts):
    # short radiating burst marks, like the sparks off a campfire sketch
    return "".join(f'<path d="M{x} {y} l{dx} {dy}" stroke="{c}" stroke-width="2.8" stroke-linecap="round"/>' for x, y, dx, dy in pts)

def _stem(top):
    d = f"M100 144 Q97 112 101 {top}"
    return ('<g class="stem">'
            f'<path pathLength="1" d="{d}" fill="none" stroke="{INK}" stroke-width="3.2" stroke-linecap="round"/>'
            f'<path pathLength="1" d="M103 144 Q100 114 104 {top+2}" fill="none" stroke="{INK}" stroke-width="1.2" stroke-linecap="round" opacity=".5"/>'
            '</g>')

def mascot(size: int = 96, mood: str = "happy", plants: int = 0) -> str:
    kind = mood if mood in ("sleep", "celebrate") else "happy"
    if mood == "sleep":
        top = 86
        body = (_leaf(100, 110, -32, 4, LEAF2, 18, "l1", .25) + _leaf(100, 98, 32, 2, LEAF, 18, "l2", .35)
                + _leaf(101, 88, -3, -12, LEAF, 0, "l3", .45)
                # moon: yellow spot colour offset from its ink outline
                + _fill("M158 42 a14 14 0 1 0 12 20 a11 11 0 1 1 -12 -20z", SUN)
                + _ink("M158 42 a14 14 0 1 0 12 20 a11 11 0 1 1 -12 -20z", 2.2)
                + _dashes(SKY, ((40, 54, 0, 8), (36, 58, 8, 0), (62, 82, 0, 6), (59, 85, 6, 0))))
    elif mood == "celebrate":
        top = 72
        petals = ''.join(
            f'<g transform="rotate({a} 101 70)">'
            + _fill('M101 52 C92 44 94 28 101 22 C108 28 110 44 101 52z', "var(--accent)", 2, 3, .9)
            + _ink('M101 52 C92 44 94 28 101 22 C108 28 110 44 101 52z', 2.3) + '</g>'
            for a in (0, 72, 144, 216, 288))
        body = (_leaf(99, 130, -46, -8, LEAF, 0, "l1", .3) + _leaf(100, 118, 46, -10, LEAF2, 0, "l2", .4)
                + '<g class=bloom>' + petals
                + f'<circle cx="101" cy="70" r="9" fill="{FIRE}" stroke="{INK}" stroke-width="2.4"/>'
                + '</g>'
                + '<g class=sparkles>' + _dashes(FIRE, ((42, 44, -7, -5), (36, 56, -9, 0), (46, 66, -7, 5),
                                                      (160, 44, 7, -5), (166, 56, 9, 0), (156, 66, 7, 5))) + '</g>')
    else:
        top = 84
        body = (_leaf(100, 114, -40, -10, LEAF, 0, "l1", .3) + _leaf(100, 100, 40, -16, LEAF2, 0, "l2", .4)
                + _leaf(101, 86, -8, -28, LEAF2, 0, "l3", .5) + _leaf(101, 86, 26, -20, LEAF, 0, "l4", .6)
                + _dashes(SKY, ((152, 62, 6, -4), (156, 72, 8, 0), (152, 82, 6, 4))))
    return (f'<svg class="mascot {kind}" width="{size}" height="{size}" viewBox="0 0 200 210" fill="none" aria-hidden="true">'
            '<defs><filter id="wob" x="-5%" y="-5%" width="110%" height="110%">'
            '<feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="2" seed="7" result="n"/>'
            '<feDisplacementMap in="SourceGraphic" in2="n" scale="2.6"/></filter></defs>'
            '<g filter="url(#wob)">' + _ground() + _stem(top) + body + _pot() + '</g></svg>')
