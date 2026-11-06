# VOICE-MODELS — 语音模型清单（只有清单，没有二进制）

> 本文件只记文件名、大小、md5 和配置。`.pth` / `.ckpt` / ONNX 目录 / tar.gz / chunks / GenieData（392MB）一律不进仓库。模型本体在本地 `~/workspace/voice-reference/models/`，重建时再传。

## 批准的配置（Torres 2026-11-06 11:05、12:07 两次点头）

- 训练：GPT-SoVITS V2ProPlus，SoVITS 8 轮 + GPT 10 轮，参考音频 60 秒（李诞播客 151.9–212.3 秒，邓紫棋一个人说话那段）。
- 试听批准：e8 权重 + 参考第 6 段（4.9 秒，“所以拍摄停滞不前，我自己在家里面两三个月没事干。”）+ temperature 0.7、top_k 5、top_p 0.8。
- 部署用的是**官方顺序版 ONNX**（top_p 在温度之前）：`xiaoman-onnx-official/`。参数版（top_p 在 Softmax 之后）他听了说「没感情、像一路念过去」，不要用。
- Genie 接口本身没有 temperature/top_k/top_p，这三个焊死在 ONNX 图里。另修了一个 Genie 采样 bug（RandomNormalLike 会抽到被过滤掉的词，改成指数竞赛采样，8000 次测试 0 越界）。

## 模型文件（本地，md5 已对过）

| 文件 | 大小 | md5 |
|---|---|---|
| `xiaoman-sovits-e8.pth` | 172,765,299 B | `3115ba0edf2345af11b42049ef030df7` |
| `xiaoman-gpt-e8.ckpt` | 155,313,011 B | `a0811b7a03004bb695827b7e2e77ffab` |
| `ref-seg6.wav` | 约 308 KB | `942ed13de04b228d68c75c78f53e0293` |
| `xiaoman-onnx-official.tar.gz`（已传服务器的打包） | 306,136,288 B | `2c072cc75930b83064679bb0fa1ba2a1` |

## ONNX 三个版本（本地 `models/` 下）

- `xiaoman-onnx/`：原版，321MB，回滚用，别动。
- `xiaoman-onnx-param/`：参数版，321MB，温度 0.7、top_k 5、top_p 在 Softmax 后。他听了不要。
- `xiaoman-onnx-official/`：官方顺序版，321MB，9 个文件（prompt_encoder、t2s_encoder、t2s_first_stage_decoder、t2s_shared、t2s_stage_decoder、vits 各 fp16/fp32），**部署用这一版**。

## Genie 服务（服务器上，已部署未验证）

- GenieData：392MB，17 个文件，服务器自己从 hf-mirror 下的，路径 `/home/ubuntu/qq-bridge/genie-data/GenieData/`。其中 speaker_encoder.onnx 184,812,166 B，chinese-hubert-base_weights_fp16.bin 188,741,632 B。
- Genie 镜像：`genie-tts-xiaoman`，ID f71c25575289，1.57GB。构建时 apt 卡住改走清华源、缺 gcc 又补上了。
- Genie 容器：`genie`，ID `31c237b695c4`，`--restart unless-stopped`，127.0.0.1:8000。启动命令和加载流程见 `genie/entrypoint.sh`（先起服务，再 POST `/load_character`，再 POST `/set_reference_audio`，打 "genie xiaoman ready"）。
- 切桥脚本：`scripts/patch_bridge_genie.py`，已传服务器、还没跑。Genie 优先、失败回落 edge-tts，妈妈模式永远 edge-tts（Xiaoxuan）。
- 待验证：容器日志、加载后内存（服务器总共 1.7GB）、合成一句「哥，我是小满」的延迟。

## 训练环境（AutoDL，已关机）

- 实例 `4f0d4c9ba8-50cbe310`，重庆 A 区/020 机，RTX 4090D，¥1.88/小时。2026-11-06 11:16 按 Torres 的话关机停费，**没点释放**，数据和装好的环境还在；连续关机 15 天自动释放（约 2026-11-21）。没他点头不要释放。
- 免费 GPU 两条路都死了：Colab 装环境时崩了、Kaggle 注册卡在同一个 Google 二维码验证（码显示在他正看屏幕的手机上，没第二台设备扫；短信验证可以）。
- 重训备选数据（不用先训，他选了先调参数）：播客里她单独说话的 F 段还有 3 段，约 3 分半（2093.1–2148.3 秒 55 秒、1455.8–1509.2 秒 53 秒、1798.9–1846.1 秒 47 秒）。
