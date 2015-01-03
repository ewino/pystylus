from collections import namedtuple

units = [
    'em', 'ex', 'ch', 'rem',  # relative lengths
    'vw', 'vh', 'vmin', 'vmax'  # relative viewport-percentage lengths
    'cm', 'mm', 'in', 'pt', 'pc', 'px'  # absolute lengths
    'deg', 'grad', 'rad', 'turn'  # angles
    's', 'ms'  # times
    'Hz', 'kHz'  # frequencies
    'dpi', 'dpcm', 'dppx', 'x'  # resolutions
    '%'  # percentage type
    'fr'  # grid-layout (http://www.w3.org/TR/css3-grid-layout/)
]

Color = namedtuple('Color', ['r', 'g', 'b', 'a'])