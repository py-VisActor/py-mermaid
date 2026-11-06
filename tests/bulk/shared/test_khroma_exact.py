"""Independent fixed npm Khroma 2.1.0 results, never loaded in production.

Oracle literals are captured from the pinned installed distribution via a
standard workflow Run. Source colors/channels/methods/utils define expectations.
"""
import json
import math
from pathlib import Path
import unittest

INPUTS = [
    {'op':'adjust','args':[color,changes]}
    for color in ('hsl(120, 80%, 100%)','hsl(270, 65%, 0%)','hsl(230, 0%, 50%)','hsla(-30, 70%, 100%, .3)','#ececff','red','transparent')
    for changes in ({'l':-10},{'s':-40,'l':-10},{'h':-400},{'h':0,'s':0,'a':0},{'r':.25},{'a':-.1})
] + [
    {'op':op,'args':[color]}
    for color in ('hsl(240,100%,100%)','hsl(270,65%,0%)','hsl(-30,100%,50%)','hsl(-750,100%,50%)','hsl(120grad,25%,75%)','hsl(.5turn,100%,50%)','rgb(1.25, 2.5, 3.75)','rgba(12.25, 180.5, 230.75, .333333333333)','rgb(10%,20%,30%)','transparent','rebeccapurple','white','black','#abcd')
    for op in ('invert','isDark','channels','lighten','darken')
] + [
    {'op':'rgba','args':args} for args in ([0,0,0],[255,0,255,1],[1.25,2.5,3.75,1],[-5,300,4,.2],[4,5,6,0],['hsl(280,70%,100%)',.5],['red',1],['rgba(1,2,3,.4)',.25])
] + [
    {'op':'chain','args':[color,steps]} for color,steps in (
       ('hsl(120,80%,100%)',[['darken',10],['darken',10]]),
       ('hsl(270,65%,0%)',[['lighten',10],['lighten',10]]),
       ('hsl(204,100%,70%)',[['invert'],['darken',10]]),
       ('hsla(-30,70%,100%,.3)',[['adjust',{'l':-20}],['invert'],['lighten',5]]))
] + [
    {'op':'lighten','args':[color,delta]} for color in ('RED','#fff','hsl(-30,0%,50%)','hsl(240,100%,100%)') for delta in (0,-200,200)
]

ORACLE = ['hsl(120, 80%, 90%)', 'hsl(120, 40%, 90%)', 'hsl(-280, 80%, 100%)', 'hsl(120, 80%, 100%)', '#ffffff', 'hsla(120, 80%, 100%, 0.9)', 'hsl(270, 65%, 0%)', 'hsl(270, 25%, 0%)', 'hsl(-130, 65%, 0%)', 'hsl(270, 65%, 0%)', 'rgb(0.25, 0, 0)', 'hsla(270, 65%, 0%, 0.9)', 'hsl(230, 0%, 40%)', 'hsl(230, 0%, 40%)', 'hsl(-170, 0%, 50%)', 'hsl(230, 0%, 50%)', 'rgb(127.75, 127.5, 127.5)', 'hsla(230, 0%, 50%, 0.9)', 'hsla(-30, 70%, 90%, 0.3)', 'hsla(-30, 30%, 90%, 0.3)', 'hsla(-70, 70%, 100%, 0.3)', 'hsla(-30, 70%, 100%, .3)', 'rgba(255, 255, 255, 0.3)', 'hsla(-30, 70%, 100%, 0.19999999999999998)', 'hsl(240, 100%, 86.2745098039%)', 'hsl(240, 60%, 86.2745098039%)', 'hsl(-160, 100%, 96.2745098039%)', '#ececff', 'rgb(236.25, 236, 255)', 'rgba(236, 236, 255, 0.9)', 'hsl(0, 100%, 40%)', 'hsl(0, 60%, 40%)', 'hsl(-40, 100%, 50%)', '#ff0000', '#ff0000', 'rgba(255, 0, 0, 0.9)', 'hsla(0, 0%, 0%, 0)', 'hsla(0, 0%, 0%, 0)', 'hsla(-40, 0%, 0%, 0)', '#00000000', 'rgba(0.25, 0, 0, 0)', 'rgba(0, 0, 0, 0)', '#000000', False, [1, 1, 1, 1], 'hsl(240, 100%, NaN%)', 'hsl(240, 100%, NaN%)', '#ffffff', True, [0, 0, 0, 1], 'hsl(270, 65%, NaN%)', 'hsl(270, 65%, NaN%)', 'rgb(0, 255, 127.5)', True, [1, 0, 0.49999999999999956, 1], 'hsl(-30, 100%, NaN%)', 'hsl(-30, 100%, NaN%)', 'rgb(0, 255, 127.5)', True, [1, 0, 0.49999999999999956, 1], 'hsl(-30, 100%, NaN%)', 'hsl(-30, 100%, NaN%)', 'rgb(73.3125, 47.8125, 79.6875)', False, [0.7125, 0.8125, 0.6875, 1], 'hsl(108, 25%, NaN%)', 'hsl(108, 25%, NaN%)', 'rgb(255, 0, 0)', False, [0, 0.9999999999999998, 1, 1], 'hsl(180, 100%, NaN%)', 'hsl(180, 100%, NaN%)', 'rgb(253.75, 252.5, 251.25)', True, [0.004901960784313725, 0.00980392156862745, 0.014705882352941176, 1], 'hsl(210, 50%, NaN%)', 'hsl(210, 50%, NaN%)', 'rgba(242.75, 74.5, 24.25, 0.3333333333)', True, [0.04803921568627451, 0.707843137254902, 0.9049019607843137, 0.333333333333], 'hsla(193.7986270023, 89.9176954733%, NaN%, 0.333333333333)', 'hsla(193.7986270023, 89.9176954733%, NaN%, 0.333333333333)', 'rgb(229.5, 204, 178.5)', True, [0.1, 0.2, 0.3, 1], 'hsl(210, 50%, NaN%)', 'hsl(210, 50%, NaN%)', 'rgba(255, 255, 255, 0)', True, [0, 0, 0, 0], 'hsla(0, 0%, NaN%, 0)', 'hsla(0, 0%, NaN%, 0)', '#99cc66', True, [0.4, 0.2, 0.6, 1], 'hsl(270, 50%, NaN%)', 'hsl(270, 50%, NaN%)', '#000000', False, [1, 1, 1, 1], 'hsl(0, 0%, NaN%)', 'hsl(0, 0%, NaN%)', '#ffffff', True, [0, 0, 0, 1], 'hsl(0, 0%, NaN%)', 'hsl(0, 0%, NaN%)', 'rgba(85, 68, 51, 0.8666666667)', True, [0.6666666666666666, 0.7333333333333333, 0.8, 0.8666666666666667], 'hsla(210, 25%, NaN%, 0.8666666666666667)', 'hsla(210, 25%, NaN%, 0.8666666666666667)', '#000000', '#ff00ff', 'rgb(1.25, 2.5, 3.75)', 'rgba(0, 255, 4, 0.2)', 'rgba(4, 5, 6, 0)', 'hsla(280, 70%, 100%, 0.5)', '#ff0000', 'rgba(1, 2, 3, 0.25)', 'hsl(120, 80%, 80%)', 'hsl(270, 65%, 20%)', 'hsl(24, 100%, 20%)', 'hsla(150, 70%, 25%, 0.3)', '#ff0000', 'hsl(0, 100%, 0%)', 'hsl(0, 100%, 100%)', '#fff', 'hsl(0, 0%, 0%)', '#fff', 'hsl(-30,0%,50%)', 'hsl(-30, 0%, 0%)', 'hsl(-30, 0%, 100%)', 'hsl(240,100%,100%)', 'hsl(240, 100%, 0%)', 'hsl(240,100%,100%)']


def actual(row):
    from py_mermaid.config import colors
    if row['op']=='chain':
        value,steps=row['args']
        for name,*args in steps:value=getattr(colors,name)(value,*args)
        return value
    return getattr(colors,row['op'])(*row['args'])


class FixedKhromaExact(unittest.TestCase):
    def test_adjust_preserves_authored_hsl_and_css_noop(self):self.check_ops({'adjust'})
    def test_invert_keeps_fractional_rgb(self):self.check_ops({'invert'})
    def test_darkness_matches_fixed_linear_threshold(self):self.check_ops({'isDark'})
    def test_public_normalized_rgba_contract(self):self.check_ops({'channels'})
    def test_omitted_lighten_and_darken_preserve_nan(self):self.check_ops({'lighten','darken'},omitted=True)
    def test_lighten_clamps_but_returns_original_if_unchanged(self):self.check_ops({'lighten'},omitted=False)
    def test_rgba_uses_source_hex_rgb_hsl_serialization(self):self.check_ops({'rgba'})
    def test_chained_derived_palette_retains_intent(self):self.check_ops({'chain'})
    def test_mkborder_is_fixed_two_channel_adjust(self):
        from py_mermaid.config.colors import mkBorder
        self.assertEqual(mkBorder('hsl(240,100%,100%)'),'hsl(240, 60%, 90%)')
        self.assertEqual(mkBorder('hsl(240,100%,0%)',True),'hsl(240, 60%, 10%)')
    def test_js_truthiness_includes_empty_collections(self):
        from py_mermaid.config.colors import truthy
        for value in ({},[],(),set(),frozenset(),'0'):self.assertTrue(truthy(value))
        for value in (None,False,0,0.,'',float('nan')):self.assertFalse(truthy(value))
    def test_mixed_rgb_hsl_axes_are_rejected(self):
        from py_mermaid.config.colors import adjust
        from py_mermaid import MermaidError
        with self.assertRaises(MermaidError):adjust('red',{'h':1,'r':1})
    def test_all_fixed_named_colors_match_independent_oracle(self):
        from py_mermaid.config.colors import channels
        for name,expected in NAMED_ORACLE.items():
            with self.subTest(name=name):
                for a,b in zip(channels(name),expected):self.assertAlmostEqual(a,b,places=12)
    def check_ops(self,ops,omitted=None):
        self.assertEqual(len(ORACLE),len(INPUTS))
        for row,expected in zip(INPUTS,ORACLE):
            if row['op'] not in ops:continue
            if omitted is not None and (len(row['args'])==1)!=omitted:continue
            with self.subTest(row=row):
                got=actual(row)
                if isinstance(expected,list):
                    for a,b in zip(got,expected):self.assertAlmostEqual(a,b,places=12)
                else:self.assertEqual(got,expected)

NAMED_ORACLE = {'aliceblue': [0.9411764705882353, 0.9725490196078431, 1, 1], 'antiquewhite': [0.9803921568627451, 0.9215686274509803, 0.8431372549019608, 1], 'aqua': [0, 1, 1, 1], 'aquamarine': [0.4980392156862745, 1, 0.8313725490196079, 1], 'azure': [0.9411764705882353, 1, 1, 1], 'beige': [0.9607843137254902, 0.9607843137254902, 0.8627450980392157, 1], 'bisque': [1, 0.8941176470588236, 0.7686274509803922, 1], 'black': [0, 0, 0, 1], 'blanchedalmond': [1, 0.9215686274509803, 0.803921568627451, 1], 'blue': [0, 0, 1, 1], 'blueviolet': [0.5411764705882353, 0.16862745098039217, 0.8862745098039215, 1], 'brown': [0.6470588235294118, 0.16470588235294117, 0.16470588235294117, 1], 'burlywood': [0.8705882352941177, 0.7215686274509804, 0.5294117647058824, 1], 'cadetblue': [0.37254901960784315, 0.6196078431372549, 0.6274509803921569, 1], 'chartreuse': [0.4980392156862745, 1, 0, 1], 'chocolate': [0.8235294117647058, 0.4117647058823529, 0.11764705882352941, 1], 'coral': [1, 0.4980392156862745, 0.3137254901960784, 1], 'cornflowerblue': [0.39215686274509803, 0.5843137254901961, 0.9294117647058824, 1], 'cornsilk': [1, 0.9725490196078431, 0.8627450980392157, 1], 'crimson': [0.8627450980392157, 0.0784313725490196, 0.23529411764705882, 1], 'cyanaqua': [0, 1, 1, 1], 'darkblue': [0, 0, 0.5450980392156862, 1], 'darkcyan': [0, 0.5450980392156862, 0.5450980392156862, 1], 'darkgoldenrod': [0.7215686274509804, 0.5254901960784314, 0.043137254901960784, 1], 'darkgray': [0.6627450980392157, 0.6627450980392157, 0.6627450980392157, 1], 'darkgreen': [0, 0.39215686274509803, 0, 1], 'darkgrey': [0.6627450980392157, 0.6627450980392157, 0.6627450980392157, 1], 'darkkhaki': [0.7411764705882353, 0.7176470588235294, 0.4196078431372549, 1], 'darkmagenta': [0.5450980392156862, 0, 0.5450980392156862, 1], 'darkolivegreen': [0.3333333333333333, 0.4196078431372549, 0.1843137254901961, 1], 'darkorange': [1, 0.5490196078431373, 0, 1], 'darkorchid': [0.6, 0.19607843137254902, 0.8, 1], 'darkred': [0.5450980392156862, 0, 0, 1], 'darksalmon': [0.9137254901960784, 0.5882352941176471, 0.47843137254901963, 1], 'darkseagreen': [0.5607843137254902, 0.7372549019607844, 0.5607843137254902, 1], 'darkslateblue': [0.2823529411764706, 0.23921568627450981, 0.5450980392156862, 1], 'darkslategray': [0.1843137254901961, 0.30980392156862746, 0.30980392156862746, 1], 'darkslategrey': [0.1843137254901961, 0.30980392156862746, 0.30980392156862746, 1], 'darkturquoise': [0, 0.807843137254902, 0.8196078431372549, 1], 'darkviolet': [0.5803921568627451, 0, 0.8274509803921568, 1], 'deeppink': [1, 0.0784313725490196, 0.5764705882352941, 1], 'deepskyblue': [0, 0.7490196078431373, 1, 1], 'dimgray': [0.4117647058823529, 0.4117647058823529, 0.4117647058823529, 1], 'dimgrey': [0.4117647058823529, 0.4117647058823529, 0.4117647058823529, 1], 'dodgerblue': [0.11764705882352941, 0.5647058823529412, 1, 1], 'firebrick': [0.6980392156862745, 0.13333333333333333, 0.13333333333333333, 1], 'floralwhite': [1, 0.9803921568627451, 0.9411764705882353, 1], 'forestgreen': [0.13333333333333333, 0.5450980392156862, 0.13333333333333333, 1], 'fuchsia': [1, 0, 1, 1], 'gainsboro': [0.8627450980392157, 0.8627450980392157, 0.8627450980392157, 1], 'ghostwhite': [0.9725490196078431, 0.9725490196078431, 1, 1], 'gold': [1, 0.8431372549019608, 0, 1], 'goldenrod': [0.8549019607843137, 0.6470588235294118, 0.12549019607843137, 1], 'gray': [0.5019607843137255, 0.5019607843137255, 0.5019607843137255, 1], 'green': [0, 0.5019607843137255, 0, 1], 'greenyellow': [0.6784313725490196, 1, 0.1843137254901961, 1], 'grey': [0.5019607843137255, 0.5019607843137255, 0.5019607843137255, 1], 'honeydew': [0.9411764705882353, 1, 0.9411764705882353, 1], 'hotpink': [1, 0.4117647058823529, 0.7058823529411765, 1], 'indianred': [0.803921568627451, 0.3607843137254902, 0.3607843137254902, 1], 'indigo': [0.29411764705882354, 0, 0.5098039215686274, 1], 'ivory': [1, 1, 0.9411764705882353, 1], 'khaki': [0.9411764705882353, 0.9019607843137255, 0.5490196078431373, 1], 'lavender': [0.9019607843137255, 0.9019607843137255, 0.9803921568627451, 1], 'lavenderblush': [1, 0.9411764705882353, 0.9607843137254902, 1], 'lawngreen': [0.48627450980392156, 0.9882352941176471, 0, 1], 'lemonchiffon': [1, 0.9803921568627451, 0.803921568627451, 1], 'lightblue': [0.6784313725490196, 0.8470588235294118, 0.9019607843137255, 1], 'lightcoral': [0.9411764705882353, 0.5019607843137255, 0.5019607843137255, 1], 'lightcyan': [0.8784313725490196, 1, 1, 1], 'lightgoldenrodyellow': [0.9803921568627451, 0.9803921568627451, 0.8235294117647058, 1], 'lightgray': [0.8274509803921568, 0.8274509803921568, 0.8274509803921568, 1], 'lightgreen': [0.5647058823529412, 0.9333333333333333, 0.5647058823529412, 1], 'lightgrey': [0.8274509803921568, 0.8274509803921568, 0.8274509803921568, 1], 'lightpink': [1, 0.7137254901960784, 0.7568627450980392, 1], 'lightsalmon': [1, 0.6274509803921569, 0.47843137254901963, 1], 'lightseagreen': [0.12549019607843137, 0.6980392156862745, 0.6666666666666666, 1], 'lightskyblue': [0.5294117647058824, 0.807843137254902, 0.9803921568627451, 1], 'lightslategray': [0.4666666666666667, 0.5333333333333333, 0.6, 1], 'lightslategrey': [0.4666666666666667, 0.5333333333333333, 0.6, 1], 'lightsteelblue': [0.6901960784313725, 0.7686274509803922, 0.8705882352941177, 1], 'lightyellow': [1, 1, 0.8784313725490196, 1], 'lime': [0, 1, 0, 1], 'limegreen': [0.19607843137254902, 0.803921568627451, 0.19607843137254902, 1], 'linen': [0.9803921568627451, 0.9411764705882353, 0.9019607843137255, 1], 'magenta': [1, 0, 1, 1], 'maroon': [0.5019607843137255, 0, 0, 1], 'mediumaquamarine': [0.4, 0.803921568627451, 0.6666666666666666, 1], 'mediumblue': [0, 0, 0.803921568627451, 1], 'mediumorchid': [0.7294117647058823, 0.3333333333333333, 0.8274509803921568, 1], 'mediumpurple': [0.5764705882352941, 0.4392156862745098, 0.8588235294117647, 1], 'mediumseagreen': [0.23529411764705882, 0.7019607843137254, 0.44313725490196076, 1], 'mediumslateblue': [0.4823529411764706, 0.40784313725490196, 0.9333333333333333, 1], 'mediumspringgreen': [0, 0.9803921568627451, 0.6039215686274509, 1], 'mediumturquoise': [0.2823529411764706, 0.8196078431372549, 0.8, 1], 'mediumvioletred': [0.7803921568627451, 0.08235294117647059, 0.5215686274509804, 1], 'midnightblue': [0.09803921568627451, 0.09803921568627451, 0.4392156862745098, 1], 'mintcream': [0.9607843137254902, 1, 0.9803921568627451, 1], 'mistyrose': [1, 0.8941176470588236, 0.8823529411764706, 1], 'moccasin': [1, 0.8941176470588236, 0.7098039215686275, 1], 'navajowhite': [1, 0.8705882352941177, 0.6784313725490196, 1], 'navy': [0, 0, 0.5019607843137255, 1], 'oldlace': [0.9921568627450981, 0.9607843137254902, 0.9019607843137255, 1], 'olive': [0.5019607843137255, 0.5019607843137255, 0, 1], 'olivedrab': [0.4196078431372549, 0.5568627450980392, 0.13725490196078433, 1], 'orange': [1, 0.6470588235294118, 0, 1], 'orangered': [1, 0.27058823529411763, 0, 1], 'orchid': [0.8549019607843137, 0.4392156862745098, 0.8392156862745098, 1], 'palegoldenrod': [0.9333333333333333, 0.9098039215686274, 0.6666666666666666, 1], 'palegreen': [0.596078431372549, 0.984313725490196, 0.596078431372549, 1], 'paleturquoise': [0.6862745098039216, 0.9333333333333333, 0.9333333333333333, 1], 'palevioletred': [0.8588235294117647, 0.4392156862745098, 0.5764705882352941, 1], 'papayawhip': [1, 0.9372549019607843, 0.8352941176470589, 1], 'peachpuff': [1, 0.8549019607843137, 0.7254901960784313, 1], 'peru': [0.803921568627451, 0.5215686274509804, 0.24705882352941178, 1], 'pink': [1, 0.7529411764705882, 0.796078431372549, 1], 'plum': [0.8666666666666667, 0.6274509803921569, 0.8666666666666667, 1], 'powderblue': [0.6901960784313725, 0.8784313725490196, 0.9019607843137255, 1], 'purple': [0.5019607843137255, 0, 0.5019607843137255, 1], 'rebeccapurple': [0.4, 0.2, 0.6, 1], 'red': [1, 0, 0, 1], 'rosybrown': [0.7372549019607844, 0.5607843137254902, 0.5607843137254902, 1], 'royalblue': [0.2549019607843137, 0.4117647058823529, 0.8823529411764706, 1], 'saddlebrown': [0.5450980392156862, 0.27058823529411763, 0.07450980392156863, 1], 'salmon': [0.9803921568627451, 0.5019607843137255, 0.4470588235294118, 1], 'sandybrown': [0.9568627450980393, 0.6431372549019608, 0.3764705882352941, 1], 'seagreen': [0.1803921568627451, 0.5450980392156862, 0.3411764705882353, 1], 'seashell': [1, 0.9607843137254902, 0.9333333333333333, 1], 'sienna': [0.6274509803921569, 0.3215686274509804, 0.17647058823529413, 1], 'silver': [0.7529411764705882, 0.7529411764705882, 0.7529411764705882, 1], 'skyblue': [0.5294117647058824, 0.807843137254902, 0.9215686274509803, 1], 'slateblue': [0.41568627450980394, 0.35294117647058826, 0.803921568627451, 1], 'slategray': [0.4392156862745098, 0.5019607843137255, 0.5647058823529412, 1], 'slategrey': [0.4392156862745098, 0.5019607843137255, 0.5647058823529412, 1], 'snow': [1, 0.9803921568627451, 0.9803921568627451, 1], 'springgreen': [0, 1, 0.4980392156862745, 1], 'tan': [0.8235294117647058, 0.7058823529411765, 0.5490196078431373, 1], 'teal': [0, 0.5019607843137255, 0.5019607843137255, 1], 'thistle': [0.8470588235294118, 0.7490196078431373, 0.8470588235294118, 1], 'transparent': [0, 0, 0, 0], 'turquoise': [0.25098039215686274, 0.8784313725490196, 0.8156862745098039, 1], 'violet': [0.9333333333333333, 0.5098039215686274, 0.9333333333333333, 1], 'wheat': [0.9607843137254902, 0.8705882352941177, 0.7019607843137254, 1], 'white': [1, 1, 1, 1], 'whitesmoke': [0.9607843137254902, 0.9607843137254902, 0.9607843137254902, 1], 'yellow': [1, 1, 0, 1], 'yellowgreen': [0.6039215686274509, 0.803921568627451, 0.19607843137254902, 1]}

if __name__=='__main__':
    import sys
    if '--capture-oracle' in sys.argv:
        import subprocess
        root=Path(__file__).resolve().parents[3]
        script="""import * as k from './.local/f011-oracle/node_modules/khroma/dist/index.js';
import Color from './.local/f011-oracle/node_modules/khroma/dist/color/index.js';
const rows=JSON.parse(process.argv[1]);
function rgba(c){const ch=Color.parse(c);return [ch.r/255,ch.g/255,ch.b/255,ch.a]}
const results=rows.map(row=>row.op==='channels'?rgba(row.args[0]):row.op==='chain'?row.args[1].reduce((v,[f,...a])=>k[f](v,...a),row.args[0]):k[row.op](...row.args));
const names=JSON.parse(process.argv[2]);
console.log(JSON.stringify({results,names:Object.fromEntries(names.map(n=>[n,rgba(n)]))}));"""
        from py_mermaid.config.color_names import COLOR_NAMES
        result=subprocess.run(['node','--input-type=module','-e',script,json.dumps(INPUTS),json.dumps(list(COLOR_NAMES))],cwd=root,text=True,encoding='utf-8',capture_output=True,check=True)
        print(result.stdout)
    else:unittest.main()
