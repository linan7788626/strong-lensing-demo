# Bending Light — Web 版

[English](#english) · [中文](#中文)

---

## 中文

**强引力透镜(strong gravitational lensing)交互式可视化工具的零依赖、纯前端实现。**
整套应用打包在单个 `index.html` 文件里,包含全部物理引擎、渲染管线、交互逻辑与帮助面板;无需 npm、无需打包工具、无需后端,任何现代浏览器双击即可运行。

### 项目背景

本项目是原桌面版 `bending_light_cython`(基于 Cython/C 的 PyQt 应用)以及参考实现 `libs/all_cv_test.c` 的**网页端 1:1 移植**。数值管线 —— 包括 NIE(Navarro–Frank–White–like elliptical)势的偏折计算、高斯光源分布、临界曲线(critical curves)符号变化检测、CIC(cloud-in-cell)焦散线沉积 —— 与 C 原版逐行对应。

正确性已通过参考测试套件 `../bending_light_jax/tests` **逐像素验证**:

- 掩码(mask)输出 **0 像素差异**
- 浮点场输出误差 **≤ 1e-14**

### 核心特性

- 🪐 **真实的引力透镜物理**:NIE 椭球势、临界曲线、焦散线
- ⚡ **多 Web Worker 并行**:数值积分按行分带(strip-parallel)分发给浏览器后台线程
- 🖱️ **丰富的实时交互**:最多 9 个源 + 9 个透镜,鼠标 + 键盘联合编辑
- 🎨 **多种渲染模式**:默认像平面、按住 `F` 显示透镜轮廓 / 按住 `G` 显示透镜光度
- 📦 **零依赖**:无 npm、无 node_modules、无 CDN 依赖,离线可用

### 运行方式

#### 方式一:直接打开(最简单)

双击 `index.html`,浏览器即可加载运行。`file://` 协议下 `Web Worker` 在某些浏览器(尤其 Chrome)会被同源策略限制,此时会自动回退到主线程计算 —— 速度会变慢但功能完全一致。

#### 方式二:本地静态服务器(推荐)

```bash
# 进入项目目录
cd strong-lensing-demo

# Python 3
python3 -m http.server 8000

# 或者 Node.js (任选其一)
npx http-server -p 8000
# npx serve .

# 然后浏览器访问
# http://localhost:8000/
```

### 交互操作速查

页面底部内置与桌面版语义完全一致的中文帮助面板,简表如下:

#### 源 Source(鼠标左键 + 数字键 `1–9`)

| 操作 | 效果 |
| --- | --- |
| `数字` + `W` + 左键(按住/点击) | 源直接跟随鼠标位置(一一对应) |
| `数字` + `S` + 左键上下拖 | 改变源大小 |
| `数字` + `E` + 左键拖动 | 横向=方位角,纵向=椭率 |
| `=` + 左键点击 | 在鼠标处添加新源(最多 9 个) |

#### 透镜 Lens(鼠标右键 + 数字键 `1–9`)

| 操作 | 效果 |
| --- | --- |
| `数字` + `W` + 右键拖动 | 移动透镜 |
| `数字` + `S` + 右键拖动 | 纵向=爱因斯坦半径,横向=核半径/光度幅值 |
| `数字` + `E` + 右键拖动 | 横向=方位角,纵向=轴比 |
| `=` + 右键点击 | 添加新透镜(最多 9 个) |
| `-` + 右键 | 删除最后一个源 + 最后一个透镜(与原版 Cython 行为一致) |

#### 显示 Display

| 操作 | 效果 |
| --- | --- |
| `F`(按住) | 显示透镜形状轮廓 + 源 + 像 |
| `G`(按住) | 显示透镜光度 + 源 + 像 |
| 默认 | 源(白)+ 引力透镜像(蓝) |
| 画布下方圆点开关 | 源(白)/ 焦散线(绿)/ 临界曲线(红)/ 透镜星系图像(橙) |

### 实现要点

- **物理引擎脚本以字符串形式嵌入**(`<script id="phys-src">`),由 `URL.createObjectURL(new Blob(...))` 派生 `Worker` 源;同一段代码在主线程与每个 Worker 中执行。
- **数组布局**:`[row, col]`,其中 `row = x1`(屏幕 y 轴向下),`col = x2`(屏幕 x 轴向右),与 `all_cv_test.c` 的 row-major 约定保持一致。
- **周期性边界**:保留 C 代码的周期环绕(periodic wrap)约定,使迁移不损失边缘数值。
- **脏标记渲染**:交互只置 `dirty` 位,真正积分在 Worker 中异步执行;主线程用 `requestAnimationFrame` 调度,确保交互流畅。

### 相关仓库

| 名称 | 描述 |
| --- | --- |
| `bending_light_cython` | 桌面 PyQt + Cython 原版 |
| `bending_light_jax` | JAX 参考实现 + 逐像素回归测试 |
| `libs/all_cv_test.c` | 物理引擎 C 参考实现 |

---

## English

**A zero-dependency, pure-frontend interactive visualizer for strong gravitational lensing.**
The entire application is packaged in a single `index.html` file — including the physics engine, rendering pipeline, interaction logic, and built-in help panel. No npm, no bundler, no backend; double-click to run in any modern browser.

### Background

This project is a **1:1 web port** of the original desktop application `bending_light_cython` (a Cython/C + PyQt implementation) and the reference C source `libs/all_cv_test.c`. The numerical pipeline — NIE (Navarro–Frank–White–like elliptical) deflection, Gaussian source distributions, critical-curve detection via magnification sign changes, and CIC (cloud-in-cell) caustic deposition — matches the C original **line by line**.

Correctness has been verified pixel-by-pixel against the reference test suite `../bending_light_jax/tests`:

- **Mask output: 0 pixel difference**
- **Floating-point field errors: ≤ 1e-14**

### Key Features

- 🪐 **Realistic lensing physics** — NIE elliptical potential, critical curves, caustics
- ⚡ **Multi-Worker parallelism** — Strip-parallel row decomposition runs on browser background threads
- 🖱️ **Rich real-time interaction** — Up to 9 sources + 9 lenses, edited with mouse + keyboard
- 🎨 **Multiple render modes** — Default image plane; hold `F` for lens contours, `G` for lens surface brightness
- 📦 **Zero dependencies** — No npm, no node_modules, no CDN; works offline

### Running

#### Option 1: Open directly (simplest)

Double-click `index.html`. Under `file://`, some engines may restrict `Web Worker` for same-origin reasons; the app automatically falls back to main-thread computation (slower but fully functional).

#### Option 2: Local static server (recommended)

```bash
cd strong-lensing-demo

# Python 3
python3 -m http.server 8000

# Or Node.js (any one)
npx http-server -p 8000
# npx serve .

# Then visit
# http://localhost:8000/
```

### Interaction Cheat Sheet

A complete help panel is built into the page (semantics identical to the desktop version):

#### Sources (left mouse button + digit `1–9`)

| Action | Effect |
| --- | --- |
| `digit` + `W` + LMB (hold/click) | Source directly tracks mouse position (1-to-1) |
| `digit` + `S` + LMB drag (vertical) | Change source size |
| `digit` + `E` + LMB drag | Horizontal = position angle, Vertical = ellipticity |
| `=` + LMB click | Add source at mouse position (max 9) |

#### Lenses (right mouse button + digit `1–9`)

| Action | Effect |
| --- | --- |
| `digit` + `W` + RMB drag | Move the lens |
| `digit` + `S` + RMB drag | Vertical = Einstein radius, Horizontal = core radius / amplitude |
| `digit` + `E` + RMB drag | Horizontal = position angle, Vertical = axis ratio |
| `=` + RMB click | Add a new lens (max 9) |
| `-` + RMB | Remove the last source and last lens (matches original Cython behavior) |

#### Display

| Action | Effect |
| --- | --- |
| `F` (hold) | Lens shape contours + sources + images |
| `G` (hold) | Lens surface brightness + sources + images |
| Default | Sources (white) + lensed images (blue) |
| Canvas dot toggles | Sources (white) / Caustics (green) / Critical curves (red) / Lens galaxy image (orange) |

### Implementation Notes

- **The physics engine script is embedded as a string** (`<script id="phys-src">`) and dispatched to `Worker`s via `URL.createObjectURL(new Blob(...))`. The same code runs on the main thread and inside every Worker.
- **Array layout**: `[row, col]`, with `row = x1` (vertical, screen y-down) and `col = x2` (horizontal, screen x-right) — matching the row-major convention of `all_cv_test.c`.
- **Periodic boundary**: the C code's periodic-wrap convention is preserved, so edge numerics are unchanged by the port.
- **Dirty-flag rendering**: interactions only set a `dirty` flag; the actual integration runs asynchronously in Workers; the main thread schedules via `requestAnimationFrame` to keep interaction fluid.

### Related Repositories

| Repository | Description |
| --- | --- |
| `bending_light_cython` | Original desktop PyQt + Cython implementation |
| `bending_light_jax` | JAX reference implementation + per-pixel regression tests |
| `libs/all_cv_test.c` | Reference C implementation of the physics engine |

---

### License

See the upstream `bending_light_cython` project for licensing terms.