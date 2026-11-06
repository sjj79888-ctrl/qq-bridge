# rebuild/ — 重做草稿（DRAFT）

> 本目录是 2026-11-06 晚 Torres 说“备份吧，准备重做”后准备的本地草稿。
> **全部是草稿，不是服务器真本，不可以直接部署。**
> 服务器真本 `bridge.py`、`.env`（含真 key）、NapCat 登录态均不在本地，
> 2026-11-06 下午起服务器因内存假死进不去终端，取不下来。

## 文件清单

| 文件 | 说明 |
|---|---|
| `bridge.py.DRAFT` | 桥的代码草稿（按 BRIDGE-SPEC.md 等重写）。部署前审完改名为 `bridge.py`。Genie 切换不要直接改它，跑 `patch_bridge_genie.DRAFT.py` |
| `patch_bridge_genie.DRAFT.py` | 切桥脚本的适配副本（只改了匹配缩进，Genie 逻辑未动；已实测一次 patched OK、二次 already patched）。部署真本时用原版 `../scripts/patch_bridge_genie.py` |
| `UNCERTAINTIES.md` | 不确定清单，共 32 条（U01–U32）。部署前逐条核对 |
| `docker-compose.yml.DRAFT` | napcat + bridge + genie 三服务草稿。Genie 已加内存上限 800m（建议值，未经实测）与 `on-failure:3`，不再无限制自启 |
| `Dockerfile.bridge.DRAFT` | 桥镜像草稿：python slim、pip 清华源、只 COPY bridge.py + stickers |
| `NAPCAT-DEPLOY.md` | NapCat 部署步骤草稿：镜像名待确认、OneBot 上报 `127.0.0.1:8787/event`、Torres 重新扫码登录小号 2750579528；绝不重启 napcat 容器来“修”登录 |
| `.env.draft` | 配置草稿：已知确定值已填，所有 key 一律 `<redacted>` 占位符。填好真 key 后再改名 `.env` |
| `REBUILD-CHECKLIST.md` | 按顺序的重做清单（控制台重装 → 验证 → 切桥 → 测试语音）+ 需要 Torres 做的 7 件事 |
| `MISSING.md` | 缺失清单：表情包缺的 9 张原图（只列清单，不重新生成）、legs4 待重做、legs2 已废弃；声音不用重训 |

## 使用顺序

1. 先读 `UNCERTAINTIES.md`，32 条逐条过。
2. 按 `REBUILD-CHECKLIST.md` 阶段 0 把草稿审完、把 Torres 要定的事定下来
   （Genie 内存限制最终值、legs4 改什么、GitHub 建库授权、key）。
3. 再按清单阶段 1–7 执行。任何一步验证不通过就停下来，不要往下赶。
4. 重建后把实测结果写回仓库，UNCERTAINTIES.md 里证实了的条目改成“已确认：……”+ 证据。

## 红线

- 不要把本目录的草稿当成原版直接部署。
- 不要把任何真 key 写进任何文件（本目录已 grep 核查过，只有 `<redacted>` 占位符）。
- 绝不重启 napcat 容器来“修”登录；登录过期只能重新扫码。
- Genie 不要再用无限制的 `--restart unless-stopped`。
