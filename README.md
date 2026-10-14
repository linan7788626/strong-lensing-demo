# Bending Light — Web 版

[中文](#中文) · [English](#english)

<a id="中文"></a>

**强引力透镜 (strong gravitational lensing) 交互式可视化的零依赖、纯前端实现。**
无需 npm、无需打包工具、无需后端,任何现代浏览器即可运行;推荐通过本地静态服务器访问。

本项目现在包含**三个网页**:

| 页面 | 文件 | 定位 |
| --- | --- | --- |
| 强引力透镜课堂与仿真实验室 | `strong-lensing.html` | **主页面**。SIE 透镜物理 + 三画布联动 + 巡天 Mock 观测仿真 |
| 星系透镜探险小游戏 | `playground.html` | 游戏化闯关:WebGL 实时透镜特效 + 三关挑战 + 成就系统 |
| 多源多透镜实验台(旧版) | `index.html` | NIE 势 + Web Worker 并行的 1:1 桌面版移植,支持 9 源 + 9 透镜 |

---

## 一、强引力透镜课堂与仿真实验室 (`strong-lensing.html`)

面向教学与演示的**物理实验室**:左侧源平面、中间透镜平面、右侧 Mock 观测视场三画布实时联动,下方光路侧视剖面追踪光子路径。

### 物理模型

- **SIE (奇异等温椭球)** 偏折角公式,远场附加高斯软截断 `α·exp(−r²/2r_c²)`(r_c = 2.5θ_E),避免远场不衰减导致的整体画面漂移
- 透镜方程数值求解采用**阻尼牛顿迭代**(残差种子域扫描 + 中心差分雅可比 + 半步回退),稳定命中 4 像 / 2 像 / 1 像拓扑(含鞍点简并情形)
- 源光分布为高斯椭圆源;可选叠加 **Sérsic 轮廓透镜光**(b_n 近似 + 流量归一化)

### 三画布联动

| 画布 | 内容 |
| --- | --- |
| 源平面 β-空间 | 高斯源(等高线)、焦散线映射、直接拖拽移动源心 |
| 透镜平面像平面 | 临界曲线(红实线, det A = 0)、焦散线(紫实线)、像位置 + 放大率 μ 标注、半光等高线(虚线)、直接拖拽移动透镜 |
| Mock 巡天视场 | 巡天仪器真实观测仿真(见下) |

- **预设形态一键切换**:爱因斯坦十字 (Cross) / 爱因斯坦环 (Ring) / 尖点折叠长弧 (Cusp) / 经典双像 (Double)
- 参数滑块:源位置/星等 m_AB/尺寸/轴比/方位角,透镜 θ_E(0.5–6″)/轴比 q/方位角/星等;滑块带实时填充色
- 画布顶部徽标实时显示像数、极大局部放大率 μ、爱因斯坦半径 θ_E、当前仪器

### Mock 巡天观测仿真

内置 6 台真实巡天仪器参数(像元尺度、口径、三波段 PSF、曝光时间、天光、读出噪声):
**CSST / HST (ACS+WFC3) / JWST (NIRCam) / Euclid / Roman (WFIRST) / HSC (Subaru)**

- 噪声标定两种模式:**仪器参数 (Poisson + 读出)** 与 **极限星等 (Gaussian)**
- 波段三通道独立成像 → **稀疏 PSF 卷积**(文件实测 PSF 核,边缘锥化消除方形伪影)→ asinh 灰度拉伸 → RGB 合成
- 每像素 SNR 实时估计;初始为**理想无噪像**,点击「应用仪器效应」后叠加完整仪器链
- 渲染单位可选 electron (e⁻) / flux (Jy)

### 性能

渲染采用分层缓存(临界/焦散曲线、像面网格、像求解、源平面网格按依赖拆分缓存)+ 滑块 `requestAnimationFrame` 合批,拖拽交互单帧约 12–15 ms。

---

## 二、星系透镜探险小游戏 (`playground.html`)

WebGL 实时引力透镜**游戏化闯关**页面,底图即被透镜扭曲的对象:

1. **第一关 · 宇宙深场** — 哈勃极深场 (HUDF) 官方原图,寻找中央星系拖拽扭曲
2. **第二关 · 星际风景** — 雪山风光,制造折叠弯曲的地表地平线虫洞
3. **第三关 · 引力自拍** — 魔性大头火柴人,把透镜拖至面部制造哈哈镜外星人

### 玩法与功能

- 画布内**按住并拖动**即可移动透镜,实时 WebGL 渲染(60 FPS HUD 显示)
- 右侧「透镜物理魔杖」:θ_E / 轴比 q / 方位角 PA 三个滑块 + 对称圆环/拉伸长弧预设 + 一键还原
- **上传自定义图片**作为底图;**导出作品**即通关点亮关卡星星
- 三星收集进度、全通关成就弹窗(并可一键跳转进入 `strong-lensing.html` 物理实验室)
- 内置合成音效(可静音)

---

## 三、多源多透镜实验台 (`index.html`,旧版)

原桌面版 `bending_light_cython`(PyQt + Cython/C)与参考实现 `libs/all_cv_test.c` 的**网页端 1:1 移植**。数值管线 —— NIE (Navarro–Frank–White–like elliptical) 势偏折、高斯光源、临界曲线符号变化检测、CIC 焦散线沉积 —— 与 C 原版逐行对应,并已通过参考测试套件 `../bending_light_jax/tests` **逐像素验证**(掩码 0 像素差异,浮点场误差 ≤ 1e-14)。

### 核心特性

- 🪐 NIE 椭球势、临界曲线、焦散线
- ⚡ 多 Web Worker 并行(按行分带);`file://` 下自动回退主线程
- 🖱️ 最多 9 源 + 9 透镜,鼠标 + 键盘联合编辑

### 交互速查

| 操作 | 效果 |
| --- | --- |
| `数字`+`W`+左键 / 右键拖 | 移动源 / 透镜(一一对应) |
| `数字`+`S`+拖 | 改源大小 / 纵向=θ_E,横向=核半径·光度 |
| `数字`+`E`+拖 | 横向=方位角,纵向=椭率/轴比 |
| `=` + 左/右键 | 添加新源 / 新透镜;`-`+右键删除最后一组 |
| `F` / `G` (按住) | 显示透镜形状轮廓 / 透镜光度 |

实现要点:物理引擎以字符串嵌入 (`<script id="phys-src">`) 派生 Worker;`[row, col]` row-major 数组布局与 C 约定一致;周期性边界保留;脏标记 + `requestAnimationFrame` 调度。

---

## 运行方式

```bash
# 进入项目目录
cd strong-lensing-demo

# Python 3
python3 -m http.server 8000

# 或 Node.js (任选其一)
npx http-server -p 8000

# 浏览器访问
# http://localhost:8000/strong-lensing.html   ← 物理实验室
# http://localhost:8000/playground.html       ← 探险小游戏
# http://localhost:8000/index.html            ← 旧版实验台
```

三个页面均为单文件自包含实现,也可直接双击打开(`file://` 协议下个别功能可能受浏览器同源策略限制,建议本地服务器方式)。

## 目录结构

```
strong-lensing-demo/
├── strong-lensing.html   # 强引力透镜课堂与仿真实验室(SIE,单文件自包含)
├── playground.html       # 星系透镜探险小游戏(WebGL,单文件自包含)
├── index.html            # 旧版多源多透镜实验台(NIE + Web Worker)
├── hudf.jpg              # playground 底图备份(哈勃极深场)
└── *.html.bak*           # 历史版本备份(可安全删除)
```

## 相关仓库

| 名称 | 描述 |
| --- | --- |
| `bending_light_cython` | 桌面 PyQt + Cython 原版 |
| `bending_light_jax` | JAX 参考实现 + 逐像素回归测试 |
| `libs/all_cv_test.c` | 物理引擎 C 参考实现 |

## License

See the upstream `bending_light_cython` project for licensing terms.

---

<a id="english"></a>

# Bending Light — Web Edition

**A zero-dependency, pure-frontend interactive visualizer for strong gravitational lensing.**
No npm, no bundler, no backend — runs in any modern browser; a local static server is recommended.

The project now ships **three web pages**:

| Page | File | Role |
| --- | --- | --- |
| Strong Lensing Classroom & Simulation Lab | `strong-lensing.html` | **Main page**. SIE lens physics + three linked canvases + survey Mock observation |
| Cosmic Lensing Quest (game) | `playground.html` | Gamified WebGL lensing challenges + 3 levels + achievements |
| Multi-source Multi-lens Bench (legacy) | `index.html` | 1:1 web port of the desktop version (NIE + Web Workers), 9 sources + 9 lenses |

---

## 1. Strong Lensing Classroom & Simulation Lab (`strong-lensing.html`)

A **physics laboratory** for teaching and demonstration: source plane, lens plane, and Mock survey field are three canvases linked in real time, with a side-view ray-tracing panel tracking photon paths below.

### Physics Model

- **SIE (Singular Isothermal Ellipsoid)** deflection with a far-field Gaussian soft truncation `α·exp(−r²/2r_c²)` (r_c = 2.5θ_E), preventing global frame drift from non-decaying far-field deflection
- The lens equation is solved by **damped Newton iteration** (residual-seed domain scan + central-difference Jacobian + step-halving fallback), robustly recovering 4-image / 2-image / 1-image topologies (including saddle-point degeneracies)
- Sources are elliptical Gaussians; an optional **Sérsic lens light** can be superposed (b_n approximation + flux normalization)

### Three Linked Canvases

| Canvas | Contents |
| --- | --- |
| Source plane (β-space) | Gaussian source (contours), caustic mapping, drag to move the source |
| Lens plane (image plane) | Critical curve (red solid, det A = 0), caustics (purple solid), image positions + magnifications μ, half-light contours (dashed), drag to move the lens |
| Mock survey field | Realistic survey observation simulation (see below) |

- **One-click morphology presets**: Einstein Cross / Einstein Ring / Cusp (folded arcs) / Classic Double
- Sliders: source position / m_AB / size / axis ratio / PA; lens θ_E (0.5–6″) / axis ratio q / PA / magnitude — all with live track fill
- Badges above each canvas show image count, maximum local magnification μ, Einstein radius θ_E, and the current instrument

### Mock Survey Observation

Six real survey instruments are built in (pixel scale, aperture, 3-band PSFs, exposure, sky, read noise):
**CSST / HST (ACS+WFC3) / JWST (NIRCam) / Euclid / Roman (WFIRST) / HSC (Subaru)**

- Two noise calibration modes: **instrument parameters (Poisson + read noise)** and **limiting magnitude (Gaussian)**
- Three-band imaging → **sparse PSF convolution** (measured PSF kernels with edge apodization to remove square artifacts) → asinh stretch → RGB composite
- Per-pixel SNR estimation; starts as an **ideal noiseless image** — click "Apply Instrument Effects" to superpose the full survey pipeline
- Display units: electron (e⁻) or flux (Jy)

### Performance

Layered render caches (critical/caustic curves, image-plane mesh, image solver, source-plane grid cached by dependency) + slider `requestAnimationFrame` batching keep drag interactions at roughly 12–15 ms per frame.

---

## 2. Cosmic Lensing Quest (`playground.html`)

A **gamified** real-time WebGL lensing page where the background image itself is lensed:

1. **Level 1 · Cosmic Deep Field** — the official Hubble Ultra Deep Field; find and distort the central galaxy
2. **Level 2 · Interstellar Scenery** — a snowy mountain landscape; fold the horizon into a wormhole
3. **Level 3 · Gravitational Selfie** — a stick figure; drag the lens onto the face for a funhouse-alien effect

### Gameplay & Features

- **Press and drag** inside the canvas to move the lens, rendered in real-time WebGL (60 FPS HUD)
- "Lens Physics Wand" panel: θ_E / axis ratio q / PA sliders + circular-ring / stretched-arc presets + one-click reset
- **Upload custom images** as the background; **export your artwork** to complete a level and earn its star
- Three-star collection progress and a full-completion achievement dialog (with a shortcut into the `strong-lensing.html` physics lab)
- Built-in synthesized sound effects (mutable)

---

## 3. Multi-source Multi-lens Bench (`index.html`, legacy)

A **1:1 web port** of the desktop application `bending_light_cython` (PyQt + Cython/C) and the reference C source `libs/all_cv_test.c`. The numerical pipeline — NIE (Navarro–Frank–White–like elliptical) deflection, Gaussian sources, critical-curve detection via magnification sign changes, and CIC caustic deposition — matches the C original **line by line**, and has been verified pixel-by-pixel against the reference suite `../bending_light_jax/tests` (mask: 0 pixel difference; floating-point fields: ≤ 1e-14).

### Key Features

- 🪐 NIE elliptical potential, critical curves, caustics
- ⚡ Multi-Web-Worker parallelism (strip-parallel); automatic main-thread fallback under `file://`
- 🖱️ Up to 9 sources + 9 lenses, edited with mouse + keyboard

### Interaction Cheat Sheet

| Action | Effect |
| --- | --- |
| `digit`+`W`+LMB / RMB drag | Move source / lens (1-to-1) |
| `digit`+`S`+drag | Source size / vertical = θ_E, horizontal = core radius · brightness |
| `digit`+`E`+drag | Horizontal = position angle, vertical = ellipticity / axis ratio |
| `=` + LMB / RMB | Add a source / lens; `-`+RMB removes the last pair |
| `F` / `G` (hold) | Lens shape contours / lens surface brightness |

Implementation notes: the physics engine is embedded as a string (`<script id="phys-src">`) and spawned into Workers; `[row, col]` row-major layout matches the C convention; periodic boundaries are preserved; dirty-flag rendering is scheduled via `requestAnimationFrame`.

---

## Running

```bash
cd strong-lensing-demo

# Python 3
python3 -m http.server 8000

# Or Node.js (either one)
npx http-server -p 8000

# Visit
# http://localhost:8000/strong-lensing.html   ← physics lab
# http://localhost:8000/playground.html       ← lensing game
# http://localhost:8000/index.html            ← legacy bench
```

All three pages are self-contained single files and can also be opened by double-click (some features may be restricted by same-origin policy under `file://`; a local server is preferred).

## Directory Layout

```
strong-lensing-demo/
├── strong-lensing.html   # Strong lensing classroom & simulation lab (SIE, single file)
├── playground.html       # Cosmic Lensing Quest game (WebGL, single file)
├── index.html            # Legacy multi-source bench (NIE + Web Workers)
├── hudf.jpg              # Backup background image for playground (HUDF)
└── *.html.bak*           # Historical backups (safe to delete)
```

## Related Repositories

| Repository | Description |
| --- | --- |
| `bending_light_cython` | Original desktop PyQt + Cython implementation |
| `bending_light_jax` | JAX reference implementation + per-pixel regression tests |
| `libs/all_cv_test.c` | Reference C implementation of the physics engine |

## License

See the upstream `bending_light_cython` project for licensing terms.
