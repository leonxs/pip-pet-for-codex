# Pip 素材制作与复核

本文件记录从已确认的 [`assets/reference.png`](../assets/reference.png) 重建动画和复核交付文件的方式。交付文件为 [`assets/spritesheet.png`](../assets/spritesheet.png) 与 [`assets/pet.json`](../assets/pet.json)，规格和完整坐标表见 [README](../README.md)。

## 角色约束

Pip 的主要特征是圆润企鹅轮廓、白色肚皮、宽橙色喙、两只白色眼睛与黑色瞳孔，以及红色围巾。参考 PNG 是所有动作的唯一图像来源；制作时复用其像素、配色和曲线，不为不同姿态重新生成角色。待机第 0 帧直接使用去除外部背景后的完整参考图，保留原始轮廓。

视线方向使用头部与瞳孔的轻微变化：眼睛先看向目标方向，喙与头部略微跟随；向上抬起视线和喙，向下则降低，斜向组合两个轴。躯干、肚皮、脚和围巾保持稳定，双眼始终可见。

## 制作流程

1. **提取参考图层。** [`scripts/build_sprites.cjs`](../scripts/build_sprites.cjs) 在 768 × 768 的参考坐标中处理图片，仅移除与画布边界连通的外部白色背景，保留封闭区域内的白色肚皮和眼睛，并处理边缘的白色底色。按原图位置与颜色提取躯干、双翅、双脚、围巾和面部图层。
2. **定义九种动作。** [`scripts/poses.cjs`](../scripts/poses.cjs) 记录每帧的身体、面部、翅膀、双脚和围巾变换。动作依次为 `idle`、`running-right`、`running-left`、`waving`、`jumping`、`failed`、`waiting`、`running`、`review`，分别使用 6、8、8、4、5、8、6、6、6 帧。左右移动分别定义变换，保留原图不对称的围巾位置。
3. **保持关节与布料连接。** 翅膀使用带原图纹理的连续形变，肩部保持连接，变形量逐渐过渡至翼尖；肩根位于围巾后，弯起的翼尖可覆盖躯干。思考动作沿弧形弯肘路径绕过围巾外侧，再将翼尖靠近喙，避免硬旋转造成穿插和红色残片。轮廓裁切保留抗锯齿覆盖率，彩色边缘去除白底混色。围巾尾部从固定连接处逐渐弯曲。双脚保留原图中相连的整块纹理，左右动作通过中间区域平滑过渡，避免硬拆双脚产生直切缝。
4. **使用固定画布与尺度。** 所有帧共用 192 × 208 px 画布和 0.235 的参考图缩放比例；动作本身可有轻微压缩、拉伸、倾斜和位移。着地姿态补偿身体纵向缩放对脚底基线的影响，跳跃保留起落位移。不会按每帧或每行动作的外接矩形重新缩放。构建器拒绝触及单格边界的姿态。
5. **制作视线方向。** 姿态脚本按上方 0°、顺时针每隔 22.5° 定义 16 个方向，通过瞳孔、面部倾斜和喙的细微位移表达视线，放入第 9、10 行。
6. **组装最终图集并记录来源。** 将 57 个动作帧与 16 个方向帧放入 8 × 11 网格，输出 1536 × 2288 px 的 RGBA PNG。未使用的 15 格保持透明，完全透明像素中的 RGB 清零。构建器更新素材描述中的图集及参考图 SHA-256，并写入逐帧边界报告。
7. **复核最终编码文件。** Python 工具从最终 PNG 再次裁切帧并生成预览，检查结构与视觉表现，使预览对应交付图集。

这套流程由参考 PNG、姿态参数和确定性的图像变换组成，重建无需 AI 图像生成调用。修改动作时调整姿态参数或图层变形与合成逻辑，然后重新构建和复核。

## 从参考图重建

需要 Node.js 20.9+、Python 3.10+。在项目根目录运行：

```sh
npm ci
python -m pip install -r requirements.txt
npm run build
python scripts/validate.py --output qa/validation.json
python scripts/make_previews.py --output previews
python scripts/test_install_codex.py
```

构建器输出图集、更新后的 `assets/pet.json` 和 [`qa/generation-validation.json`](../qa/generation-validation.json)。生成报告记录参考图与图集哈希、固定缩放比例、原始待机姿态坐标以及各帧非透明边界。`qa/validation.json` 保存独立结构检查结果。

## 从最终图集复核

在项目根目录安装依赖并运行：

```sh
python -m pip install -r requirements.txt
python scripts/validate.py
python scripts/extract_frames.py --output work/frames
python scripts/make_previews.py --output work/previews
```

`work/frames` 与 `work/previews` 是可重新导出的本地检查材料；构建时导出的原图分层保存在 `work/refinement/layers`。`work/` 不进入 Git，也不是重新构建的输入。

### 结构复核

- PNG 为 RGBA，尺寸为 1536 × 2288 px，可均分为 8 列 × 11 行。
- 动作行只使用规定的前若干格，总计 57 帧；两行视线方向全部使用，共 16 帧。
- 有效格包含非透明内容，15 个未使用格完全透明。
- 完全透明像素中的 RGB 值为零，角色内容没有碰到单格边界。
- 素材描述中的状态、方向、尺寸和图集 SHA-256 与交付 PNG 一致；生成报告另外记录参考图 SHA-256。

### 视觉复核

| 复核材料 | 关注点 |
| --- | --- |
| [`all-states.gif`](../previews/all-states.gif) | 九种动作是否可区分；步态、挥手、跳跃和恢复动作的帧序是否自然 |
| [`idle-jump-idle.gif`](../previews/idle-jump-idle.gif) | 切换状态时角色尺度和落点是否一致，跳跃是否具有蓄力、腾空和落地 |
| [`look-loop.gif`](../previews/look-loop.gif) | 双眼、喙与头部是否协调，视线方向是否按顺序变化，循环接缝是否突兀 |
| [`motion-stills.png`](../previews/motion-stills.png) | 原始待机轮廓、配色、边缘、翅膀与双脚连接、围巾尾部和代表性姿态是否一致 |

预览工具还导出各状态 GIF、`idle.png`、`overview.png` 和 `contact-sheet.png`。逐帧检查时保持 192 × 208 的完整画布。仅裁切角色的非透明外接矩形会改变帧内定位，容易把留白差异变成播放抖动。

## 使用边界

GIF 是演示材料，包含展示用的背景、标签或帧时长，不应作为 RGBA 源素材的替代品。实际播放时长和循环策略由宿主决定；跳跃、失败等动作也可按业务需要播放一次后回到待机。

v2 在这里表示图集布局版本。仓库提供 `scripts/install_codex.py`，用于将原始 PNG 和 `codex/pet.json` 清单安装到 Codex 本地宠物目录。更新已有 Pip 时使用 `python scripts/install_codex.py --update`，脚本先核实安装身份并备份旧文件。安装后需在 Codex 设置中刷新并选择 Pip，再通过 `/pet` 显示；脚本不会自动切换当前宠物。仓库结构检查和安装器测试不能代替宿主界面确认。16 个方向表示视线，不提供全身转向动画。二维像素变形也需要检查连接、遮挡和状态切换，视觉预览仍是判断动作质量的重要依据。

修改参考图或动作后应重新运行构建，让构建器同步更新素材描述中的 SHA-256，再运行结构检查并重新生成预览；若改动网格、行顺序或帧数，应同步修改素材描述、工具参数和 README 中的布局说明。

许可说明见 [README 的许可部分](../README.md#许可)；本项目未声明开源许可证。
