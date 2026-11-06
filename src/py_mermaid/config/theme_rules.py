"""Flowchart-reachable theme rules statically ported from pinned Mermaid themes.
Generated expressions are Python source, not a runtime JS interpreter.
Includes shared note/state paint reached by F01.4 shapes. See f014-parser-sources.json.
"""
from .colors import adjust, darken, lighten, invert, isDark, rgba, mkBorder, truthy

def base_construct(v):
    v['background'] = '#f4f4f4'
    v['primaryColor'] = '#fff4dd'
    v['noteBkgColor'] = '#fff5ad'
    v['noteTextColor'] = '#333'
    v['THEME_COLOR_LIMIT'] = 12
    v['radius'] = 5
    v['strokeWidth'] = 1
    v['fontFamily'] = '"trebuchet ms", verdana, arial, sans-serif'
    v['fontSize'] = '16px'
    v['useGradient'] = True
    v['dropShadow'] = 'drop-shadow( 1px 2px 2px rgba(185,185,185,1))'

def base_update(v):
    v['primaryTextColor'] = (v.get('primaryTextColor') if truthy(v.get('primaryTextColor')) else ('#eee' if truthy(v.get('darkMode')) else '#333'))
    v['secondaryColor'] = (v.get('secondaryColor') if truthy(v.get('secondaryColor')) else adjust(v.get('primaryColor'), {'h': (-120)}))
    v['tertiaryColor'] = (v.get('tertiaryColor') if truthy(v.get('tertiaryColor')) else adjust(v.get('primaryColor'), {'h': 180, 'l': 5}))
    v['primaryBorderColor'] = (v.get('primaryBorderColor') if truthy(v.get('primaryBorderColor')) else mkBorder(v.get('primaryColor'), v.get('darkMode')))
    v['secondaryBorderColor'] = (v.get('secondaryBorderColor') if truthy(v.get('secondaryBorderColor')) else mkBorder(v.get('secondaryColor'), v.get('darkMode')))
    v['tertiaryBorderColor'] = (v.get('tertiaryBorderColor') if truthy(v.get('tertiaryBorderColor')) else mkBorder(v.get('tertiaryColor'), v.get('darkMode')))
    v['noteBorderColor'] = (v.get('noteBorderColor') if truthy(v.get('noteBorderColor')) else mkBorder(v.get('noteBkgColor'), v.get('darkMode')))
    v['noteBkgColor'] = (v.get('noteBkgColor') if truthy(v.get('noteBkgColor')) else '#fff5ad')
    v['noteTextColor'] = (v.get('noteTextColor') if truthy(v.get('noteTextColor')) else '#333')
    v['tertiaryTextColor'] = (v.get('tertiaryTextColor') if truthy(v.get('tertiaryTextColor')) else invert(v.get('tertiaryColor')))
    v['lineColor'] = (v.get('lineColor') if truthy(v.get('lineColor')) else invert(v.get('background')))
    v['arrowheadColor'] = (v.get('arrowheadColor') if truthy(v.get('arrowheadColor')) else invert(v.get('background')))
    v['textColor'] = (v.get('textColor') if truthy(v.get('textColor')) else v.get('primaryTextColor'))
    v['nodeBkg'] = (v.get('nodeBkg') if truthy(v.get('nodeBkg')) else v.get('primaryColor'))
    v['mainBkg'] = (v.get('mainBkg') if truthy(v.get('mainBkg')) else v.get('primaryColor'))
    v['nodeBorder'] = (v.get('nodeBorder') if truthy(v.get('nodeBorder')) else v.get('primaryBorderColor'))
    v['clusterBkg'] = (v.get('clusterBkg') if truthy(v.get('clusterBkg')) else v.get('tertiaryColor'))
    v['clusterBorder'] = (v.get('clusterBorder') if truthy(v.get('clusterBorder')) else v.get('tertiaryBorderColor'))
    v['defaultLinkColor'] = (v.get('defaultLinkColor') if truthy(v.get('defaultLinkColor')) else v.get('lineColor'))
    v['titleColor'] = (v.get('titleColor') if truthy(v.get('titleColor')) else v.get('tertiaryTextColor'))
    v['edgeLabelBackground'] = (v.get('edgeLabelBackground') if truthy(v.get('edgeLabelBackground')) else (darken(v.get('secondaryColor'), 30) if truthy(v.get('darkMode')) else v.get('secondaryColor')))
    v['nodeTextColor'] = (v.get('nodeTextColor') if truthy(v.get('nodeTextColor')) else v.get('primaryTextColor'))
    v['actorTextColor'] = (v.get('actorTextColor') if truthy(v.get('actorTextColor')) else v.get('primaryTextColor'))
    v['labelTextColor'] = (v.get('labelTextColor') if truthy(v.get('labelTextColor')) else v.get('actorTextColor'))
    v['gradientStart'] = v.get('primaryBorderColor')
    v['gradientStop'] = v.get('secondaryBorderColor')

def dark_construct(v):
    v['background'] = '#333'
    v['primaryColor'] = '#1f2020'
    v['secondaryColor'] = lighten(v.get('primaryColor'), 16)
    v['primaryBorderColor'] = invert(v.get('background'))
    v['secondaryBorderColor'] = mkBorder(v.get('secondaryColor'), v.get('darkMode'))
    v['secondaryTextColor'] = invert(v.get('secondaryColor'))
    v['lineColor'] = invert(v.get('background'))
    v['textColor'] = invert(v.get('background'))
    v['mainBkg'] = '#1f2020'
    v['secondBkg'] = 'calculated'
    v['mainContrastColor'] = 'lightgrey'
    v['lineColor'] = 'calculated'
    v['border1'] = '#ccc'
    v['border2'] = rgba(255, 255, 255, 0.25)
    v['arrowheadColor'] = 'calculated'
    v['fontFamily'] = '"trebuchet ms", verdana, arial, sans-serif'
    v['fontSize'] = '16px'
    v['labelBackground'] = '#181818'
    v['textColor'] = '#ccc'
    v['THEME_COLOR_LIMIT'] = 12
    v['radius'] = 5
    v['strokeWidth'] = 1
    v['nodeBkg'] = 'calculated'
    v['nodeBorder'] = 'calculated'
    v['clusterBkg'] = 'calculated'
    v['clusterBorder'] = 'calculated'
    v['defaultLinkColor'] = 'calculated'
    v['titleColor'] = '#F9FFFE'
    v['edgeLabelBackground'] = 'calculated'
    v['labelTextColor'] = 'calculated'
    v['noteBorderColor'] = 'calculated'
    v['noteBkgColor'] = '#fff5ad'
    v['noteTextColor'] = 'calculated'
    v['clusterBkg'] = '#302F3D'
    v['useGradient'] = True
    v['gradientStart'] = v.get('primaryBorderColor')
    v['gradientStop'] = v.get('secondaryBorderColor')
    v['dropShadow'] = 'drop-shadow( 1px 2px 2px rgba(185,185,185,1))'

def dark_update(v):
    v['secondBkg'] = lighten(v.get('mainBkg'), 16)
    v['lineColor'] = v.get('mainContrastColor')
    v['arrowheadColor'] = v.get('mainContrastColor')
    v['nodeBkg'] = v.get('mainBkg')
    v['nodeBorder'] = v.get('border1')
    v['clusterBkg'] = v.get('secondBkg')
    v['clusterBorder'] = v.get('border2')
    v['defaultLinkColor'] = v.get('lineColor')
    v['edgeLabelBackground'] = lighten(v.get('labelBackground'), 25)
    v['labelTextColor'] = v.get('mainContrastColor')
    v['noteBorderColor'] = v.get('secondaryBorderColor')
    v['noteBkgColor'] = v.get('secondBkg')
    v['noteTextColor'] = v.get('secondaryTextColor')
    v['nodeBorder'] = (v.get('nodeBorder') if truthy(v.get('nodeBorder')) else '#999')

def default_construct(v):
    v['background'] = '#f4f4f4'
    v['primaryColor'] = '#ECECFF'
    v['secondaryColor'] = adjust(v.get('primaryColor'), {'h': 120})
    v['secondaryColor'] = '#ffffde'
    v['primaryBorderColor'] = mkBorder(v.get('primaryColor'), v.get('darkMode'))
    v['secondaryBorderColor'] = mkBorder(v.get('secondaryColor'), v.get('darkMode'))
    v['lineColor'] = invert(v.get('background'))
    v['textColor'] = invert(v.get('background'))
    v['background'] = 'white'
    v['mainBkg'] = '#ECECFF'
    v['secondBkg'] = '#ffffde'
    v['lineColor'] = '#333333'
    v['border1'] = '#9370DB'
    v['primaryBorderColor'] = mkBorder(v.get('primaryColor'), v.get('darkMode'))
    v['border2'] = '#aaaa33'
    v['arrowheadColor'] = '#333333'
    v['fontFamily'] = '"trebuchet ms", verdana, arial, sans-serif'
    v['fontSize'] = '16px'
    v['labelBackground'] = 'rgba(232,232,232, 0.8)'
    v['textColor'] = '#333'
    v['THEME_COLOR_LIMIT'] = 12
    v['radius'] = 5
    v['strokeWidth'] = 1
    v['nodeBkg'] = 'calculated'
    v['nodeBorder'] = 'calculated'
    v['clusterBkg'] = 'calculated'
    v['clusterBorder'] = 'calculated'
    v['defaultLinkColor'] = 'calculated'
    v['titleColor'] = 'calculated'
    v['edgeLabelBackground'] = 'calculated'
    v['actorTextColor'] = 'black'
    v['labelTextColor'] = 'calculated'
    v['noteBorderColor'] = 'calculated'
    v['noteBkgColor'] = '#fff5ad'
    v['noteTextColor'] = 'calculated'
    v['clusterBkg'] = '#FBFBFF'
    v['useGradient'] = False
    v['gradientStart'] = v.get('primaryBorderColor')
    v['gradientStop'] = v.get('secondaryBorderColor')
    v['dropShadow'] = 'drop-shadow(1px 2px 2px rgba(185, 185, 185, 1))'

def default_update(v):
    v['nodeBkg'] = v.get('mainBkg')
    v['nodeBorder'] = v.get('border1')
    v['clusterBkg'] = v.get('secondBkg')
    v['clusterBorder'] = v.get('border2')
    v['defaultLinkColor'] = v.get('lineColor')
    v['titleColor'] = v.get('textColor')
    v['edgeLabelBackground'] = v.get('labelBackground')
    v['labelTextColor'] = v.get('actorTextColor')
    v['noteBorderColor'] = v.get('border2')
    v['noteTextColor'] = v.get('actorTextColor')

def forest_construct(v):
    v['background'] = '#f4f4f4'
    v['primaryColor'] = '#cde498'
    v['secondaryColor'] = '#cdffb2'
    v['background'] = 'white'
    v['mainBkg'] = '#cde498'
    v['secondBkg'] = '#cdffb2'
    v['lineColor'] = 'green'
    v['border1'] = '#13540c'
    v['border2'] = '#6eaa49'
    v['arrowheadColor'] = 'green'
    v['fontFamily'] = '"trebuchet ms", verdana, arial, sans-serif'
    v['fontSize'] = '16px'
    v['primaryBorderColor'] = mkBorder(v.get('primaryColor'), v.get('darkMode'))
    v['secondaryBorderColor'] = mkBorder(v.get('secondaryColor'), v.get('darkMode'))
    v['lineColor'] = invert(v.get('background'))
    v['textColor'] = invert(v.get('background'))
    v['THEME_COLOR_LIMIT'] = 12
    v['radius'] = 5
    v['strokeWidth'] = 1
    v['nodeBkg'] = 'calculated'
    v['nodeBorder'] = 'calculated'
    v['clusterBkg'] = 'calculated'
    v['clusterBorder'] = 'calculated'
    v['defaultLinkColor'] = 'calculated'
    v['titleColor'] = '#333'
    v['edgeLabelBackground'] = '#e8e8e8'
    v['actorTextColor'] = 'black'
    v['labelTextColor'] = 'calculated'
    v['noteBorderColor'] = 'calculated'
    v['noteBkgColor'] = '#fff5ad'
    v['noteTextColor'] = 'calculated'
    v['useGradient'] = True
    v['gradientStart'] = v.get('primaryBorderColor')
    v['gradientStop'] = v.get('secondaryBorderColor')
    v['dropShadow'] = 'drop-shadow( 1px 2px 2px rgba(185,185,185,0.5))'

def forest_update(v):
    v['labelTextColor'] = v.get('actorTextColor')
    v['noteBorderColor'] = v.get('border2')
    v['noteTextColor'] = v.get('actorTextColor')
    v['nodeBkg'] = v.get('mainBkg')
    v['nodeBorder'] = v.get('border1')
    v['clusterBkg'] = v.get('secondBkg')
    v['clusterBorder'] = v.get('border2')
    v['defaultLinkColor'] = v.get('lineColor')

def neutral_construct(v):
    v['primaryColor'] = '#eee'
    v['contrast'] = '#707070'
    v['secondaryColor'] = lighten(v.get('contrast'), 55)
    v['background'] = '#ffffff'
    v['primaryBorderColor'] = mkBorder(v.get('primaryColor'), v.get('darkMode'))
    v['secondaryBorderColor'] = mkBorder(v.get('secondaryColor'), v.get('darkMode'))
    v['lineColor'] = invert(v.get('background'))
    v['textColor'] = invert(v.get('background'))
    v['mainBkg'] = '#eee'
    v['secondBkg'] = 'calculated'
    v['lineColor'] = '#666'
    v['border1'] = '#999'
    v['border2'] = 'calculated'
    v['text'] = '#333'
    v['arrowheadColor'] = '#333333'
    v['fontFamily'] = '"trebuchet ms", verdana, arial, sans-serif'
    v['fontSize'] = '16px'
    v['THEME_COLOR_LIMIT'] = 12
    v['radius'] = 5
    v['strokeWidth'] = 1
    v['nodeBkg'] = 'calculated'
    v['nodeBorder'] = 'calculated'
    v['clusterBkg'] = 'calculated'
    v['clusterBorder'] = 'calculated'
    v['defaultLinkColor'] = 'calculated'
    v['titleColor'] = 'calculated'
    v['edgeLabelBackground'] = 'white'
    v['labelTextColor'] = 'calculated'
    v['noteBorderColor'] = 'calculated'
    v['noteBkgColor'] = 'calculated'
    v['noteTextColor'] = 'calculated'
    v['useGradient'] = True
    v['gradientStart'] = v.get('primaryBorderColor')
    v['gradientStop'] = v.get('secondaryBorderColor')
    v['dropShadow'] = 'drop-shadow( 1px 2px 2px rgba(185,185,185,1))'

def neutral_update(v):
    v['secondBkg'] = lighten(v.get('contrast'), 55)
    v['border2'] = v.get('contrast')
    v['labelTextColor'] = v.get('text')
    v['noteBorderColor'] = '#999'
    v['noteBkgColor'] = '#666'
    v['noteTextColor'] = '#fff'
    v['nodeBkg'] = v.get('mainBkg')
    v['nodeBorder'] = v.get('border1')
    v['clusterBkg'] = v.get('secondBkg')
    v['clusterBorder'] = v.get('border2')
    v['defaultLinkColor'] = v.get('lineColor')
    v['titleColor'] = v.get('text')
    v['stateBorder'] = (v.get('stateBorder') if truthy(v.get('stateBorder')) else '#000')

def neo_construct(v):
    v['background'] = '#ffffff'
    v['primaryColor'] = '#cccccc'
    v['mainBkg'] = '#ffffff'
    v['noteBkgColor'] = '#fff5ad'
    v['noteTextColor'] = '#333'
    v['THEME_COLOR_LIMIT'] = 12
    v['radius'] = 3
    v['strokeWidth'] = 2
    v['primaryBorderColor'] = mkBorder(v.get('primaryColor'), v.get('darkMode'))
    v['fontFamily'] = 'arial, sans-serif'
    v['fontSize'] = '14px'
    v['nodeBorder'] = '#000000'
    v['stateBorder'] = '#000000'
    v['useGradient'] = True
    v['gradientStart'] = '#0042eb'
    v['gradientStop'] = '#eb0042'
    v['dropShadow'] = 'drop-shadow( 0px 1px 2px rgba(0, 0, 0, 0.25));'
    v['tertiaryColor'] = '#ffffff'

def neo_update(v):
    v['primaryTextColor'] = (v.get('primaryTextColor') if truthy(v.get('primaryTextColor')) else ('#eee' if truthy(v.get('darkMode')) else '#333'))
    v['secondaryColor'] = (v.get('secondaryColor') if truthy(v.get('secondaryColor')) else adjust(v.get('primaryColor'), {'h': (-120)}))
    v['tertiaryColor'] = (v.get('tertiaryColor') if truthy(v.get('tertiaryColor')) else adjust(v.get('primaryColor'), {'h': 180, 'l': 5}))
    v['primaryBorderColor'] = (v.get('primaryBorderColor') if truthy(v.get('primaryBorderColor')) else mkBorder(v.get('primaryColor'), v.get('darkMode')))
    v['tertiaryBorderColor'] = (v.get('tertiaryBorderColor') if truthy(v.get('tertiaryBorderColor')) else mkBorder(v.get('tertiaryColor'), v.get('darkMode')))
    v['noteBorderColor'] = (v.get('noteBorderColor') if truthy(v.get('noteBorderColor')) else mkBorder(v.get('noteBkgColor'), v.get('darkMode')))
    v['noteBkgColor'] = (v.get('noteBkgColor') if truthy(v.get('noteBkgColor')) else '#fff5ad')
    v['noteTextColor'] = (v.get('noteTextColor') if truthy(v.get('noteTextColor')) else '#333')
    v['tertiaryTextColor'] = (v.get('tertiaryTextColor') if truthy(v.get('tertiaryTextColor')) else invert(v.get('tertiaryColor')))
    v['lineColor'] = (v.get('lineColor') if truthy(v.get('lineColor')) else invert(v.get('background')))
    v['arrowheadColor'] = (v.get('arrowheadColor') if truthy(v.get('arrowheadColor')) else invert(v.get('background')))
    v['textColor'] = (v.get('textColor') if truthy(v.get('textColor')) else v.get('primaryTextColor'))
    v['nodeBkg'] = (v.get('nodeBkg') if truthy(v.get('nodeBkg')) else v.get('primaryColor'))
    v['mainBkg'] = (v.get('mainBkg') if truthy(v.get('mainBkg')) else v.get('primaryColor'))
    v['nodeBorder'] = (v.get('nodeBorder') if truthy(v.get('nodeBorder')) else v.get('primaryBorderColor'))
    v['clusterBkg'] = (v.get('clusterBkg') if truthy(v.get('clusterBkg')) else v.get('tertiaryColor'))
    v['clusterBorder'] = (v.get('clusterBorder') if truthy(v.get('clusterBorder')) else v.get('tertiaryBorderColor'))
    v['defaultLinkColor'] = (v.get('defaultLinkColor') if truthy(v.get('defaultLinkColor')) else v.get('lineColor'))
    v['titleColor'] = (v.get('titleColor') if truthy(v.get('titleColor')) else v.get('tertiaryTextColor'))
    v['edgeLabelBackground'] = (v.get('edgeLabelBackground') if truthy(v.get('edgeLabelBackground')) else (darken(v.get('secondaryColor'), 30) if truthy(v.get('darkMode')) else v.get('secondaryColor')))
    v['nodeTextColor'] = (v.get('nodeTextColor') if truthy(v.get('nodeTextColor')) else v.get('primaryTextColor'))
    v['actorTextColor'] = (v.get('actorTextColor') if truthy(v.get('actorTextColor')) else v.get('primaryTextColor'))
    v['labelTextColor'] = (v.get('labelTextColor') if truthy(v.get('labelTextColor')) else v.get('actorTextColor'))

def neo_dark_construct(v):
    v['background'] = '#333'
    v['primaryColor'] = '#1f2020'
    v['secondaryColor'] = lighten(v.get('primaryColor'), 16)
    v['tertiaryColor'] = adjust(v.get('primaryColor'), {'h': (-160)})
    v['tertiaryBorderColor'] = mkBorder(v.get('tertiaryColor'), v.get('darkMode'))
    v['primaryTextColor'] = invert(v.get('primaryColor'))
    v['tertiaryTextColor'] = invert(v.get('tertiaryColor'))
    v['mainBkg'] = '#2a2020'
    v['border1'] = '#ccc'
    v['arrowheadColor'] = invert(v.get('background'))
    v['fontFamily'] = 'arial, sans-serif'
    v['fontSize'] = '14px'
    v['textColor'] = '#ccc'
    v['THEME_COLOR_LIMIT'] = 12
    v['radius'] = 3
    v['strokeWidth'] = 1
    v['noteBkgColor'] = '#fff5ad'
    v['noteTextColor'] = '#333'
    v['THEME_COLOR_LIMIT'] = 12
    v['fontFamily'] = 'arial, sans-serif'
    v['fontSize'] = '14px'
    v['useGradient'] = True
    v['gradientStart'] = '#0042eb'
    v['gradientStop'] = '#eb0042'
    v['dropShadow'] = 'drop-shadow( 1px 2px 2px rgba(185,185,185,0.2))'

def neo_dark_update(v):
    v['primaryTextColor'] = (v.get('primaryTextColor') if truthy(v.get('primaryTextColor')) else ('#eee' if truthy(v.get('darkMode')) else '#333'))
    v['secondaryColor'] = (v.get('secondaryColor') if truthy(v.get('secondaryColor')) else adjust(v.get('primaryColor'), {'h': (-120)}))
    v['tertiaryColor'] = (v.get('tertiaryColor') if truthy(v.get('tertiaryColor')) else adjust(v.get('primaryColor'), {'h': 180, 'l': 5}))
    v['tertiaryBorderColor'] = (v.get('tertiaryBorderColor') if truthy(v.get('tertiaryBorderColor')) else mkBorder(v.get('tertiaryColor'), v.get('darkMode')))
    v['noteBorderColor'] = (v.get('noteBorderColor') if truthy(v.get('noteBorderColor')) else mkBorder(v.get('noteBkgColor'), v.get('darkMode')))
    v['noteBkgColor'] = (v.get('noteBkgColor') if truthy(v.get('noteBkgColor')) else '#fff5ad')
    v['noteTextColor'] = (v.get('noteTextColor') if truthy(v.get('noteTextColor')) else '#333')
    v['tertiaryTextColor'] = (v.get('tertiaryTextColor') if truthy(v.get('tertiaryTextColor')) else invert(v.get('tertiaryColor')))
    v['lineColor'] = (v.get('lineColor') if truthy(v.get('lineColor')) else invert(v.get('background')))
    v['arrowheadColor'] = (v.get('arrowheadColor') if truthy(v.get('arrowheadColor')) else invert(v.get('background')))
    v['textColor'] = (v.get('textColor') if truthy(v.get('textColor')) else v.get('primaryTextColor'))
    v['nodeBkg'] = (v.get('nodeBkg') if truthy(v.get('nodeBkg')) else v.get('primaryColor'))
    v['mainBkg'] = (v.get('mainBkg') if truthy(v.get('mainBkg')) else v.get('primaryColor'))
    v['nodeBorder'] = (v.get('nodeBorder') if truthy(v.get('nodeBorder')) else v.get('border1'))
    v['clusterBkg'] = (v.get('clusterBkg') if truthy(v.get('clusterBkg')) else v.get('tertiaryColor'))
    v['clusterBorder'] = (v.get('clusterBorder') if truthy(v.get('clusterBorder')) else v.get('tertiaryBorderColor'))
    v['defaultLinkColor'] = (v.get('defaultLinkColor') if truthy(v.get('defaultLinkColor')) else v.get('lineColor'))
    v['titleColor'] = (v.get('titleColor') if truthy(v.get('titleColor')) else v.get('tertiaryTextColor'))
    v['edgeLabelBackground'] = (v.get('edgeLabelBackground') if truthy(v.get('edgeLabelBackground')) else (darken(v.get('secondaryColor'), 30) if truthy(v.get('darkMode')) else v.get('secondaryColor')))
    v['nodeTextColor'] = (v.get('nodeTextColor') if truthy(v.get('nodeTextColor')) else v.get('primaryTextColor'))
    v['actorTextColor'] = (v.get('actorTextColor') if truthy(v.get('actorTextColor')) else v.get('primaryTextColor'))
    v['labelTextColor'] = (v.get('labelTextColor') if truthy(v.get('labelTextColor')) else v.get('actorTextColor'))

def redux_construct(v):
    v['background'] = '#ffffff'
    v['primaryColor'] = '#cccccc'
    v['mainBkg'] = '#ffffff'
    v['noteBkgColor'] = '#fff5ad'
    v['noteTextColor'] = '#28253D'
    v['THEME_COLOR_LIMIT'] = 12
    v['radius'] = 12
    v['strokeWidth'] = 2
    v['primaryBorderColor'] = mkBorder('#28253D', v.get('darkMode'))
    v['fontFamily'] = '"Recursive Variable", arial, sans-serif'
    v['fontSize'] = '14px'
    v['nodeBorder'] = '#28253D'
    v['stateBorder'] = '#28253D'
    v['useGradient'] = False
    v['gradientStart'] = '#0042eb'
    v['gradientStop'] = '#eb0042'
    v['dropShadow'] = 'url(#drop-shadow)'
    v['nodeShadow'] = True
    v['tertiaryColor'] = '#ffffff'
    v['clusterBkg'] = '#F9F9FB'
    v['clusterBorder'] = '#BDBCCC'
    v['noteBorderColor'] = '#FACC15'

def redux_update(v):
    v['primaryTextColor'] = (v.get('primaryTextColor') if truthy(v.get('primaryTextColor')) else ('#eee' if truthy(v.get('darkMode')) else '#28253D'))
    v['secondaryColor'] = (v.get('secondaryColor') if truthy(v.get('secondaryColor')) else adjust(v.get('primaryColor'), {'h': (-120)}))
    v['tertiaryColor'] = (v.get('tertiaryColor') if truthy(v.get('tertiaryColor')) else adjust(v.get('primaryColor'), {'h': 180, 'l': 5}))
    v['primaryBorderColor'] = (v.get('primaryBorderColor') if truthy(v.get('primaryBorderColor')) else mkBorder(v.get('primaryColor'), v.get('darkMode')))
    v['tertiaryBorderColor'] = (v.get('tertiaryBorderColor') if truthy(v.get('tertiaryBorderColor')) else mkBorder(v.get('tertiaryColor'), v.get('darkMode')))
    v['noteBorderColor'] = (v.get('noteBorderColor') if truthy(v.get('noteBorderColor')) else mkBorder(v.get('noteBkgColor'), v.get('darkMode')))
    v['noteBkgColor'] = (v.get('noteBkgColor') if truthy(v.get('noteBkgColor')) else '#FEF9C3')
    v['noteTextColor'] = (v.get('noteTextColor') if truthy(v.get('noteTextColor')) else '#28253D')
    v['tertiaryTextColor'] = (v.get('tertiaryTextColor') if truthy(v.get('tertiaryTextColor')) else invert(v.get('tertiaryColor')))
    v['lineColor'] = (v.get('lineColor') if truthy(v.get('lineColor')) else invert(v.get('background')))
    v['arrowheadColor'] = (v.get('arrowheadColor') if truthy(v.get('arrowheadColor')) else invert(v.get('background')))
    v['textColor'] = (v.get('textColor') if truthy(v.get('textColor')) else v.get('primaryTextColor'))
    v['nodeBkg'] = (v.get('nodeBkg') if truthy(v.get('nodeBkg')) else v.get('primaryColor'))
    v['mainBkg'] = (v.get('mainBkg') if truthy(v.get('mainBkg')) else v.get('primaryColor'))
    v['nodeBorder'] = (v.get('nodeBorder') if truthy(v.get('nodeBorder')) else v.get('primaryBorderColor'))
    v['clusterBkg'] = (v.get('clusterBkg') if truthy(v.get('clusterBkg')) else v.get('tertiaryColor'))
    v['clusterBorder'] = (v.get('clusterBorder') if truthy(v.get('clusterBorder')) else v.get('tertiaryBorderColor'))
    v['defaultLinkColor'] = (v.get('defaultLinkColor') if truthy(v.get('defaultLinkColor')) else v.get('lineColor'))
    v['titleColor'] = (v.get('titleColor') if truthy(v.get('titleColor')) else v.get('tertiaryTextColor'))
    v['edgeLabelBackground'] = (v.get('edgeLabelBackground') if truthy(v.get('edgeLabelBackground')) else (darken(v.get('secondaryColor'), 30) if truthy(v.get('darkMode')) else v.get('secondaryColor')))
    v['nodeTextColor'] = (v.get('nodeTextColor') if truthy(v.get('nodeTextColor')) else v.get('primaryTextColor'))
    v['actorTextColor'] = (v.get('actorTextColor') if truthy(v.get('actorTextColor')) else v.get('primaryTextColor'))
    v['labelTextColor'] = (v.get('labelTextColor') if truthy(v.get('labelTextColor')) else v.get('actorTextColor'))

def redux_dark_construct(v):
    v['background'] = '#333'
    v['primaryColor'] = '#1f2020'
    v['secondaryColor'] = lighten(v.get('primaryColor'), 16)
    v['tertiaryColor'] = adjust(v.get('primaryColor'), {'h': (-160)})
    v['tertiaryBorderColor'] = mkBorder(v.get('tertiaryColor'), v.get('darkMode'))
    v['primaryTextColor'] = invert(v.get('primaryColor'))
    v['tertiaryTextColor'] = invert(v.get('tertiaryColor'))
    v['mainBkg'] = '#111113'
    v['border1'] = '#ccc'
    v['arrowheadColor'] = invert(v.get('background'))
    v['fontFamily'] = '"Recursive Variable", arial, sans-serif'
    v['fontSize'] = '14px'
    v['textColor'] = '#ccc'
    v['THEME_COLOR_LIMIT'] = 12
    v['radius'] = 12
    v['strokeWidth'] = 2
    v['noteBkgColor'] = (v.get('noteBkgColor') if v.get('noteBkgColor') is not None else '#FEF9C3')
    v['noteTextColor'] = (v.get('noteTextColor') if v.get('noteTextColor') is not None else '#28253D')
    v['THEME_COLOR_LIMIT'] = 12
    v['fontFamily'] = '"Recursive Variable", arial, sans-serif'
    v['fontSize'] = '14px'
    v['nodeBorder'] = '#FFFFFF'
    v['stateBorder'] = '#FFFFFF'
    v['useGradient'] = False
    v['gradientStart'] = '#0042eb'
    v['gradientStop'] = '#eb0042'
    v['dropShadow'] = 'url(#drop-shadow)'
    v['nodeShadow'] = True
    v['clusterBkg'] = '#1E1A2E'
    v['clusterBorder'] = '#BDBCCC'
    v['noteBorderColor'] = '#FACC15'

def redux_dark_update(v):
    v['primaryTextColor'] = (v.get('primaryTextColor') if truthy(v.get('primaryTextColor')) else ('#eee' if truthy(v.get('darkMode')) else '#FFFFFF'))
    v['secondaryColor'] = (v.get('secondaryColor') if truthy(v.get('secondaryColor')) else adjust(v.get('primaryColor'), {'h': (-120)}))
    v['tertiaryColor'] = (v.get('tertiaryColor') if truthy(v.get('tertiaryColor')) else adjust(v.get('primaryColor'), {'h': 180, 'l': 5}))
    v['tertiaryBorderColor'] = (v.get('tertiaryBorderColor') if truthy(v.get('tertiaryBorderColor')) else mkBorder(v.get('tertiaryColor'), v.get('darkMode')))
    v['noteBorderColor'] = (v.get('noteBorderColor') if truthy(v.get('noteBorderColor')) else mkBorder(v.get('noteBkgColor'), v.get('darkMode')))
    v['noteBkgColor'] = (v.get('noteBkgColor') if truthy(v.get('noteBkgColor')) else '#fff5ad')
    v['noteTextColor'] = (v.get('noteTextColor') if truthy(v.get('noteTextColor')) else '#FFFFFF')
    v['tertiaryTextColor'] = (v.get('tertiaryTextColor') if truthy(v.get('tertiaryTextColor')) else invert(v.get('tertiaryColor')))
    v['lineColor'] = (v.get('lineColor') if truthy(v.get('lineColor')) else invert(v.get('background')))
    v['arrowheadColor'] = (v.get('arrowheadColor') if truthy(v.get('arrowheadColor')) else invert(v.get('background')))
    v['textColor'] = (v.get('textColor') if truthy(v.get('textColor')) else v.get('primaryTextColor'))
    v['nodeBkg'] = (v.get('nodeBkg') if truthy(v.get('nodeBkg')) else v.get('primaryColor'))
    v['mainBkg'] = (v.get('mainBkg') if truthy(v.get('mainBkg')) else v.get('primaryColor'))
    v['nodeBorder'] = (v.get('nodeBorder') if truthy(v.get('nodeBorder')) else v.get('border1'))
    v['clusterBkg'] = (v.get('clusterBkg') if truthy(v.get('clusterBkg')) else v.get('tertiaryColor'))
    v['clusterBorder'] = (v.get('clusterBorder') if truthy(v.get('clusterBorder')) else v.get('tertiaryBorderColor'))
    v['defaultLinkColor'] = (v.get('defaultLinkColor') if truthy(v.get('defaultLinkColor')) else v.get('lineColor'))
    v['titleColor'] = (v.get('titleColor') if truthy(v.get('titleColor')) else v.get('tertiaryTextColor'))
    v['edgeLabelBackground'] = (v.get('edgeLabelBackground') if truthy(v.get('edgeLabelBackground')) else (darken(v.get('secondaryColor'), 30) if truthy(v.get('darkMode')) else v.get('secondaryColor')))
    v['nodeTextColor'] = (v.get('nodeTextColor') if truthy(v.get('nodeTextColor')) else v.get('primaryTextColor'))
    v['actorTextColor'] = (v.get('actorTextColor') if truthy(v.get('actorTextColor')) else v.get('primaryTextColor'))
    v['labelTextColor'] = (v.get('labelTextColor') if truthy(v.get('labelTextColor')) else v.get('actorTextColor'))

def redux_color_construct(v):
    v['background'] = '#ffffff'
    v['primaryColor'] = '#cccccc'
    v['mainBkg'] = '#ffffff'
    v['noteBkgColor'] = '#fff5ad'
    v['noteTextColor'] = '#28253D'
    v['THEME_COLOR_LIMIT'] = 12
    v['radius'] = 12
    v['strokeWidth'] = 2
    v['primaryBorderColor'] = mkBorder('#28253D', v.get('darkMode'))
    v['fontFamily'] = '"Recursive Variable", arial, sans-serif'
    v['fontSize'] = '14px'
    v['nodeBorder'] = '#28253D'
    v['stateBorder'] = '#28253D'
    v['useGradient'] = False
    v['gradientStart'] = '#0042eb'
    v['gradientStop'] = '#eb0042'
    v['dropShadow'] = 'url(#drop-shadow)'
    v['nodeShadow'] = True
    v['tertiaryColor'] = '#ffffff'
    v['clusterBkg'] = '#F9F9FB'
    v['clusterBorder'] = '#BDBCCC'
    v['noteBorderColor'] = '#FACC15'
    v['borderColorArray'] = ['#E879F9', '#2DD4BF', '#FB923C', '#22D3EE', '#4ADE80', '#A78BFA', '#F87171', '#FACC15', '#818CF8', '#A3E635 ', '#38BDF8', '#FB7185']
    v['bkgColorArray'] = ['#FDF4FF', '#F0FDFA', '#FFF7ED', '#ECFEFF', '#F0FDF4', '#F5F3FF', '#FEF2F2', '#FEFCE8', '#EEF2FF', '#F7FEE7', '#F0F9FF', '#FFF1F2']

def redux_color_update(v):
    v['primaryTextColor'] = (v.get('primaryTextColor') if truthy(v.get('primaryTextColor')) else ('#eee' if truthy(v.get('darkMode')) else '#28253D'))
    v['secondaryColor'] = (v.get('secondaryColor') if truthy(v.get('secondaryColor')) else adjust(v.get('primaryColor'), {'h': (-120)}))
    v['tertiaryColor'] = (v.get('tertiaryColor') if truthy(v.get('tertiaryColor')) else adjust(v.get('primaryColor'), {'h': 180, 'l': 5}))
    v['primaryBorderColor'] = (v.get('primaryBorderColor') if truthy(v.get('primaryBorderColor')) else mkBorder(v.get('primaryColor'), v.get('darkMode')))
    v['tertiaryBorderColor'] = (v.get('tertiaryBorderColor') if truthy(v.get('tertiaryBorderColor')) else mkBorder(v.get('tertiaryColor'), v.get('darkMode')))
    v['noteBorderColor'] = (v.get('noteBorderColor') if truthy(v.get('noteBorderColor')) else mkBorder(v.get('noteBkgColor'), v.get('darkMode')))
    v['noteBkgColor'] = (v.get('noteBkgColor') if truthy(v.get('noteBkgColor')) else '#fff5ad')
    v['noteTextColor'] = (v.get('noteTextColor') if truthy(v.get('noteTextColor')) else '#28253D')
    v['tertiaryTextColor'] = (v.get('tertiaryTextColor') if truthy(v.get('tertiaryTextColor')) else invert(v.get('tertiaryColor')))
    v['lineColor'] = (v.get('lineColor') if truthy(v.get('lineColor')) else invert(v.get('background')))
    v['arrowheadColor'] = (v.get('arrowheadColor') if truthy(v.get('arrowheadColor')) else invert(v.get('background')))
    v['textColor'] = (v.get('textColor') if truthy(v.get('textColor')) else v.get('primaryTextColor'))
    v['nodeBkg'] = (v.get('nodeBkg') if truthy(v.get('nodeBkg')) else v.get('primaryColor'))
    v['mainBkg'] = (v.get('mainBkg') if truthy(v.get('mainBkg')) else v.get('primaryColor'))
    v['nodeBorder'] = (v.get('nodeBorder') if truthy(v.get('nodeBorder')) else v.get('primaryBorderColor'))
    v['clusterBkg'] = (v.get('clusterBkg') if truthy(v.get('clusterBkg')) else v.get('tertiaryColor'))
    v['clusterBorder'] = (v.get('clusterBorder') if truthy(v.get('clusterBorder')) else v.get('tertiaryBorderColor'))
    v['defaultLinkColor'] = (v.get('defaultLinkColor') if truthy(v.get('defaultLinkColor')) else v.get('lineColor'))
    v['titleColor'] = (v.get('titleColor') if truthy(v.get('titleColor')) else v.get('tertiaryTextColor'))
    v['edgeLabelBackground'] = (v.get('edgeLabelBackground') if truthy(v.get('edgeLabelBackground')) else (darken(v.get('secondaryColor'), 30) if truthy(v.get('darkMode')) else v.get('secondaryColor')))
    v['nodeTextColor'] = (v.get('nodeTextColor') if truthy(v.get('nodeTextColor')) else v.get('primaryTextColor'))
    v['actorTextColor'] = (v.get('actorTextColor') if truthy(v.get('actorTextColor')) else v.get('primaryTextColor'))
    v['labelTextColor'] = (v.get('labelTextColor') if truthy(v.get('labelTextColor')) else v.get('actorTextColor'))

def redux_dark_color_construct(v):
    v['background'] = '#333'
    v['primaryColor'] = '#1f2020'
    v['secondaryColor'] = lighten(v.get('primaryColor'), 16)
    v['tertiaryColor'] = adjust(v.get('primaryColor'), {'h': (-160)})
    v['tertiaryBorderColor'] = mkBorder(v.get('tertiaryColor'), v.get('darkMode'))
    v['primaryTextColor'] = invert(v.get('primaryColor'))
    v['tertiaryTextColor'] = invert(v.get('tertiaryColor'))
    v['mainBkg'] = '#111113'
    v['border1'] = '#ccc'
    v['arrowheadColor'] = invert(v.get('background'))
    v['fontFamily'] = '"Recursive Variable", arial, sans-serif'
    v['fontSize'] = '14px'
    v['textColor'] = '#ccc'
    v['THEME_COLOR_LIMIT'] = 12
    v['radius'] = 12
    v['strokeWidth'] = 2
    v['noteBkgColor'] = (v.get('noteBkgColor') if v.get('noteBkgColor') is not None else '#FEF9C3')
    v['noteTextColor'] = (v.get('noteTextColor') if v.get('noteTextColor') is not None else '#28253D')
    v['THEME_COLOR_LIMIT'] = 12
    v['fontFamily'] = '"Recursive Variable", arial, sans-serif'
    v['fontSize'] = '14px'
    v['nodeBorder'] = '#FFFFFF'
    v['stateBorder'] = '#FFFFFF'
    v['useGradient'] = False
    v['gradientStart'] = '#0042eb'
    v['gradientStop'] = '#eb0042'
    v['dropShadow'] = 'url(#drop-shadow)'
    v['nodeShadow'] = True
    v['clusterBkg'] = '#1E1A2E'
    v['clusterBorder'] = '#BDBCCC'
    v['noteBorderColor'] = '#FACC15'
    v['borderColorArray'] = ['#E879F9', '#2DD4BF', '#FB923C', '#22D3EE', '#4ADE80', '#A78BFA', '#F87171', '#FACC15', '#818CF8', '#A3E635 ', '#38BDF8', '#FB7185']
    v['bkgColorArray'] = []

def redux_dark_color_update(v):
    v['primaryTextColor'] = (v.get('primaryTextColor') if truthy(v.get('primaryTextColor')) else ('#eee' if truthy(v.get('darkMode')) else '#FFFFFF'))
    v['secondaryColor'] = (v.get('secondaryColor') if truthy(v.get('secondaryColor')) else adjust(v.get('primaryColor'), {'h': (-120)}))
    v['tertiaryColor'] = (v.get('tertiaryColor') if truthy(v.get('tertiaryColor')) else adjust(v.get('primaryColor'), {'h': 180, 'l': 5}))
    v['tertiaryBorderColor'] = (v.get('tertiaryBorderColor') if truthy(v.get('tertiaryBorderColor')) else mkBorder(v.get('tertiaryColor'), v.get('darkMode')))
    v['noteBorderColor'] = (v.get('noteBorderColor') if truthy(v.get('noteBorderColor')) else mkBorder(v.get('noteBkgColor'), v.get('darkMode')))
    v['noteBkgColor'] = (v.get('noteBkgColor') if truthy(v.get('noteBkgColor')) else '#fff5ad')
    v['noteTextColor'] = (v.get('noteTextColor') if truthy(v.get('noteTextColor')) else '#FFFFFF')
    v['tertiaryTextColor'] = (v.get('tertiaryTextColor') if truthy(v.get('tertiaryTextColor')) else invert(v.get('tertiaryColor')))
    v['lineColor'] = (v.get('lineColor') if truthy(v.get('lineColor')) else invert(v.get('background')))
    v['arrowheadColor'] = (v.get('arrowheadColor') if truthy(v.get('arrowheadColor')) else invert(v.get('background')))
    v['textColor'] = (v.get('textColor') if truthy(v.get('textColor')) else v.get('primaryTextColor'))
    v['nodeBkg'] = (v.get('nodeBkg') if truthy(v.get('nodeBkg')) else v.get('primaryColor'))
    v['mainBkg'] = (v.get('mainBkg') if truthy(v.get('mainBkg')) else v.get('primaryColor'))
    v['nodeBorder'] = (v.get('nodeBorder') if truthy(v.get('nodeBorder')) else v.get('border1'))
    v['clusterBkg'] = (v.get('clusterBkg') if truthy(v.get('clusterBkg')) else v.get('tertiaryColor'))
    v['clusterBorder'] = (v.get('clusterBorder') if truthy(v.get('clusterBorder')) else v.get('tertiaryBorderColor'))
    v['defaultLinkColor'] = (v.get('defaultLinkColor') if truthy(v.get('defaultLinkColor')) else v.get('lineColor'))
    v['titleColor'] = (v.get('titleColor') if truthy(v.get('titleColor')) else v.get('tertiaryTextColor'))
    v['edgeLabelBackground'] = (v.get('edgeLabelBackground') if truthy(v.get('edgeLabelBackground')) else (darken(v.get('secondaryColor'), 30) if truthy(v.get('darkMode')) else v.get('secondaryColor')))
    v['nodeTextColor'] = (v.get('nodeTextColor') if truthy(v.get('nodeTextColor')) else v.get('primaryTextColor'))
    v['actorTextColor'] = (v.get('actorTextColor') if truthy(v.get('actorTextColor')) else v.get('primaryTextColor'))
    v['labelTextColor'] = (v.get('labelTextColor') if truthy(v.get('labelTextColor')) else v.get('actorTextColor'))

THEME_RULES = {
    'base': (base_construct, base_update),
    'dark': (dark_construct, dark_update),
    'default': (default_construct, default_update),
    'forest': (forest_construct, forest_update),
    'neutral': (neutral_construct, neutral_update),
    'neo': (neo_construct, neo_update),
    'neo-dark': (neo_dark_construct, neo_dark_update),
    'redux': (redux_construct, redux_update),
    'redux-dark': (redux_dark_construct, redux_dark_update),
    'redux-color': (redux_color_construct, redux_color_update),
    'redux-dark-color': (redux_dark_color_construct, redux_dark_color_update),
}
