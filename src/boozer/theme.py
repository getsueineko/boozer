"""The phosphor-green CRT palette, as plain hex strings.

boozer.tcss hardcodes the same values for the stylesheet (Textual CSS
files don't support Python-side interpolation), so this module is the
single source of truth only for colors used in *inline Rich markup*
from Python (the ✓/✕ marks in DetailPanel). If the palette changes,
update both places — see the comment at the top of boozer.tcss.
"""

BG = "#020402"
ROW_ALT_BG = "#071c0a"
GREEN_BRIGHT = "#39ff6a"
GREEN = "#2ecc71"
GREEN_DIM = "#1a7a3c"
CHEVRON = "#175c30"
AMBER = "#ffb000"

# Selection highlight stays within the green family (bright green on
# near-black) rather than an out-of-theme accent colour.
HILITE_BG = GREEN_BRIGHT
HILITE_FG = "#02150a"
