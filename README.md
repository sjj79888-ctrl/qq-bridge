# QQ桥接

QQ 小号「小满」的 NapCat + 桥接备份仓库。单独建库，备份 QQ 桥接的全部本地资料。

- 小号：2750579528（小满）
- Torres 大号：1323841589（长温），私聊白名单
- 服务器：腾讯云 Lighthouse 广州，实例 `lhins-7y2px0v5`，公网 139.199.204.177，2 核 2G，免费试用到 **2026-12-04 00:02:55**

## 备份说明（先看这段）

- 备份时间：2026-11-06 晚。来源是 Muse 本地的资料，不是服务器拉下来的。
- **服务器上的最新 `bridge.py`、`.env`（含真 key）、NapCat 登录态，本仓库没有。** 2026-11-06 下午起服务器因内存假死进不去终端，取不下来。不要以为这仓库就是服务器的完整镜像。
- `.env` 真配置永远不进仓库。这里只有 `.env.example` 模板。
- 语音模型的大二进制也不在这里，只有清单和 md5（见 `VOICE-MODELS.md`）。模型本体在本地 `~/workspace/voice-reference/models/`，重建时再传。
- 表情包原图：`stickers/legs3.jpg`、`legs5.jpg` 两张已部署的新图在仓库里；其余原图（happy、hug、shy、pout、sad、sleep、happy2、sad2、legs 原图）只在服务器上，清单见 `stickers/MANIFEST.md`。

## 最重要的一条

**绝不能重启 napcat 容器。** 重启会丢 QQ 登录状态。只重建 bridge 服务，而且要 Torres 同意了再重建。

## 文件清单

| 文件 | 内容 |
|---|---|
| `BRIDGE-SPEC.md` | 桥的行为规格：回复规则、人格切换、称呼、黑名单 |
| `BACKEND.md` | 模型后端：中转、GLM 备胎、2026-11-05 故障 |
| `VOICE-STICKERS.md` | 语音和表情包的触发规则 |
| `VOICE-TRAINING.md` | 给小满训专属声音的全过程 |
| `VOICE-MODELS.md` | 语音模型清单（文件名、md5、批准的配置），无二进制 |
| `SERVER-STATE.md` | 服务器现状、工单、快照、升配价格、重建清单 |
| `POST-RESET-CHECKLIST.md` | 密码重置后逐项核对清单（2026-11-06） |
| `.env.example` | 配置模板，无真 key |
| `personas/` | 三个人格：小满、妈妈、女仆（含女仆 47 字压缩版草稿） |
| `stickers/` | 表情包清单 + legs3、legs5 两张已部署原图 |
| `genie/` | Genie-TTS 服务的 Dockerfile + entrypoint.sh |
| `scripts/patch_bridge_genie.py` | 把桥的语音切到 Genie 的补丁脚本（未在服务器上跑过） |

## 回复规则（摘要，详见 BRIDGE-SPEC.md）

- 私聊只回大号 1323841589；群聊只在被 @ 时回。
- 群聊每天 0:00–10:00（北京）静默，私聊不受影响。
- 黑名单（先于白名单检查）：2482076278、428762607。
- 女仆模式只对 QQ 2716043774 生效，他说「女仆」才切入，叫他主人；其余任何人（包括 Torres）不带称呼。说「小满」退出。
- 只有大号才会被叫哥 / 小家伙 / 宝贝；群里别人 @ 她，回话不带称呼。

## 模型后端（摘要）

- 在用：`x-deepseek-v4.1-flash` @ `https://ly.77625.xyz/v1`（2026-11-05 18:00 切回）。
- 备胎：GLM `glm-5.3-flash` @ `https://www.kamente.com/v1`，key 没写进 `.env`，没上线。
- 语音：现在仍是 edge-tts（平时 Xiaoyi，妈妈模式 Xiaoxuan）；Genie 专属音色已批准、文件已上服务器、容器已启动，但未验证、桥还没切过去。

## 重建要做的事

完整清单见 `SERVER-STATE.md`，摘要：

1. 重新扫码登录 QQ 小号（NapCat 登录态随重装丢失）。
2. 重新填 `.env` 的 key（Torres 本人给）。
3. 按 `BRIDGE-SPEC.md` 重建 bridge.py（规格在，逐字代码只在服务器上）。
4. 重新传 Genie 文件约 747MB（GenieData 392MB + ONNX 321MB + 参考音频）。
5. 表情包缺的原图从服务器取；服务器没了就按清单重新生成。
