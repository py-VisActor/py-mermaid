"""Native paint/text style resolution, without a browser CSS runtime."""
from .flowchart import apply_declarations, css_size, parse_css, parse_declarations, resolve_style, resolve_inline_svg_style

__all__=['apply_declarations','css_size','parse_css','parse_declarations','resolve_style','resolve_inline_svg_style']
