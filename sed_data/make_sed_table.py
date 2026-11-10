# -*- coding: utf-8 -*-
"""
make_sed_table.py — GalaxyGenius 真实星系 SED → strong-lensing.html 波段权重表生成器

输入: sed_data/lens_source_SEDs_v2/*_galaxy_SEDs.fits
      (BinTable 两列: WAVELENGTH [μm, 观测帧] + FLUX [Jy, f_ν]; 表头 REDSHIFT)

物理处理流程 (对每个星系):
  1) 波长覆盖延拓 (仅覆盖现有 18 个 top-hat 波段所需范围):
     - 透镜 (z=0.298, 覆盖 1298–15573 Å): 红端以平坦 f_ν 外推至 22500 Å,
       覆盖 JWST F200W (至 22100 Å) / Euclid H (至 ~17800 Å) / Roman F158 (至 ~16700 Å)。
       老年星族在 rest ~1.2 μm 处 f_ν 仍缓升, 平坦外推是保守近似 (教学演示可接受)。
     - 源 (z=2.002, 覆盖 3002–36024 Å): 蓝端按幂律 f_ν ∝ λ_rest^γ 外推至观测 2400 Å
       (rest ~799 Å), 幂律在 rest 1001–1250 Å 拟合; 覆盖 HST F275W (至 ~2960 Å)。
  2) 源 SED 乘以 Madau (1995) IGM 平均透射 (透镜 z=0.298 时所有波段都远红于
     Lyα/Lyman 极限的观测位置 1578/1183 Å, 吸收恒为 0, 故只对源施加):
     实现逐行对照 FSPS 的参考实现 igm_absorb.f90 (Conroy et al.):
       - 17 条 Lyman 系线吸收: τ_i = A_i·(λ_obs/λ_i)^3.46, λ_obs < λ_i(1+z)
       - i=1 附加金属线 blanketing 项 a_metal·(λ_obs/1215.67)^1.68 (FSPS 注释: 影响可忽略)
       - Lyman 连续吸收: Madau (1995) Eq.16 分段解析式 (FSPS 同式, 含单调性封顶)
  3) 对 6 台仪器 × 3 个波段的 top-hat 带通做光子加权带内积分:
       I_b = ∫_band f_ν(λ)·dλ/λ        (光子数 ∝ ∫ f_ν dν/(hν), dν/ν = dλ/λ)
     top-hat 带宽取文献带通的对数宽度 w = ln(λ2/λ1), 中心按 CAL 表 λ_eff
     (galaxyGenius 实际仪器曲线的有效波长) 对齐: λ1 = λ_eff·w/(e^w−1), λ2 = λ1·e^w,
     使平坦 f_ν 光谱的光子加权平均波长严格等于 λ_eff — 保证与 HTML 中 Q 定标自洽。
  4) 相对权重 (以每台仪器的中间波段为亮度锚点):
       w_b = (Q_b·I_b) / (Q_mid·I_mid),  中间波段恒为 1
     → HTML 中 bandImage 以 kappa_mid (中间波段 e⁻ 定标) 乘 w_b:
       m_AB / SNR 语义与旧版逐项一致, 跨波段颜色完全由 SED 决定。

输出: ../sed_bands.js (供 strong-lensing.html <script> 引入)
运行: python sed_data/make_sed_table.py  (工作目录任意, 路径相对本文件)
"""

import os
import csv
import base64
import struct
import datetime
import numpy as np
from astropy.io import fits

HERE = os.path.dirname(os.path.abspath(__file__))
SED_DIR = os.path.join(HERE, "lens_source_SEDs_v2")
OUT_JS = os.path.join(HERE, "..", "sed_bands.js")

# ---------------------------------------------------------------------------
# 仪器定标表: 与 strong-lensing.html 中 CAL 常量逐项一致 (Q 为 galaxyGenius
# 真实仪器曲线的总吞吐, lam 为其有效波长 — top-hat 中心按它对齐)
# ---------------------------------------------------------------------------
CAL = {
    "CSST/g": {"lam": 4804.4, "Q": 0.185596}, "CSST/r": {"lam": 6190.2, "Q": 0.149427}, "CSST/z": {"lam": 9032.7, "Q": 0.0698987},
    "HST/UV_F275W": {"lam": 2714.3, "Q": 0.0185643}, "HST/UV_F390W": {"lam": 3934.4, "Q": 0.0568796}, "HST/UV_F814W": {"lam": 8068.0, "Q": 0.0453128},
    "JWST/F070W": {"lam": 7060.3, "Q": 0.054654}, "JWST/F150W": {"lam": 15045.7, "Q": 0.10393}, "JWST/F200W": {"lam": 19922.4, "Q": 0.122304},
    "Euclid/Y": {"lam": 10812.4, "Q": 0.189359}, "Euclid/J": {"lam": 13669.5, "Q": 0.232676}, "Euclid/H": {"lam": 17707.9, "Q": 0.221884},
    "Roman/F087": {"lam": 8719.1, "Q": 0.663456}, "Roman/F129": {"lam": 12936.0, "Q": 0.711075}, "Roman/F158": {"lam": 15791.1, "Q": 0.734048},
    "HSC/g": {"lam": 4809.0, "Q": 0.125344}, "HSC/r": {"lam": 6229.1, "Q": 0.120707}, "HSC/z": {"lam": 8906.2, "Q": 0.0406593},
}

INSTRUMENTS = ["CSST", "HST", "JWST", "Euclid", "Roman", "HSC"]

# top-hat 带通的文献近似范围 [Å]。最终边界 = 对数宽度不变, 中心平移对齐 CAL λ_eff
# (见 make_tophat)。出处 (近似矩形带通):
#   CSST: 巡天设计常用 g/r/i/z/y 划分 (Zhan 2021; CSST 仪器文档)
#   HST:  WFC3/UVIS F275W/F390W/F814W 曲线近似 (WFC3 Instrument Handbook)
#   JWST: NIRCam 宽带 F070W/F150W/F200W 曲线近似 (JWST User Documentation)
#   Euclid: NISP Y/J/H 近似划分 (Euclid Recognition Survey / NISP 滤光片文档)
#   Roman: F087/F129/F158 曲线近似 (Roman/WFIRST 仪器文档)
#   HSC:  Hyper Suprime-Cam g/r/z 近似 (HSC PDR 文档)
BANDPASS_DOC = {
    "CSST":  {"g": (4000.0, 5500.0), "r": (5500.0, 7000.0), "z": (8400.0, 9800.0)},
    "HST":   {"UV_F275W": (2400.0, 2960.0), "UV_F390W": (3480.0, 4380.0), "UV_F814W": (7250.0, 8900.0)},
    "JWST":  {"F070W": (6400.0, 7700.0), "F150W": (13500.0, 16700.0), "F200W": (17800.0, 22100.0)},
    "Euclid": {"Y": (9200.0, 11500.0), "J": (11500.0, 13700.0), "H": (13700.0, 17800.0)},
    "Roman": {"F087": (7980.0, 9460.0), "F129": (11170.0, 13560.0), "F158": (14130.0, 16650.0)},
    "HSC":   {"g": (4000.0, 5600.0), "r": (5800.0, 7300.0), "z": (7800.0, 9000.0)},
}

# ---------------------------------------------------------------------------
# Madau (1995) IGM 平均透射 — 与 FSPS src/igm_absorb.f90 逐项对照的移植
# ---------------------------------------------------------------------------
LYW = np.array([1215.67, 1025.72, 972.537, 949.743, 937.803,
                930.748, 926.226, 923.150, 920.963, 919.352,
                918.129, 917.181, 916.429, 915.824, 915.329,
                914.919, 914.576])
LYCOEFF = np.array([0.0036, 0.0017, 0.0011846, 0.0009410, 0.0007960,
                    0.0006967, 0.0006236, 0.0005665, 0.0005200, 0.0004817,
                    0.0004487, 0.0004200, 0.0003947, 0.000372, 0.000352,
                    0.0003334, 0.00031644])
LYLIM = 911.75      # Lyman 极限 [Å]
A_METAL = 0.0017    # Lyα 处金属线 blanketing (FSPS: ~无影响, 保留以与参考实现一致)


def madau_igm_tau(lam_obs, z):
    """观测波长 lam_obs [Å] 处红移 z 源的 IGM 有效光学深度 (Madau 1995 / FSPS)"""
    z1 = 1.0 + z
    tau = np.zeros_like(lam_obs)
    # Lyman 系线 blanketing: 蓝于该线观测位置的波长都计入
    for lw, ac in zip(LYW, LYCOEFF):
        m = lam_obs < lw * z1
        tau[m] += ac * (lam_obs[m] / lw) ** 3.46
    # i=1 (Lyα) 处附加金属 blanketing (FSPS 同款)
    m = lam_obs < LYW[0] * z1
    tau[m] += A_METAL * (lam_obs[m] / LYW[0]) ** 1.68
    # Lyman 连续吸收: Madau (1995) Eq.16 (FSPS 引用其 footnote 3 的近似式)
    m = lam_obs < LYLIM * z1
    xc = lam_obs[m] / LYLIM
    tau[m] += (0.25 * xc ** 3 * (z1 ** 0.46 - xc ** 0.46)
               + 9.4 * xc ** 1.5 * (z1 ** 0.18 - xc ** 0.18)
               - 0.7 * xc ** 3 * (xc ** (-1.32) - z1 ** (-1.32))
               - 0.023 * (z1 ** 1.68 - xc ** 1.68))
    # 拟合式在极短波端可能非单调: 蓝于最大值处一律取最大值 (与 FSPS 相同处理)
    imax = int(np.argmax(tau))
    if imax > 0:
        tau[:imax + 1] = tau[imax]
    return tau


def make_tophat(band, inst):
    """给定文献带通 (λ1,λ2) 与 CAL λ_eff: 保持对数宽度, 中心平移对齐。
    返回 (λ1', λ2', w) 且保证平坦 f_ν 的光子加权平均波长 = (λ2'−λ1')/ln(λ2'/λ1') = λ_eff"""
    lo, hi = BANDPASS_DOC[inst][band]
    w = np.log(hi / lo)
    lam_eff = CAL[f"{inst}/{band}"]["lam"]
    l1 = lam_eff * w / (np.expm1(w))
    l2 = l1 * np.exp(w)
    return l1, l2, w


def load_sed(path):
    with fits.open(path) as hdul:
        d = hdul[1].data
        wave_um = np.asarray(d["WAVELENGTH"], dtype=float)
        flux = np.asarray(d["FLUX"], dtype=float)
        z = float(hdul[1].header["REDSHIFT"])
    order = np.argsort(wave_um)
    return wave_um[order] * 1e4, flux[order], z  # → Å


def build_work_grid(wave, flux, z, lam_min, lam_max, step, extrap="flat"):
    """在 [lam_min, lam_max] 上以步长 step 建工作网格并取 f_ν。
    蓝端 (低于原生覆盖) 仅 extrap='power' 时按幂律外推; 红端 np.interp 天然平坦外推。"""
    grid = np.arange(lam_min, lam_max + 0.5 * step, step)
    f = np.interp(grid, wave, flux)  # 红端自动平坦 f_ν 外推
    if extrap == "power" and grid[0] < wave[0]:
        m = grid < wave[0]
        lam_rest = np.array(grid[m]) / (1.0 + z)
        # 幂律拟合: rest 1001–1250 Å (原生最蓝 250 Å) 内 log f_ν – log λ_rest 线性回归
        r = wave / (1.0 + z)
        sel = (r >= wave[0] / (1.0 + z)) & (r <= 1250.0)
        p = np.polyfit(np.log(r[sel]), np.log(flux[sel]), 1)  # f_ν ∝ λ_rest^γ
        f[m] = np.exp(np.polyval(p, np.log(lam_rest)))
        gamma = p[0]
        return grid, f, gamma
    return grid, f, None


def band_integral(grid, f, l1, l2):
    """I_b = ∫ f_ν·dλ/λ (梯形积分, top-hat 带通 [l1,l2])"""
    m = (grid >= l1) & (grid <= l2)
    lam = grid[m]
    return np.trapz(f[m] / lam, lam)


# ---------------------------------------------------------------------------
def main():
    targets = {
        "lens": ["lens_z0.298_subhalo-188058_snap78_galaxy_SEDs.fits",
                 "lens_z0.298_subhalo-297108_snap78_galaxy_SEDs.fits"],
        "source": ["source_z2.002_subhalo-190571_snap33_galaxy_SEDs.fits",
                   "source_z2.002_subhalo-197424_snap33_galaxy_SEDs.fits"],
    }
    result = {"lens": {}, "source": {}}
    report = []

    # 元数据 (溯源) — 提前加载
    meta = {}
    with open(os.path.join(SED_DIR, "manifest.csv"), newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            meta[row["filename"].split("subhalo-")[1].split("_")[0]] = {
                "kind": row["kind"], "z": float(row["redshift"]),
                "logMstar": float(row["logMstar"]), "SFR": float(row["SFR"]),
                "ageGyr": float(row["age_Gyr"]), "sersicN": float(row["sersic_n"]),
            }

    # 源静止帧 SED 曲线 (供前端动态红移): 将观测帧 f_ν 重标注到发射帧 λ_rest = λ_obs/(1+z_native).
    # f_ν_obs = f_ν_em(λ_rest)·(1+z)/(4πD_L² 归一), (1+z) 为常数 → 带内比值 w_b 中严格抵消, 不影响颜色.
    # 覆盖 rest 799–12004 Å (蓝端幂律外推段含内, 红端取原生上限): z_s ∈ [1, 4.5] 时
    # 最红波段 F200W (22100 Å) 采样 rest ≤ 11050 Å, F275W 下限采样 rest ≥ 444 Å (IGM 死区, 外推足够).
    # 源的静态 w 表也在此网格上计算 (边界除以 1+z) — 静态表与前端动态路径完全同源.
    curves = {}
    for fn in targets["source"]:
        fid = fn.split("subhalo-")[1].split("_")[0]
        wave, flux, z = load_sed(os.path.join(SED_DIR, fn))
        lam_rest = wave / (1.0 + z)
        grid_rest = np.arange(799.0, 12004.0, 4.0)
        f_em = np.interp(grid_rest, lam_rest, flux)
        # 蓝端 (rest < 原生 ~1001 Å) 幂律外推: 在 rest 1001–1250 Å 拟合 f_ν ∝ λ^γ
        m = grid_rest < lam_rest[0]
        sel = (lam_rest >= lam_rest[0]) & (lam_rest <= 1250.0)
        p = np.polyfit(np.log(lam_rest[sel]), np.log(flux[sel]), 1)
        f_em[m] = np.exp(np.polyval(p, np.log(grid_rest[m])))
        curves[fid] = (grid_rest, f_em.astype(np.float32))

    for kind, files in targets.items():
        for fn in files:
            fid = fn.split("subhalo-")[1].split("_")[0]
            z0 = meta[fid]["z"]
            if kind == "lens":
                # 透镜: 观测帧网格, 红端 np.interp 平坦 f_ν 外推至 22500 Å; 无 IGM (所有波段
                # 远红于观测帧 Lyα 1578 Å / Lyman 极限 1183 Å, 吸收恒为 0)
                wave, flux, _ = load_sed(os.path.join(SED_DIR, fn))
                grid, f, _ = build_work_grid(wave, flux, z0, 1300.0, 22500.0, 4.8, extrap="flat")
                zfac, tau = 1.0, None
            else:
                # 源: 静止帧网格 (与前端动态路径同源), IGM 在 λ_obs = λ_rest·(1+z) 上施加
                grid, f64 = curves[fid]
                f = f64.astype(np.float64)
                zfac = 1.0 + z0
                tau = madau_igm_tau(grid * zfac, z0)
            wtab = {}
            for inst in INSTRUMENTS:
                bands = list(BANDPASS_DOC[inst].keys())
                I_vals, tops = [], []
                for band in bands:
                    l1, l2, w = make_tophat(band, inst)
                    I = band_integral(grid, f if tau is None else f * np.exp(-tau),
                                      l1 / zfac, l2 / zfac)
                    I_vals.append(I)
                    tops.append((band, l1, l2, w))
                Qs = [CAL[f"{inst}/{b}"]["Q"] for b in bands]
                w_rel = [(Qs[i] * I_vals[i]) / (Qs[1] * I_vals[1]) for i in range(3)]
                wtab[inst] = [float(x) for x in w_rel]
                # 诊断: 各波段光子加权平均 f_ν 相对中间波段之比 (与谱形直观比对)
                fnu_ratio = [I_vals[i] / np.log(tops[i][2] / tops[i][1]) / I_vals[1]
                             * np.log(tops[1][2] / tops[1][1]) for i in range(3)]
                report.append(f"[{kind} {fid}] {inst}: w=[{w_rel[0]:.4f}, 1, {w_rel[2]:.4f}]  "
                              f"<f_nu>rel=[{fnu_ratio[0]:.3f}, 1, {fnu_ratio[2]:.3f}]")
                if tau is not None:
                    # IGM 衰减因子 (带内, 相对无 IGM): F275W/F390W 的教学看点
                    i0 = band_integral(grid, f, tops[0][1] / zfac, tops[0][2] / zfac)
                    i1 = band_integral(grid, f, tops[1][1] / zfac, tops[1][2] / zfac)
                    igm0 = I_vals[0] / i0 if i0 > 0 else float("nan")
                    igm1 = I_vals[1] / i1 if i1 > 0 else float("nan")
                    report.append(f"           IGM 带内透射: {bands[0]}={igm0:.3f}, {bands[1]}={igm1:.3f}")
            result[kind][fid] = wtab

    # 自检: 静态表应与静止帧曲线重算严格一致 (同一条路径, 仅验证 float32 嵌入精度)
    for fid, (gr, fe) in curves.items():
        z0 = meta[fid]["z"]
        tau = madau_igm_tau(gr * (1.0 + z0), z0)
        w_chk = {}
        for inst in INSTRUMENTS:
            bands = list(BANDPASS_DOC[inst].keys())
            I = []
            for b in bands:
                l1, l2, _ = make_tophat(b, inst)
                I.append(band_integral(gr.astype(np.float64), fe.astype(np.float64) * np.exp(-tau),
                                       l1 / (1.0 + z0), l2 / (1.0 + z0)))
            Qs = [CAL[f"{inst}/{b}"]["Q"] for b in bands]
            w_chk[inst] = [(Qs[i] * I[i]) / (Qs[1] * I[1]) for i in range(3)]
        w_ref = result["source"][fid]
        dev = max(abs(w_chk[i][k] / w_ref[i][k] - 1) for i in INSTRUMENTS for k in (0, 2))
        report.append(f"[自检] 源 {fid} 静止帧重算 vs 静态表最大偏差: {dev*100:.5f}%")

    # top-hat 边界与 λ_eff 对齐核验 (平坦 f_ν 光子加权平均波长应精确等于 λ_eff)
    chk = []
    for inst in INSTRUMENTS:
        for band in BANDPASS_DOC[inst]:
            l1, l2, w = make_tophat(band, inst)
            mean_lam = (l2 - l1) / np.log(l2 / l1)
            chk.append(f"  {inst}/{band}: top-hat [{l1:.0f}, {l2:.0f}] Å, "
                       f"<λ>={mean_lam:.1f} vs λ_eff={CAL[f'{inst}/{band}']['lam']:.1f}")

    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    js = _render_js(result, meta, curves, ts)
    with open(os.path.abspath(OUT_JS), "w", encoding="utf-8") as fh:
        fh.write(js)

    print("=" * 78)
    print("top-hat 边界核验 (λ_eff 对齐):")
    print("\n".join(chk))
    print("-" * 78)
    print("带内权重与诊断:")
    print("\n".join(report))
    print("-" * 78)
    print(f"已写出: {os.path.abspath(OUT_JS)}")


def _render_js(result, meta, curves, ts):
    """生成 sed_bands.js — 结构: SED_DATA.{lens,source}[id].w[inst] = [w蓝, 1, w红]
    另附: SED_BANDS (对齐后的 top-hat 边界) 与 SED_CURVE (源静止帧 SED, Float32 base64,
    供前端动态红移实时重算 w)。"""
    def obj_js(kind):
        parts = []
        for fid, wtab in result[kind].items():
            m = meta[fid]
            label = f"subhalo-{fid}"
            w_js = ", ".join(
                f'"{inst}": [{wtab[inst][0]:.6g}, 1.0, {wtab[inst][2]:.6g}]'
                for inst in INSTRUMENTS)
            parts.append(
                f'    "{fid}": {{label: "{label}", z: {m["z"]:.4f}, logMstar: {m["logMstar"]:.2f}, '
                f'SFR: {m["SFR"]:.2f}, sersicN: {m["sersicN"]:.2f}, w: {{ {w_js} }}}}')
        return ",\n".join(parts)

    # top-hat 边界表 (与静态 w 同一套)
    bp_js = ",\n".join(
        f'  "{inst}": [' + ", ".join(
            f"[{make_tophat(b, inst)[0]:.0f}, {make_tophat(b, inst)[1]:.0f}]"
            for b in BANDPASS_DOC[inst]) + "]"
        for inst in INSTRUMENTS)

    # 源静止帧 SED → Float32 (小端) → base64
    curve_js = ",\n".join(
        f'    "{fid}": {{lam0: {gr[0]:.0f}, step: {float(gr[1] - gr[0]):.1f}, n: {len(gr)}, '
        f'b64: "{base64.b64encode(fe.tobytes()).decode("ascii")}"}}'
        for fid, (gr, fe) in curves.items())

    return f"""/* sed_bands.js — 由 sed_data/make_sed_table.py 自动生成 ({ts}), 请勿手改
 *
 * 强透镜 Mock 彩色合成的物理波段权重表 (替代旧版人为谱色 SRC_TINT/LENS_TINT):
 *
 *   数据源  : GalaxyGenius mock (CSST_Galaxy_Mock) 4 个星系的观测帧 SED
 *             (f_ν [Jy], BinTable WAVELENGTH+FLUX, 详见 sed_data/lens_source_SEDs_v2/manifest.csv)
 *   带通    : 6 台仪器 × 3 波段 top-hat 近似 — 对数宽度取文献带通, 中心对齐 CAL.λ_eff,
 *             保证与 HTML 中 CAL.Q 定标自洽 (出处见 make_sed_table.py 的 BANDPASS_DOC 注释)
 *   IGM     : 源 SED 乘 Madau (1995) 平均透射, 实现对照 FSPS igm_absorb.f90;
 *             透镜 (z≈0.3) 所有波段远红于 Lyα 观测位置, 吸收恒为 0, 未施加
 *   权重    : w_b = Q_b·∫_band f_ν dλ/λ / (Q_mid·∫ f_ν dλ/λ)_mid  — 光子加权带内积分,
 *             每台仪器以中间波段为亮度锚点 (w_mid = 1), 故 m_AB/SNR 语义与旧版逐项一致
 *
 * 用法: strong-lensing.html 中
 *   SED_W_SRC  = SED_DATA.source[SED_ACTIVE.source].w        (静态, z=SED_ACTIVE 源的生成红移)
 *   sedW_srcDyn = sedSourceWeights(z_s)                       (动态红移, 见 HTML 内实现)
 *   SED_W_LENS = SED_DATA.lens[SED_ACTIVE.lens].w            (透镜红移固定, 恒为静态)
 */
const SED_DATA = {{
  lens: {{
{obj_js("lens")}
  }},
  source: {{
{obj_js("source")}
  }}
}};
/* 对齐 CAL.λ_eff 后的 top-hat 观测帧边界 [λ1, λ2] Å (每台仪器 [蓝, 中, 红] 顺序) */
const SED_BANDS = {{
{bp_js}
}};
/* 源静止帧 SED (f_ν 任意归一, (1+z) 常数因子在 w_b 中抵消):
   λ_rest = lam0 + step·i, i = 0..n-1 [Å]; f_ν = Float32Array(atob→字节, 小端) [Jy]
   覆盖 rest 799–12004 Å — 滑块 z_s ∈ [1, 4.5] 内所有波段均在覆盖范围内 */
const SED_CURVE = {{
{curve_js}
}};
/* 默认透镜/源对 (manifest 中 logMstar 最高透镜 × 最高 SFR 源; 备选可切换) */
const SED_ACTIVE = {{ lens: "188058", source: "190571" }};
"""


if __name__ == "__main__":
    main()
