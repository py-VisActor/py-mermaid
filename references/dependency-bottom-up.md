# 从底层向上的依赖工作索引（自动生成）

来源和选型说明见 [迁移方案](../docs/DEPENDENCY_MIGRATION.md)。包管理叶节点不等于算法简单。
目标采用 [Canvas 原生架构](../docs/CANVAS_NATIVE_ARCHITECTURE.md)；discard-browser-layer 表示淘汰该运行机制，相关图形功能由 Python 数据与 Canvas 承接。
层号按依赖边的 SCC 缩图计算，依赖先于使用者；同一 SCC 内部一起处理。每项计划均未实现/未验证等价。

| 层 | SCC | 精确节点 | 处理策略 | Python 候选/实现 | 工作包 |
| --- | --- | --- | --- | --- | --- |
| 0 | C0000 | `@alloc/quick-lru@5.2.0` | stdlib-with-adapter | collections.OrderedDict, functools | D00 |
| 0 | C0002 | `@antfu/utils@9.2.0` | trace-icon-resource-then-rewrite | importlib.resources, pathlib, json | D08 |
| 0 | C0004 | `@babel/compat-data@7.29.7` | trace-then-rewrite-surface | Python 重写/追踪调用面 | D10 |
| 0 | C0008 | `@babel/helper-globals@7.29.7` | trace-then-rewrite-surface | Python 重写/追踪调用面 | D10 |
| 0 | C0010 | `@babel/helper-string-parser@7.29.7` | trace-then-rewrite-surface | Python 重写/追踪调用面 | D10 |
| 0 | C0011 | `@babel/helper-validator-identifier@7.29.7` | trace-then-rewrite-surface | Python 重写/追踪调用面 | D10 |
| 0 | C0012 | `@babel/helper-validator-option@7.29.7` | trace-then-rewrite-surface | Python 重写/追踪调用面 | D10 |
| 0 | C0018 | `@braintree/sanitize-url@7.1.2` | retain-url-policy-adapter | urllib.parse | D05 |
| 0 | C0021 | `@chevrotain/regexp-to-ast@13.2.0` | candidate-or-rewrite | lark | D04 |
| 0 | C0022 | `@chevrotain/types@13.2.0` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0023 | `@chevrotain/utils@13.2.0` | candidate-or-rewrite | lark | D04 |
| 0 | C0029 | `@floating-ui/utils@0.2.10` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 0 | C0032 | `@iconify/types@2.0.0` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0037 | `@jridgewell/resolve-uri@3.1.2` | trace-then-rewrite-surface | Python 重写/追踪调用面 | D10 |
| 0 | C0038 | `@jridgewell/sourcemap-codec@1.5.5` | trace-then-rewrite-surface | Python 重写/追踪调用面 | D10 |
| 0 | C0040 | `@napi-rs/canvas-android-arm64@0.1.100` | discard-alternate-renderer | py-skia-canvas | D08 |
| 0 | C0041 | `@napi-rs/canvas-darwin-arm64@0.1.100` | discard-alternate-renderer | py-skia-canvas | D08 |
| 0 | C0042 | `@napi-rs/canvas-darwin-x64@0.1.100` | discard-alternate-renderer | py-skia-canvas | D08 |
| 0 | C0043 | `@napi-rs/canvas-linux-arm-gnueabihf@0.1.100` | discard-alternate-renderer | py-skia-canvas | D08 |
| 0 | C0044 | `@napi-rs/canvas-linux-arm64-gnu@0.1.100` | discard-alternate-renderer | py-skia-canvas | D08 |
| 0 | C0045 | `@napi-rs/canvas-linux-arm64-musl@0.1.100` | discard-alternate-renderer | py-skia-canvas | D08 |
| 0 | C0046 | `@napi-rs/canvas-linux-riscv64-gnu@0.1.100` | discard-alternate-renderer | py-skia-canvas | D08 |
| 0 | C0047 | `@napi-rs/canvas-linux-x64-gnu@0.1.100` | discard-alternate-renderer | py-skia-canvas | D08 |
| 0 | C0048 | `@napi-rs/canvas-linux-x64-musl@0.1.100` | discard-alternate-renderer | py-skia-canvas | D08 |
| 0 | C0049 | `@napi-rs/canvas-win32-arm64-msvc@0.1.100` | discard-alternate-renderer | py-skia-canvas | D08 |
| 0 | C0050 | `@napi-rs/canvas-win32-x64-msvc@0.1.100` | discard-alternate-renderer | py-skia-canvas | D08 |
| 0 | C0053 | `@nodelib/fs.stat@2.0.5` | stdlib-with-adapter-and-trace | pathlib, glob, os, io | D02 |
| 0 | C0055 | `@pkgjs/parseargs@0.11.0` | trace-cli-then-adapt | argparse | D00 |
| 0 | C0065 | `@tanstack/virtual-core@3.13.12` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 0 | C0066 | `@types/d3-array@3.2.2` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0069 | `@types/d3-chord@3.0.6` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0070 | `@types/d3-color@3.1.3` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0072 | `@types/d3-delaunay@6.0.4` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0073 | `@types/d3-dispatch@3.0.7` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0075 | `@types/d3-dsv@3.0.7` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0076 | `@types/d3-ease@3.0.2` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0078 | `@types/d3-force@3.0.10` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0079 | `@types/d3-format@3.0.4` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0081 | `@types/d3-hierarchy@3.1.7` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0083 | `@types/d3-path@3.1.1` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0084 | `@types/d3-polygon@3.0.2` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0085 | `@types/d3-quadtree@3.0.6` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0086 | `@types/d3-random@3.0.3` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0087 | `@types/d3-scale-chromatic@3.1.0` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0089 | `@types/d3-selection@3.0.11` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0091 | `@types/d3-time-format@4.0.3` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0092 | `@types/d3-time@3.0.4` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0093 | `@types/d3-timer@3.0.2` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0097 | `@types/geojson@7946.0.16` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0099 | `@types/trusted-types@2.0.7` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0103 | `acorn@8.15.0` | trace-icon-resource-then-rewrite | importlib.resources, pathlib, json | D08 |
| 0 | C0104 | `ansi-regex@5.0.1` | stdlib-with-adapter-and-trace | re, unicodedata | D00 |
| 0 | C0105 | `ansi-regex@6.2.2` | stdlib-with-adapter-and-trace | re, unicodedata | D00 |
| 0 | C0107 | `ansi-styles@6.2.3` | stdlib-with-adapter-and-trace | re, unicodedata | D00 |
| 0 | C0108 | `antlr4@4.11.0` | candidate-or-rewrite | antlr4-python3-runtime, lark | D10 |
| 0 | C0109 | `any-promise@1.3.0` | stdlib-with-adapter-and-trace | logging, json, io, asyncio | D00 |
| 0 | C0111 | `arg@5.0.2` | trace-cli-then-adapt | argparse | D00 |
| 0 | C0112 | `argparse@2.0.1` | trace-cli-then-adapt | argparse | D00 |
| 0 | C0113 | `atomic-sleep@1.0.0` | trace-platform-then-rewrite | sys, os, asyncio | D00 |
| 0 | C0114 | `balanced-match@1.0.2` | rewrite-used-surface-and-trace | re, fnmatch | D00 |
| 0 | C0115 | `base64-js@1.5.1` | stdlib-with-adapter-and-trace | bytes, base64, struct, zlib, asyncio | D00 |
| 0 | C0116 | `baseline-browser-mapping@2.11.1` | trace-style-targets-then-rewrite | Python 重写/追踪调用面 | D05 |
| 0 | C0117 | `binary-extensions@2.3.0` | stdlib-with-adapter-and-trace | pathlib, glob, os, io | D02 |
| 0 | C0122 | `camelcase-css@2.0.1` | host-rewrite-and-trace | Python 重写/追踪调用面 | D10 |
| 0 | C0123 | `caniuse-lite@1.0.30001806` | trace-style-targets-then-rewrite | Python 重写/追踪调用面 | D05 |
| 0 | C0128 | `clsx@2.1.1` | replace-ui-state-with-python-data | Python 重写/追踪调用面 | D10 |
| 0 | C0130 | `color-name@1.1.4` | candidate-with-adapter | coloraide, stdlib colorsys | D02 |
| 0 | C0131 | `color-name@2.0.2` | candidate-with-adapter | coloraide, stdlib colorsys | D02 |
| 0 | C0133 | `commander@15.0.0` | trace-cli-then-adapt | argparse | D00 |
| 0 | C0134 | `commander@4.1.1` | trace-cli-then-adapt | argparse | D00 |
| 0 | C0135 | `commander@7.2.0` | trace-cli-then-adapt | argparse | D00 |
| 0 | C0136 | `confbox@0.1.8` | trace-icon-resource-then-rewrite | importlib.resources, pathlib, json | D08 |
| 0 | C0137 | `confbox@0.2.2` | trace-icon-resource-then-rewrite | importlib.resources, pathlib, json | D08 |
| 0 | C0138 | `convert-source-map@2.0.0` | trace-compiler-config-then-rewrite | importlib.resources, json | D10 |
| 0 | C0142 | `cssesc@3.0.0` | replace-style-meaning-not-browser-css | Python 重写/追踪调用面 | D05 |
| 0 | C0143 | `csstype@3.2.3` | type-contract | Python 重写/追踪调用面 | TYPES |
| 0 | C0146 | `cytoscape@3.34.0` | retain-graph-and-layout-computation | Python 重写/追踪调用面 | D07 |
| 0 | C0149 | `d3-axis@3.0.0` | rewrite-axis-geometry | Python 重写/追踪调用面 | D06 |
| 0 | C0152 | `d3-color@3.1.0` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 0 | C0155 | `d3-dispatch@3.0.1` | replace-host-control-if-needed | Python 重写/追踪调用面 | D00 |
| 0 | C0158 | `d3-ease@3.0.1` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 0 | C0161 | `d3-format@3.1.0` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 0 | C0163 | `d3-hierarchy@3.1.2` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 0 | C0165 | `d3-path@1.0.9` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 0 | C0166 | `d3-path@3.1.0` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 0 | C0167 | `d3-polygon@3.0.1` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 0 | C0168 | `d3-quadtree@3.0.1` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 0 | C0169 | `d3-random@3.0.1` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 0 | C0173 | `d3-selection@3.0.0` | discard-browser-layer | Python 重写/追踪调用面 | D08 |
| 0 | C0178 | `d3-timer@3.0.1` | replace-host-control-if-needed | Python 重写/追踪调用面 | D00 |
| 0 | C0183 | `dayjs@1.11.21` | stdlib-with-adapter | datetime, zoneinfo, calendar | D02 |
| 0 | C0186 | `didyoumean@1.2.2` | rewrite-used-surface | collections, json, hashlib, re | D00 |
| 0 | C0187 | `dlv@1.1.3` | rewrite-used-surface | collections, json, hashlib, re | D00 |
| 0 | C0189 | `eastasianwidth@0.2.0` | stdlib-with-adapter-and-trace | re, unicodedata | D00 |
| 0 | C0190 | `electron-to-chromium@1.5.396` | trace-style-targets-then-rewrite | Python 重写/追踪调用面 | D05 |
| 0 | C0191 | `elkjs@0.9.3` | reuse-existing-python | py-visactor-elk | D07 |
| 0 | C0192 | `emoji-regex@8.0.0` | stdlib-with-adapter-and-trace | re, unicodedata | D00 |
| 0 | C0193 | `emoji-regex@9.2.2` | stdlib-with-adapter-and-trace | re, unicodedata | D00 |
| 0 | C0194 | `es-errors@1.3.0` | rewrite-used-surface | collections, json, hashlib, re | D00 |
| 0 | C0195 | `es-toolkit@1.45.1` | stdlib-with-adapter | collections, copy, textwrap | D00 |
| 0 | C0196 | `escalade@3.2.0` | trace-compiler-config-then-rewrite | importlib.resources, json | D10 |
| 0 | C0197 | `event-target-shim@5.0.1` | stdlib-with-adapter-and-trace | bytes, base64, struct, zlib, asyncio | D00 |
| 0 | C0198 | `events@3.3.0` | stdlib-with-adapter-and-trace | bytes, base64, struct, zlib, asyncio | D00 |
| 0 | C0199 | `exsolve@1.0.7` | trace-icon-resource-then-rewrite | importlib.resources, pathlib, json | D08 |
| 0 | C0201 | `fast-redact@3.5.0` | stdlib-with-adapter-and-trace | logging, json, io, asyncio | D00 |
| 0 | C0206 | `fsevents@2.3.3` | stdlib-with-adapter-and-trace | pathlib, glob, os, io | D02 |
| 0 | C0207 | `function-bind@1.1.2` | rewrite-used-surface | collections, json, hashlib, re | D00 |
| 0 | C0208 | `gensync@1.0.0-beta.2` | trace-compiler-config-then-rewrite | importlib.resources, json | D10 |
| 0 | C0212 | `globals@15.15.0` | trace-icon-resource-then-rewrite | importlib.resources, pathlib, json | D08 |
| 0 | C0213 | `hachure-fill@0.5.2` | candidate-or-rewrite | rough, svg.path | D01 |
| 0 | C0215 | `highlight.js@11.11.1` | rewrite-used-surface-and-trace | Python 重写/追踪调用面 | D10 |
| 0 | C0216 | `html-to-image@1.11.13` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 0 | C0218 | `ieee754@1.2.1` | stdlib-with-adapter-and-trace | bytes, base64, struct, zlib, asyncio | D00 |
| 0 | C0219 | `immer@10.2.0` | replace-ui-state-with-python-data | Python 重写/追踪调用面 | D10 |
| 0 | C0220 | `internmap@1.0.1` | rewrite-used-surface | Python 重写/追踪调用面 | D00 |
| 0 | C0221 | `internmap@2.0.3` | rewrite-used-surface | Python 重写/追踪调用面 | D00 |
| 0 | C0224 | `is-extglob@2.1.1` | rewrite-used-surface-and-trace | re, fnmatch | D00 |
| 0 | C0225 | `is-fullwidth-code-point@3.0.0` | stdlib-with-adapter-and-trace | re, unicodedata | D00 |
| 0 | C0227 | `is-number@7.0.0` | rewrite-used-surface | collections, json, hashlib, re | D00 |
| 0 | C0228 | `isexe@2.0.0` | trace-platform-then-rewrite | sys, os, asyncio | D00 |
| 0 | C0230 | `jiti@1.21.7` | trace-compiler-config-then-rewrite | importlib.resources, json | D10 |
| 0 | C0232 | `js-tokens@4.0.0` | rewrite-used-surface | collections, json, hashlib, re | D00 |
| 0 | C0234 | `jsesc@3.1.0` | rewrite-used-surface | collections, json, hashlib, re | D00 |
| 0 | C0235 | `json5@2.2.3` | rewrite-used-surface | collections, json, hashlib, re | D00 |
| 0 | C0237 | `khroma@2.1.0` | candidate-with-adapter | coloraide, stdlib colorsys | D02 |
| 0 | C0238 | `kolorist@1.8.0` | trace-icon-resource-then-rewrite | importlib.resources, pathlib, json | D08 |
| 0 | C0240 | `layout-base@1.0.2` | rewrite-used-surface | Python 重写/追踪调用面 | D07 |
| 0 | C0241 | `layout-base@2.0.1` | rewrite-used-surface | Python 重写/追踪调用面 | D07 |
| 0 | C0242 | `lilconfig@3.1.3` | trace-compiler-config-then-rewrite | importlib.resources, json | D10 |
| 0 | C0243 | `lines-and-columns@1.2.4` | trace-compiler-config-then-rewrite | importlib.resources, json | D10 |
| 0 | C0245 | `lodash-es@4.18.1` | stdlib-with-adapter | collections, copy, textwrap | D00 |
| 0 | C0246 | `lodash@4.18.1` | stdlib-with-adapter | collections, copy, textwrap | D00 |
| 0 | C0247 | `lru-cache@10.4.3` | stdlib-with-adapter | collections.OrderedDict, functools | D00 |
| 0 | C0249 | `marked@16.3.0` | candidate-with-adapter | markdown-it-py, mdit-py-plugins | D05 |
| 0 | C0250 | `marked@4.3.0` | candidate-with-adapter | markdown-it-py, mdit-py-plugins | D05 |
| 0 | C0251 | `merge2@1.4.1` | stdlib-with-adapter-and-trace | logging, json, io, asyncio | D00 |
| 0 | C0254 | `minipass@7.1.2` | stdlib-with-adapter-and-trace | logging, json, io, asyncio | D00 |
| 0 | C0256 | `ms@2.1.3` | stdlib-with-adapter-and-trace | logging, json, io, asyncio | D00 |
| 0 | C0258 | `nanoid@3.3.12` | stdlib-with-adapter | secrets | D00 |
| 0 | C0259 | `node-releases@2.0.51` | trace-style-targets-then-rewrite | Python 重写/追踪调用面 | D05 |
| 0 | C0260 | `non-layered-tidy-tree-layout@2.0.2` | rewrite-used-surface | Python 重写/追踪调用面 | D07 |
| 0 | C0261 | `normalize-path@3.0.0` | stdlib-with-adapter-and-trace | pathlib, glob, os, io | D02 |
| 0 | C0262 | `object-assign@4.1.1` | rewrite-used-surface | collections, json, hashlib, re | D00 |
| 0 | C0263 | `object-hash@3.0.0` | rewrite-used-surface | collections, json, hashlib, re | D00 |
| 0 | C0264 | `on-exit-leak-free@2.1.2` | trace-platform-then-rewrite | sys, os, asyncio | D00 |
| 0 | C0265 | `package-json-from-dist@1.0.1` | trace-compiler-config-then-rewrite | importlib.resources, json | D10 |
| 0 | C0266 | `package-manager-detector@1.3.0` | trace-icon-resource-then-rewrite | importlib.resources, pathlib, json | D08 |
| 0 | C0267 | `pako@2.1.0` | stdlib-with-adapter-and-trace | bytes, base64, struct, zlib, asyncio | D00 |
| 0 | C0268 | `path-data-parser@0.1.0` | candidate-or-rewrite | rough, svg.path | D01 |
| 0 | C0269 | `path-key@3.1.1` | stdlib-with-adapter-and-trace | pathlib, glob, os, io | D02 |
| 0 | C0270 | `path-parse@1.0.7` | stdlib-with-adapter-and-trace | pathlib, glob, os, io | D02 |
| 0 | C0272 | `pathe@2.0.3` | stdlib-with-adapter-and-trace | posixpath, pathlib | D02 |
| 0 | C0273 | `picocolors@1.1.1` | stdlib-with-adapter-and-trace | re, unicodedata | D00 |
| 0 | C0274 | `picomatch@2.3.1` | rewrite-used-surface-and-trace | re, fnmatch | D00 |
| 0 | C0275 | `picomatch@2.3.2` | rewrite-used-surface-and-trace | re, fnmatch | D00 |
| 0 | C0276 | `pify@2.3.0` | stdlib-with-adapter-and-trace | logging, json, io, asyncio | D00 |
| 0 | C0278 | `pino-std-serializers@6.2.2` | stdlib-with-adapter-and-trace | logging, io | D00 |
| 0 | C0280 | `pirates@4.0.7` | trace-compiler-config-then-rewrite | importlib.resources, json | D10 |
| 0 | C0282 | `points-on-curve@0.2.0` | candidate-or-rewrite | rough, svg.path | D01 |
| 0 | C0289 | `postcss-value-parser@4.2.0` | replace-style-meaning-not-browser-css | Python 重写/追踪调用面 | D05 |
| 0 | C0291 | `process-warning@3.0.0` | trace-platform-then-rewrite | sys, os, asyncio | D00 |
| 0 | C0292 | `process@0.11.10` | trace-platform-then-rewrite | sys, os, asyncio | D00 |
| 0 | C0293 | `quansync@0.2.11` | trace-icon-resource-then-rewrite | importlib.resources, pathlib, json | D08 |
| 0 | C0294 | `queue-microtask@1.2.3` | stdlib-with-adapter-and-trace | logging, json, io, asyncio | D00 |
| 0 | C0295 | `quick-format-unescaped@4.0.4` | stdlib-with-adapter-and-trace | logging, json, io, asyncio | D00 |
| 0 | C0297 | `react@19.2.5` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 0 | C0301 | `real-require@0.2.0` | trace-compiler-config-then-rewrite | importlib.resources, json | D10 |
| 0 | C0303 | `reusify@1.1.0` | stdlib-with-adapter-and-trace | logging, json, io, asyncio | D00 |
| 0 | C0304 | `robust-predicates@3.0.2` | rewrite-used-surface | Python 重写/追踪调用面 | D01 |
| 0 | C0307 | `rw@1.3.3` | stdlib-with-adapter-and-trace | pathlib, glob, os, io | D02 |
| 0 | C0308 | `safe-buffer@5.2.1` | stdlib-with-adapter-and-trace | bytes, base64, struct, zlib, asyncio | D00 |
| 0 | C0309 | `safe-stable-stringify@2.5.0` | stdlib-with-adapter-and-trace | logging, json, io, asyncio | D00 |
| 0 | C0310 | `safer-buffer@2.1.2` | stdlib-with-adapter-and-trace | bytes, base64, struct, zlib, asyncio | D00 |
| 0 | C0311 | `scheduler@0.27.0` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 0 | C0312 | `semver@6.3.1` | rewrite-used-surface-and-trace | re, fnmatch | D00 |
| 0 | C0314 | `shebang-regex@3.0.0` | trace-platform-then-rewrite | sys, os, asyncio | D00 |
| 0 | C0315 | `signal-exit@4.1.0` | trace-platform-then-rewrite | sys, os, asyncio | D00 |
| 0 | C0317 | `source-map-js@1.2.1` | trace-compiler-config-then-rewrite | importlib.resources, json | D10 |
| 0 | C0318 | `split2@4.2.0` | stdlib-with-adapter-and-trace | logging, json, io, asyncio | D00 |
| 0 | C0319 | `strictdom@1.0.1` | discard-browser-layer | Python 重写/追踪调用面 | D08 |
| 0 | C0325 | `stylis@4.3.6` | replace-style-meaning-not-browser-css | Python 重写/追踪调用面 | D05 |
| 0 | C0327 | `supports-preserve-symlinks-flag@1.0.0` | trace-compiler-config-then-rewrite | importlib.resources, json | D10 |
| 0 | C0328 | `tabbable@6.2.0` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 0 | C0329 | `tailwind-merge@3.5.0` | replace-style-meaning-not-browser-css | Python 重写/追踪调用面 | D05 |
| 0 | C0334 | `tinyexec@1.2.4` | trace-icon-resource-then-rewrite | importlib.resources, pathlib, json | D08 |
| 0 | C0336 | `ts-dedent@2.2.0` | stdlib-with-adapter | collections, copy, textwrap | D00 |
| 0 | C0337 | `ts-interface-checker@0.1.13` | trace-compiler-config-then-rewrite | importlib.resources, json | D10 |
| 0 | C0338 | `tslib@2.8.1` | rewrite-used-surface | Python 重写/追踪调用面 | D00 |
| 0 | C0339 | `ufo@1.6.1` | trace-icon-resource-then-rewrite | importlib.resources, pathlib, json | D08 |
| 0 | C0341 | `util-deprecate@1.0.2` | stdlib-with-adapter-and-trace | logging, json, io, asyncio | D00 |
| 0 | C0342 | `uuid@14.0.0` | stdlib-with-adapter | uuid | D00 |
| 0 | C0343 | `vscode-jsonrpc@9.0.2` | trace-parser-services-then-rewrite | Python 重写/追踪调用面 | D04 |
| 0 | C0344 | `vscode-jsonrpc@9.0.3` | trace-parser-services-then-rewrite | Python 重写/追踪调用面 | D04 |
| 0 | C0347 | `vscode-languageserver-textdocument@1.0.15` | trace-parser-services-then-rewrite | Python 重写/追踪调用面 | D04 |
| 0 | C0348 | `vscode-languageserver-types@3.18.3` | trace-parser-services-then-rewrite | Python 重写/追踪调用面 | D04 |
| 0 | C0349 | `vscode-languageserver-types@3.18.4` | trace-parser-services-then-rewrite | Python 重写/追踪调用面 | D04 |
| 0 | C0351 | `vscode-uri@3.1.0` | trace-parser-services-then-rewrite | Python 重写/追踪调用面 | D04 |
| 0 | C0360 | `yallist@3.1.1` | stdlib-with-adapter | collections.OrderedDict, functools | D00 |
| 0 | C0361 | `yaml@2.8.4` | candidate-with-adapter | PyYAML (pure Python Loader) | D02 |
| 1 | C0001 | `@antfu/install-pkg@1.1.0` | trace-icon-resource-then-rewrite | importlib.resources, pathlib, json | D08 |
| 1 | C0003 | `@babel/code-frame@7.29.7` | trace-then-rewrite-surface | Python 重写/追踪调用面 | D10 |
| 1 | C0017 | `@babel/types@7.29.7` | trace-then-rewrite-surface | Python 重写/追踪调用面 | D10 |
| 1 | C0020 | `@chevrotain/gast@13.2.0` | candidate-or-rewrite | lark | D04 |
| 1 | C0024 | `@floating-ui/core@1.7.3` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 1 | C0039 | `@jridgewell/trace-mapping@0.3.31` | trace-then-rewrite-surface | Python 重写/追踪调用面 | D10 |
| 1 | C0051 | `@napi-rs/canvas@0.1.100` | discard-alternate-renderer | py-skia-canvas | D08 |
| 1 | C0062 | `@react-types/shared@3.32.0(react@19.2.5)` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 1 | C0063 | `@swc/helpers@0.5.17` | rewrite-used-surface | Python 重写/追踪调用面 | D00 |
| 1 | C0067 | `@types/d3-axis@3.0.6` | type-contract | Python 重写/追踪调用面 | TYPES |
| 1 | C0068 | `@types/d3-brush@3.0.6` | type-contract | Python 重写/追踪调用面 | TYPES |
| 1 | C0071 | `@types/d3-contour@3.0.6` | type-contract | Python 重写/追踪调用面 | TYPES |
| 1 | C0074 | `@types/d3-drag@3.0.7` | type-contract | Python 重写/追踪调用面 | TYPES |
| 1 | C0077 | `@types/d3-fetch@3.0.7` | type-contract | Python 重写/追踪调用面 | TYPES |
| 1 | C0080 | `@types/d3-geo@3.1.0` | type-contract | Python 重写/追踪调用面 | TYPES |
| 1 | C0082 | `@types/d3-interpolate@3.0.4` | type-contract | Python 重写/追踪调用面 | TYPES |
| 1 | C0088 | `@types/d3-scale@4.0.9` | type-contract | Python 重写/追踪调用面 | TYPES |
| 1 | C0090 | `@types/d3-shape@3.1.8` | type-contract | Python 重写/追踪调用面 | TYPES |
| 1 | C0094 | `@types/d3-transition@3.0.9` | type-contract | Python 重写/追踪调用面 | TYPES |
| 1 | C0098 | `@types/react@19.2.15` | type-contract | Python 重写/追踪调用面 | TYPES |
| 1 | C0102 | `abort-controller@3.0.0` | stdlib-with-adapter-and-trace | bytes, base64, struct, zlib, asyncio | D00 |
| 1 | C0110 | `anymatch@3.1.3` | rewrite-used-surface-and-trace | re, fnmatch | D00 |
| 1 | C0118 | `brace-expansion@2.1.0` | rewrite-used-surface-and-trace | re, fnmatch | D00 |
| 1 | C0120 ↻ | `browserslist@4.28.7` | trace-style-targets-then-rewrite | Python 重写/追踪调用面 | D05 |
| 1 | C0120 ↻ | `update-browserslist-db@1.2.3(browserslist@4.28.7)` | trace-style-targets-then-rewrite | Python 重写/追踪调用面 | D05 |
| 1 | C0121 | `buffer@6.0.3` | stdlib-with-adapter-and-trace | bytes, base64, struct, zlib, asyncio | D00 |
| 1 | C0127 | `class-variance-authority@0.7.1` | replace-ui-state-with-python-data | Python 重写/追踪调用面 | D10 |
| 1 | C0129 | `color-convert@2.0.1` | candidate-with-adapter | coloraide, stdlib colorsys | D02 |
| 1 | C0132 | `color-string@2.1.4` | candidate-with-adapter | coloraide, stdlib colorsys | D02 |
| 1 | C0139 | `cose-base@1.0.3` | rewrite-used-surface | Python 重写/追踪调用面 | D07 |
| 1 | C0140 | `cose-base@2.2.0` | rewrite-used-surface | Python 重写/追踪调用面 | D07 |
| 1 | C0147 | `d3-array@2.12.1` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 1 | C0148 | `d3-array@3.2.4` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 1 | C0151 | `d3-chord@3.0.1` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 1 | C0156 | `d3-drag@3.0.0` | discard-browser-layer | Python 重写/追踪调用面 | D08 |
| 1 | C0160 | `d3-force@3.0.0` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 1 | C0164 | `d3-interpolate@3.0.1` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 1 | C0174 | `d3-shape@1.3.7` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 1 | C0175 | `d3-shape@3.2.0` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 1 | C0184 | `debug@4.4.3` | stdlib-with-adapter-and-trace | logging, io | D00 |
| 1 | C0185 | `delaunator@5.0.1` | rewrite-used-surface | Python 重写/追踪调用面 | D01 |
| 1 | C0188 | `dompurify@3.4.12` | replace-security-behavior-not-dom | html, urllib.parse | D05 |
| 1 | C0202 | `fastdom@1.0.12(patch_hash=10bad52c2ff6c742f43492850f2a5a74e9d70a33f42a442cdbda4e174356aa87)` | discard-browser-layer | Python 重写/追踪调用面 | D08 |
| 1 | C0203 | `fastq@1.19.1` | stdlib-with-adapter-and-trace | logging, json, io, asyncio | D00 |
| 1 | C0214 | `hasown@2.0.4` | rewrite-used-surface | collections, json, hashlib, re | D00 |
| 1 | C0217 | `iconv-lite@0.6.3` | stdlib-with-adapter-and-trace | codecs | D00 |
| 1 | C0222 | `is-binary-path@2.1.0` | stdlib-with-adapter-and-trace | pathlib, glob, os, io | D02 |
| 1 | C0226 | `is-glob@4.0.3` | rewrite-used-surface-and-trace | re, fnmatch | D00 |
| 1 | C0233 | `js-yaml@4.3.0` | candidate-with-adapter | PyYAML (pure Python Loader) | D02 |
| 1 | C0236 | `katex@0.18.11` | candidate-and-layout-rewrite | latex2mathml | D08 |
| 1 | C0248 | `lru-cache@5.1.1` | stdlib-with-adapter | collections.OrderedDict, functools | D00 |
| 1 | C0255 ↻ | `mlly@1.8.0` | trace-icon-resource-then-rewrite | importlib.resources, pathlib, json | D08 |
| 1 | C0255 ↻ | `pkg-types@1.3.1` | trace-icon-resource-then-rewrite | importlib.resources, pathlib, json | D08 |
| 1 | C0271 | `path-scurry@1.11.1` | stdlib-with-adapter-and-trace | pathlib, glob, os, io | D02 |
| 1 | C0281 | `pkg-types@2.3.0` | trace-icon-resource-then-rewrite | importlib.resources, pathlib, json | D08 |
| 1 | C0283 | `points-on-path@0.2.1` | candidate-or-rewrite | rough, svg.path | D01 |
| 1 | C0288 | `postcss-selector-parser@6.1.2` | replace-style-meaning-not-browser-css | Python 重写/追踪调用面 | D05 |
| 1 | C0290 | `postcss@8.5.15` | replace-style-meaning-not-browser-css | Python 重写/追踪调用面 | D05 |
| 1 | C0296 | `react-dom@19.2.5(react@19.2.5)` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 1 | C0298 | `read-cache@1.0.0` | trace-compiler-config-then-rewrite | importlib.resources, json | D10 |
| 1 | C0300 | `readdirp@3.6.0` | stdlib-with-adapter-and-trace | pathlib, glob, os, io | D02 |
| 1 | C0306 | `run-parallel@1.2.0` | stdlib-with-adapter-and-trace | logging, json, io, asyncio | D00 |
| 1 | C0313 | `shebang-command@2.0.0` | trace-platform-then-rewrite | sys, os, asyncio | D00 |
| 1 | C0316 | `sonic-boom@3.8.1` | stdlib-with-adapter-and-trace | logging, io | D00 |
| 1 | C0322 | `string_decoder@1.3.0` | stdlib-with-adapter-and-trace | codecs | D00 |
| 1 | C0323 | `strip-ansi@6.0.1` | stdlib-with-adapter-and-trace | re, unicodedata | D00 |
| 1 | C0324 | `strip-ansi@7.1.2` | stdlib-with-adapter-and-trace | re, unicodedata | D00 |
| 1 | C0332 | `thenify@3.3.1` | stdlib-with-adapter-and-trace | logging, json, io, asyncio | D00 |
| 1 | C0333 | `thread-stream@2.7.0` | stdlib-with-adapter-and-trace | logging, io | D00 |
| 1 | C0335 | `to-regex-range@5.0.1` | rewrite-used-surface-and-trace | re, fnmatch | D00 |
| 1 | C0340 | `use-sync-external-store@1.5.0(react@19.2.5)` | replace-ui-state-with-python-data | Python 重写/追踪调用面 | D10 |
| 1 | C0345 | `vscode-languageserver-protocol@3.18.3` | trace-parser-services-then-rewrite | Python 重写/追踪调用面 | D04 |
| 1 | C0346 | `vscode-languageserver-protocol@3.18.4` | trace-parser-services-then-rewrite | Python 重写/追踪调用面 | D04 |
| 1 | C0352 | `which@2.0.2` | trace-platform-then-rewrite | sys, os, asyncio | D00 |
| 1 | C0357 | `workspace:packages/parser` | candidate-or-rewrite | lark | D04 |
| 2 | C0007 | `@babel/helper-compilation-targets@7.29.7` | trace-then-rewrite-surface | Python 重写/追踪调用面 | D10 |
| 2 | C0014 | `@babel/parser@7.29.7` | trace-then-rewrite-surface | Python 重写/追踪调用面 | D10 |
| 2 | C0019 | `@chevrotain/cst-dts-gen@13.2.0` | candidate-or-rewrite | lark | D04 |
| 2 | C0025 | `@floating-ui/dom@1.7.4` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 2 | C0035 | `@jridgewell/gen-mapping@0.3.13` | trace-then-rewrite-surface | Python 重写/追踪调用面 | D10 |
| 2 | C0052 | `@nodelib/fs.scandir@2.1.5` | stdlib-with-adapter-and-trace | pathlib, glob, os, io | D02 |
| 2 | C0058 | `@react-aria/ssr@3.9.10(react@19.2.5)` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 2 | C0060 | `@react-stately/flags@3.1.2` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 2 | C0061 | `@react-stately/utils@3.10.8(react@19.2.5)` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 2 | C0064 | `@tanstack/react-virtual@3.13.12(react-dom@19.2.5(react@19.2.5))(react@19.2.5)` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 2 | C0095 | `@types/d3-zoom@3.0.8` | type-contract | Python 重写/追踪调用面 | TYPES |
| 2 | C0106 | `ansi-styles@4.3.0` | stdlib-with-adapter-and-trace | re, unicodedata | D00 |
| 2 | C0141 | `cross-spawn@7.0.6` | trace-platform-then-rewrite | sys, os, asyncio | D00 |
| 2 | C0144 | `cytoscape-cose-bilkent@4.1.0(cytoscape@3.34.0)` | rewrite-used-surface | Python 重写/追踪调用面 | D07 |
| 2 | C0145 | `cytoscape-fcose@2.2.0(cytoscape@3.34.0)` | rewrite-used-surface | Python 重写/追踪调用面 | D07 |
| 2 | C0153 | `d3-contour@4.0.2` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 2 | C0154 | `d3-delaunay@6.0.4` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 2 | C0157 | `d3-dsv@3.0.1` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 2 | C0162 | `d3-geo@3.1.1` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 2 | C0170 | `d3-sankey@0.12.3` | rewrite-used-surface | Python 重写/追踪调用面 | D07 |
| 2 | C0171 | `d3-scale-chromatic@3.1.0` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 2 | C0177 | `d3-time@3.1.0` | stdlib-with-adapter | datetime, zoneinfo, calendar | D02 |
| 2 | C0179 | `d3-transition@3.0.1(d3-selection@3.0.0)` | discard-browser-layer | Python 重写/追踪调用面 | D08 |
| 2 | C0204 | `fill-range@7.1.1` | rewrite-used-surface-and-trace | re, fnmatch | D00 |
| 2 | C0209 | `glob-parent@5.1.2` | stdlib-with-adapter-and-trace | pathlib, glob, os, io | D02 |
| 2 | C0210 | `glob-parent@6.0.2` | stdlib-with-adapter-and-trace | pathlib, glob, os, io | D02 |
| 2 | C0223 | `is-core-module@2.16.1` | rewrite-used-surface-and-trace | re, fnmatch | D00 |
| 2 | C0244 | `local-pkg@1.1.2` | trace-icon-resource-then-rewrite | importlib.resources, pathlib, json | D08 |
| 2 | C0253 | `minimatch@9.0.5` | rewrite-used-surface-and-trace | re, fnmatch | D00 |
| 2 | C0285 | `postcss-js@4.0.1(postcss@8.5.15)` | replace-style-meaning-not-browser-css | Python 重写/追踪调用面 | D05 |
| 2 | C0286 | `postcss-load-config@4.0.2(postcss@8.5.15)` | replace-style-meaning-not-browser-css | Python 重写/追踪调用面 | D05 |
| 2 | C0287 | `postcss-nested@6.2.0(postcss@8.5.15)` | replace-style-meaning-not-browser-css | Python 重写/追踪调用面 | D05 |
| 2 | C0299 | `readable-stream@4.7.0` | stdlib-with-adapter-and-trace | logging, json, io, asyncio | D00 |
| 2 | C0305 | `roughjs@4.6.6(patch_hash=3543d47108cb41b68ec6a671c0e1f9d0cfe2ce524fea5b0992511ae84c3c6b64)` | candidate-or-rewrite | rough, svg.path | D01 |
| 2 | C0320 | `string-width@4.2.3` | stdlib-with-adapter-and-trace | re, unicodedata | D00 |
| 2 | C0321 | `string-width@5.1.2` | stdlib-with-adapter-and-trace | re, unicodedata | D00 |
| 2 | C0331 | `thenify-all@1.6.0` | stdlib-with-adapter-and-trace | logging, json, io, asyncio | D00 |
| 2 | C0350 | `vscode-languageserver@10.1.1` | trace-parser-services-then-rewrite | Python 重写/追踪调用面 | D04 |
| 3 | C0006 | `@babel/generator@7.29.7` | trace-then-rewrite-surface | Python 重写/追踪调用面 | D10 |
| 3 | C0015 | `@babel/template@7.29.7` | trace-then-rewrite-surface | Python 重写/追踪调用面 | D10 |
| 3 | C0026 | `@floating-ui/react-dom@2.1.6(react-dom@19.2.5(react@19.2.5))(react@19.2.5)` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 3 | C0033 | `@iconify/utils@3.0.2` | retain-offline-icon-data-and-geometry | xml.etree.ElementTree, svg.path | D08 |
| 3 | C0036 | `@jridgewell/remapping@2.3.5` | trace-then-rewrite-surface | Python 重写/追踪调用面 | D10 |
| 3 | C0054 | `@nodelib/fs.walk@1.2.8` | stdlib-with-adapter-and-trace | pathlib, glob, os, io | D02 |
| 3 | C0059 | `@react-aria/utils@3.30.1(react-dom@19.2.5(react@19.2.5))(react@19.2.5)` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 3 | C0096 | `@types/d3@7.4.3` | type-contract | Python 重写/追踪调用面 | TYPES |
| 3 | C0100 | `@upsetjs/venn.js@2.0.0` | rewrite-used-surface | Python 重写/追踪调用面 | D07 |
| 3 | C0119 | `braces@3.0.3` | rewrite-used-surface-and-trace | re, fnmatch | D00 |
| 3 | C0125 | `chevrotain@13.2.0` | candidate-or-rewrite | lark | D04 |
| 3 | C0150 | `d3-brush@3.0.0` | discard-browser-layer | Python 重写/追踪调用面 | D08 |
| 3 | C0159 | `d3-fetch@3.0.1` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 3 | C0176 | `d3-time-format@4.1.0` | stdlib-with-adapter | datetime, zoneinfo, calendar | D02 |
| 3 | C0180 | `d3-zoom@3.0.0` | discard-browser-layer | Python 重写/追踪调用面 | D08 |
| 3 | C0205 | `foreground-child@3.3.1` | trace-platform-then-rewrite | sys, os, asyncio | D00 |
| 3 | C0257 | `mz@2.7.0` | stdlib-with-adapter-and-trace | logging, json, io, asyncio | D00 |
| 3 | C0277 | `pino-abstract-transport@1.2.0` | stdlib-with-adapter-and-trace | logging, io | D00 |
| 3 | C0302 | `resolve@1.22.12` | trace-compiler-config-then-rewrite | importlib.resources, json | D10 |
| 3 | C0358 | `wrap-ansi@7.0.0` | stdlib-with-adapter-and-trace | re, unicodedata | D00 |
| 3 | C0359 | `wrap-ansi@8.1.0` | stdlib-with-adapter-and-trace | re, unicodedata | D00 |
| 4 | C0013 | `@babel/helpers@7.29.7` | trace-then-rewrite-surface | Python 重写/追踪调用面 | D10 |
| 4 | C0016 | `@babel/traverse@7.29.7` | trace-then-rewrite-surface | Python 重写/追踪调用面 | D10 |
| 4 | C0027 | `@floating-ui/react@0.26.28(react-dom@19.2.5(react@19.2.5))(react@19.2.5)` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 4 | C0028 | `@floating-ui/react@0.27.16(react-dom@19.2.5(react@19.2.5))(react@19.2.5)` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 4 | C0034 | `@isaacs/cliui@8.0.2` | trace-cli-then-adapt | argparse | D00 |
| 4 | C0057 | `@react-aria/interactions@3.25.5(react-dom@19.2.5(react@19.2.5))(react@19.2.5)` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 4 | C0124 | `chevrotain-allstar@0.5.0(chevrotain@13.2.0)` | candidate-or-rewrite | lark | D04 |
| 4 | C0126 | `chokidar@3.6.0` | stdlib-with-adapter-and-trace | pathlib, glob, os, io | D02 |
| 4 | C0172 | `d3-scale@4.0.2` | retain-used-computation-only | Python 重写/追踪调用面 | D06 |
| 4 | C0252 | `micromatch@4.0.8` | rewrite-used-surface-and-trace | re, fnmatch | D00 |
| 4 | C0279 | `pino@8.21.0` | stdlib-with-adapter-and-trace | logging, io | D00 |
| 4 | C0284 | `postcss-import@15.1.0(postcss@8.5.15)` | replace-style-meaning-not-browser-css | Python 重写/追踪调用面 | D05 |
| 5 | C0009 | `@babel/helper-module-imports@7.29.7` | trace-then-rewrite-surface | Python 重写/追踪调用面 | D10 |
| 5 | C0056 | `@react-aria/focus@3.21.1(react-dom@19.2.5(react@19.2.5))(react@19.2.5)` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 5 | C0181 | `d3@7.9.0` | split-computation-from-discarded-dom | Python 重写/追踪调用面 | D06 |
| 5 | C0200 | `fast-glob@3.3.3` | stdlib-with-adapter-and-trace | pathlib, glob, os, io | D02 |
| 5 | C0229 | `jackspeak@3.4.3` | trace-cli-then-adapt | argparse | D00 |
| 5 | C0239 | `langium@4.4.0` | candidate-or-rewrite | lark | D04 |
| 6 | C0005 ↻ | `@babel/core@7.29.7` | trace-then-rewrite-surface | Python 重写/追踪调用面 | D10 |
| 6 | C0005 ↻ | `@babel/helper-module-transforms@7.29.7(@babel/core@7.29.7)` | trace-then-rewrite-surface | Python 重写/追踪调用面 | D10 |
| 6 | C0030 | `@headlessui/react@2.2.10(react-dom@19.2.5(react@19.2.5))(react@19.2.5)` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 6 | C0182 | `dagre-d3-es@7.0.14` | excluded-by-user | 不进入目标运行时（用户排除） | D07 |
| 6 | C0211 | `glob@10.4.5` | stdlib-with-adapter-and-trace | pathlib, glob, os, io | D02 |
| 6 | C0355 | `workspace:packages/mermaid-layout-tidy-tree` | assemble-python | Python 重写/追踪调用面 | D09 |
| 7 | C0231 | `jotai@2.19.1(@babel/core@7.29.7)(@babel/template@7.29.7)(@types/react@19.2.15)(react@19.2.5)` | replace-ui-state-with-python-data | Python 重写/追踪调用面 | D10 |
| 7 | C0326 | `sucrase@3.35.0` | trace-compiler-config-then-rewrite | importlib.resources, json | D10 |
| 7 | C0353 | `workspace:packages/mermaid` | assemble-python | Python 重写/追踪调用面 | D09 |
| 7 | C0354 | `workspace:packages/mermaid-layout-elk` | assemble-python | Python 重写/追踪调用面 | D09 |
| 8 | C0330 | `tailwindcss@3.4.19` | replace-style-meaning-not-browser-css | Python 重写/追踪调用面 | D05 |
| 9 | C0031 | `@headlessui/tailwindcss@0.2.2(tailwindcss@3.4.19)` | discard-browser-layer | Python 重写/追踪调用面 | D10 |
| 10 | C0101 | `@zenuml/core@3.49.2(@babel/core@7.29.7)(@babel/template@7.29.7)(@types/react@19.2.15)` | rewrite-semantic-layout-canvas-pipeline | antlr4-python3-runtime | D10 |
| 11 | C0356 | `workspace:packages/mermaid-zenuml` | rewrite-semantic-layout-canvas-pipeline | antlr4-python3-runtime | D10 |
