"""Pure CSS Color 4 to the fixed host's opaque sRGB color-input value.

The locked browser's initial input.value is six-digit sRGB even when alpha or
colorspace attributes survive sanitizing. Color conversion uses CSS Color 4
sections 7-11 and the W3C sample conversion equations/matrices, not Canvas.
Named/hex/rgb/hsl channels reuse the existing pure Mermaid color provider.
"""
from __future__ import annotations

import colorsys
import math
import re
import struct

from ....config.colors import channels
from ....config.color_names import COLOR_NAMES
from ....model.flowchart import MermaidError


_NUMBER = re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:e[+-]?[0-9]+)?\Z', re.I)
_XYZ_TO_RGB = ((12831/3959, -329/214, -1974/3959),
               (-851781/878810, 1648619/878810, 36519/878810),
               (705/12673, -2585/12673, 705/667))
_RGB_TO_XYZ = ((506752/1228815, 87881/245763, 12673/70218),
               (87098/409605, 175762/245763, 12673/175545),
               (7918/409605, 87881/737289, 1001167/1053270))
_P3_TO_XYZ = ((608311/1250200, 189793/714400, 198249/1000160),
              (35783/156275, 247089/357200, 198249/2500400),
              (0., 32229/714400, 5220557/5000800))
_A98_TO_XYZ = ((573536/994567, 263643/1420810, 187206/994567),
               (591459/1989134, 6239551/9945670, 374412/4972835),
               (53769/1989134, 351524/4972835, 4929758/4972835))
_PROPHOTO_TO_XYZ = ((.7977666449006423, .13518129740053308, .03134773412839220),
                    (.2880748288194013, .711835234241873, .00008993693872564),
                    (0., 0., .8251046025104602))
_REC2020_TO_XYZ = ((63426534/99577255, 20160776/139408157, 47086771/278816314),
                   (26158966/99577255, 472592308/697040785, 8267143/139408157),
                   (0., 19567812/697040785, 295819943/278816314))
_D50_TO_D65 = ((.955473421488075, -.02309845494876471, .06325924320057072),
               (-.0283697093338637, 1.0099953980813041, .021041441191917323),
               (.012314014864481998, -.020507649298898964, 1.330365926242124))
_OKLAB_TO_LMS = ((1., .3963377773761749, .2158037573099136),
                 (1., -.1055613458156586, -.0638541728258133),
                 (1., -.0894841775298119, -1.2914855480194092))
_LMS_TO_XYZ = ((1.2268798758459243, -.5578149944602171, .2813910456659647),
               (-.0405757452148008, 1.112286803280317, -.0717110580655164),
               (-.0763729366746601, -.4214933324022432, 1.5869240198367816))

# Chromium 156.0.8078.76 uses these Skia D50/ICC coordinates, not the
# high-precision W3C D65 shortcut. Its DEPS pins Skia a65b5cc03a5131808aec172085b7074fc66625b9.
_HOST_SRGB_D50 = tuple(tuple(v/65536 for v in row) for row in
                       ((0x6FA2, 0x6299, 0x24A0), (0x38F5, 0xB785, 0x0F84), (0x0390, 0x18DA, 0xB6CF)))
_HOST_P3_D50 = ((.515102, .291965, .157153),
                (.241182, .692236, .0665819),
                (-.00104941, .0418818, .784378))
_HOST_REC2020_D50 = ((.673459, .165661, .125100),
                     (.279033, .675338, .0456288),
                     (-.00193139, .0299794, .797162))
_HOST_SRGB_TRANSFER = (2.4, 1/1.055, .055/1.055, 1/12.92, .04045, 0., 0.)
_HOST_REC2020_TRANSFER = (2.22222, .909672, .0903276, .222222, .0812429, 0., 0.)


def _float32(value):
    return struct.unpack('f', struct.pack('f', value))[0]


def _host_matrix(matrix, vector):
    # skcms_ext::Matrix3x3_apply operates on float operands and intermediates.
    vector = tuple(_float32(v) for v in vector)
    return tuple(_float32(_float32(_float32(_float32(row[0])*vector[0]) +
                                  _float32(_float32(row[1])*vector[1])) +
                          _float32(_float32(row[2])*vector[2])) for row in matrix)


def _host_inverse(matrix):
    # skcms matrix inversion uses double intermediates and float coefficients.
    a, b, c = matrix[0]; d, e, f = matrix[1]; g, h, i = matrix[2]
    determinant = a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g)
    cofactors = ((e*i-f*h, c*h-b*i, b*f-c*e),
                 (f*g-d*i, a*i-c*g, c*d-a*f),
                 (d*h-e*g, b*g-a*h, a*e-b*d))
    return tuple(tuple(_float32(v/determinant) for v in row) for row in cofactors)


def _host_transfer(fn, value):
    g, a, b, c, d, e, f = (_float32(v) for v in fn)
    value = _float32(value); sign = -1. if value < 0 else 1.; x = abs(value)
    if x <= d:
        return _float32(sign*_float32(_float32(c*x)+f))
    base = max(0., _float32(_float32(a*x)+b))
    return _float32(sign*_float32(_float32(base if g == 1 else math.pow(base,g))+e))


def _host_inverse_transfer(fn):
    # General parametric inverse and white-endpoint correction, as used by
    # skcms_ext (std::pow float version, not skcms's approximate exp/log path).
    g, a, b, c, d, e, f = (_float32(v) for v in fn)
    split = _float32(_float32(c*d)+f)
    ic = _float32(1/c) if split > 0 else 0.
    iff = _float32(-f/c) if split > 0 else 0.
    ig = _float32(1/g); ia = _float32(math.pow(a,-g)); ib = _float32(-ia*e)
    ie = _float32(-b/a)
    if _float32(_float32(ia*split)+ib) < 0:
        ib = _float32(-ia*split)
    white = _host_transfer(fn,1.)
    if white < split:
        iff = _float32(1-_float32(ic*white))
    else:
        ie = _float32(1-_float32(math.pow(_float32(_float32(ia*white)+ib),ig)))
    return ig, ia, ib, ic, split, ie, iff


def _host_predefined(values, matrix, transfer=None):
    linear = tuple(_host_transfer(transfer,v) for v in values) if transfer else values
    xyz = _host_matrix(matrix,linear)
    linear_rgb = _host_matrix(_host_inverse(_HOST_SRGB_D50),xyz)
    inverse = _host_inverse_transfer(_HOST_SRGB_TRANSFER)
    return tuple(_host_transfer(inverse,v) for v in linear_rgb)


def _clamp(value, low=0., high=1.):
    return max(low, min(high, value))


def _matrix(matrix, vector):
    return tuple(sum(a*b for a, b in zip(row, vector)) for row in matrix)


def _power(value, exponent):
    return math.copysign(abs(value)**exponent, value)


def _linear(value):
    return value/12.92 if abs(value) <= .04045 else math.copysign(((abs(value)+.055)/1.055)**2.4, value)


def _gamma(value):
    return 12.92*value if abs(value) <= .0031308 else math.copysign(1.055*abs(value)**(1/2.4)-.055, value)


def _component(token, percent=1.):
    if token == 'none':
        return 0.
    number = token[:-1] if token.endswith('%') else token
    if not _NUMBER.fullmatch(number):
        raise ValueError('Invalid CSS color number')
    value = float(number)*percent/100 if token.endswith('%') else float(number)
    if not math.isfinite(value):
        raise ValueError('Nonfinite CSS color number')
    return value


def _hue(token):
    for unit, factor in (('grad', .9), ('turn', 360.), ('rad', 180/math.pi), ('deg', 1.)):
        if token.endswith(unit):
            return (_component(token[:-len(unit)])*factor) % 360
    if token.endswith('%'):
        raise ValueError('Hue does not accept percentages')
    return _component(token) % 360


def _parts(body, *, legacy=False):
    """Validate separators/alpha independently from Khroma's permissive split."""
    if ',' in body:
        if not legacy or '/' in body:
            raise ValueError('Invalid legacy color syntax')
        values = [v.strip() for v in body.split(',')]
        if len(values) not in (3, 4) or any(not v or len(v.split()) != 1 or v=='none' for v in values):
            raise ValueError('Invalid color component count')
        if len(values) == 4:
            _component(values.pop())
        return values, True
    values = body.split('/')
    if len(values) > 2:
        raise ValueError('Invalid color alpha')
    if len(values) == 2:
        _component(values[1].strip())
    values = values[0].split()
    if len(values) != 3:
        raise ValueError('Invalid color component count')
    return values, False


def _basic(function, body):
    parts, legacy = _parts(body, legacy=True)
    if function.startswith('rgb'):
        if legacy and len({p.endswith('%') for p in parts}) != 1:
            raise ValueError('Mixed legacy RGB units')
        values = [_clamp(_component(p, 255.), 0., 255.) for p in parts]
        normalized = 'rgb(' + ','.join(str(v) for v in values) + ')'
    else:
        if legacy and not all(p.endswith('%') for p in parts[1:]):
            raise ValueError('Legacy HSL requires percentages')
        h = _hue(parts[0]); s, l = (_clamp(_component(p, 100.), 0., 100.) for p in parts[1:])
        normalized = f'hsl({h},{s}%,{l}%)'
    return channels(normalized)[:3]


def _from_xyz(xyz):
    return tuple(_gamma(value) for value in _matrix(_XYZ_TO_RGB, xyz))


def _predefined(body):
    match = re.fullmatch(r'([a-z0-9-]+)\s+(.+)', body)
    if not match:
        raise ValueError('Missing predefined color space')
    space = match[1]; parts, _ = _parts(match[2])
    values = tuple(_component(p) for p in parts)
    if space == 'srgb':
        return values
    if space == 'srgb-linear':
        return tuple(_gamma(v) for v in values)
    if space in {'xyz', 'xyz-d65'}:
        return _from_xyz(values)
    if space == 'xyz-d50':
        return _from_xyz(_matrix(_D50_TO_D65, values))
    if space in {'display-p3', 'display-p3-linear'}:
        return _host_predefined(values, _HOST_P3_D50,
                                None if space.endswith('-linear') else _HOST_SRGB_TRANSFER)
    elif space == 'a98-rgb':
        xyz = _matrix(_A98_TO_XYZ, tuple(_power(v, 563/256) for v in values))
    elif space == 'prophoto-rgb':
        linear = tuple(v/16 if abs(v) <= 16/512 else _power(v, 1.8) for v in values)
        xyz = _matrix(_D50_TO_D65, _matrix(_PROPHOTO_TO_XYZ, linear))
    elif space == 'rec2020':
        # Fixed host retains the BT.2020 piecewise inverse OETF. The newer
        # W3C sample's BT.1886 gamma 2.4 has measurably different values.
        return _host_predefined(values, _HOST_REC2020_D50, _HOST_REC2020_TRANSFER)
    else:
        raise ValueError('Unknown predefined color space')
    return _from_xyz(xyz)


def _lab(function, body):
    parts, _ = _parts(body)
    oklab = function.startswith('ok')
    lightness = _clamp(_component(parts[0], 1. if oklab else 100.), 0., 1. if oklab else 100.)
    if function.endswith('lch'):
        chroma = max(0., _component(parts[1], .4 if oklab else 150.))
        angle = math.radians(_hue(parts[2]))
        a, b = chroma*math.cos(angle), chroma*math.sin(angle)
    else:
        a, b = (_component(p, .4 if oklab else 125.) for p in parts[1:])
    if oklab:
        lms = _matrix(_OKLAB_TO_LMS, (lightness, a, b))
        return _from_xyz(_matrix(_LMS_TO_XYZ, tuple(v**3 for v in lms)))
    kappa = 24389/27; epsilon = 216/24389
    fy = (lightness+16)/116; fx = fy+a/500; fz = fy-b/200
    xyz = (fx**3 if fx**3 > epsilon else (116*fx-16)/kappa,
           fy**3 if lightness > kappa*epsilon else lightness/kappa,
           fz**3 if fz**3 > epsilon else (116*fz-16)/kappa)
    white = (.3457/.3585, 1., (1-.3457-.3585)/.3585)
    return _from_xyz(_matrix(_D50_TO_D65, tuple(v*w for v, w in zip(xyz, white))))


def _parse(value):
    # CSS comments are whitespace tokens, not concatenated identifiers.
    value = re.sub(r'/\*.*?\*/', ' ', value, flags=re.S).strip().lower()
    if value in {'aqua', 'cyan'}:
        return channels('#00ffff')[:3]
    if value == 'currentcolor':
        # A color-well value has no inherited color to resolve against.
        return (0., 0., 0.)
    if value in COLOR_NAMES and value != 'cyanaqua' or re.fullmatch(r'#[0-9a-f]{3,4}|#[0-9a-f]{6}(?:[0-9a-f]{2})?', value):
        return channels(value)[:3]
    match = re.fullmatch(r'([a-z][a-z0-9-]*)\((.*)\)', value, re.S)
    if not match:
        raise ValueError('Invalid CSS color')
    function, body = match.groups()
    if function in {'rgb', 'rgba', 'hsl', 'hsla'}:
        return _basic(function, body)
    if function == 'hwb':
        parts, _ = _parts(body)
        hue = _hue(parts[0]); white, black = (_clamp(_component(p, 100.)/100) for p in parts[1:])
        if white+black >= 1:
            return (white/(white+black),)*3
        rgb = colorsys.hsv_to_rgb(hue/360, 1., 1.)
        return tuple(v*(1-white-black)+white for v in rgb)
    if function == 'color':
        return _predefined(body)
    if function in {'lab', 'lch', 'oklab', 'oklch'}:
        return _lab(function, body)
    raise ValueError('Invalid CSS color function')


def normalize_color_value(value):
    """HTML color-input initial value in the verified host: opaque #rrggbb.

    Alpha is validated as part of the CSS value but is not composited against
    a background: HTML's opaque color well discards it. Invalid CSS falls back
    to black. Out-of-sRGB coordinates are converted before final channel clamp.
    """
    try:
        rgb = _parse(value)
        if not all(math.isfinite(v) for v in rgb):
            raise ValueError('Nonfinite converted color')
        # Matrix/Khroma arithmetic can place an exact half just below the
        # boundary (e.g. achromatic hsl(0 0% 50%)). Remove that roundoff only.
        return '#' + ''.join(format(math.floor(_clamp(v)*255+.5+1e-12), '02x') for v in rgb)
    except (ValueError, OverflowError, MermaidError):
        return '#000000'


def is_valid_css_color(value):
    """Validate the supported absolute CSS Color 4 syntax without black fallback.

    The returned boolean does not authorize resources, preserve alpha for
    painting, or resolve contextual system/relative colors against a host.
    """
    if not isinstance(value, str):
        return False
    try:
        return all(math.isfinite(v) for v in _parse(value))
    except (ValueError, OverflowError, MermaidError):
        return False
