
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

pseudo_classes = [
    # Logical Combinations
    'matches',
    'not',

    # Linguistic Pseudo-classes
    'dir',
    'lang',

    # Location Pseudo-classes
    'any-link',
    'link',
    'visited',
    'local-link',
    'target',
    'scope',

    # User Action Pseudo-classes
    'hover',
    'active',
    'focus',
    'drop',

    # Time-dimensional Pseudo-classes
    'current',
    'past',
    'future',

    # The Input Pseudo-classes
    'enabled',
    'disabled',
    'read-only',
    'read-write',
    'placeholder-shown',
    'checked',
    'indeterminate',
    'valid',
    'invalid',
    'in-range',
    'out-of-range',
    'required',
    'optional',
    'user-error',

    # Tree-Structural pseudo-classes
    'root',
    'empty',
    'blank',
    'nth-child',
    'nth-last-child',
    'first-child',
    'last-child',
    'only-child',
    'nth-of-type',
    'nth-last-of-type',
    'first-of-type',
    'last-of-type',
    'only-of-type',
    'nth-match',
    'nth-last-match',

    # Grid-Structural Selectors
    'nth-column',
    'nth-last-column',

    # Pseudo-elements
    'first-line',
    'first-letter',
    'before',
    'after',

    # Non-standard
    'selection',
]