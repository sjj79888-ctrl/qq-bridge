# VOICE-TRAINING — 给小满训一个专属声音

状态：2026-11-06 下午，训练已完成；参数版他听了说没感情，官方顺序版 12:07 已批准；Genie 已传上服务器、镜像建成、容器已启动，待验证；桥还没切过去，仍是 edge-tts。另：小满 13:18 起不说话、疑似登录失效，服务器 14:30 强制关机重置了密码，待核对文件，见 `../MEMORY.md`。

## 为什么做

- Torres 说小满的 AI 味还很重，语音和措辞都有。
- 措辞那半（MaiBot：人设重写 + 少量示例 + 拆条发）还没动，先做的声音。
- 现在的语音是 edge-tts：平时 Xiaoyi，妈妈模式 Xiaoxuan。

## 选的路：Genie-TTS + GPT-SoVITS

- 训 GPT-SoVITS **V2ProPlus**（只有 V2 和 V2ProPlus 能转 ONNX），
  转 ONNX 后在服务器上跑 Genie 伴生服务，桥只改 TTS 调用，
  edge-tts 留着当备胎。
- 备胎：Fish Audio API（约 $3/月，不用训练）；Kokoro 免费但只有预设音色。
- CosyVoice、IndexTTS、Spark-TTS 要 GPU，2 核 2G 的服务器跑不了。

## 参考音色

- 邓紫棋说话的声音。来源：李诞播客《邓紫棋写小说的故事》，
  151.9–212.3 秒，60 秒，她一个人说话，讲《启示录》那段。
  音调分析确认过是她（约 208Hz，对面李诞约 125Hz）。
- 训练只认干净的干声，歌曲伴奏会坏事；克隆真人歌手是冒充，
  用相似风格或清唱、采访音频更稳妥。
- 参考音频文件（60 秒 wav）和文字稿在原来那个 Muse 的工作区
  `~/workspace/voice-reference/` 里：`gem-podcast-60s.wav`、
  `gem-60s-transcript.md`。这个仓库里没有音频文件，
  重新训要先把那 60 秒音频和文字稿找回来。

## 训练参数

- 实验名 `xiaoman`。SoVITS 8 轮，GPT 10 轮，batch 2（爆显存改 1）。
- 流程：切片 → FunASR 出文字 → 人工对着文字稿校对 `.list` →
  特征提取 1A/1B/1C → SoVITS 8 轮 → GPT 10 轮 →
  找轮数最大的 `.pth`（SoVITS）和 `.ckpt`（GPT）→ API 试听 →
  下载模型 → 转 ONNX → 上服务器。
- 训练完立刻关实例再释放（按秒计费，关机不等于释放，先下载再释放）。

## 训练结果（2026-11-06 上午）

- 10:48 完成：60 秒音频切成 7 段，SoVITS 8 轮 + GPT 10 轮，都验证过。
- 试听：e8 默认设置声音发怪，e4 也不行；11:05 他批准了 e8 +
  参考第 6 段（4.9 秒，“所以拍摄停滞不前…”）+ 温度 0.7、top_k 5、top_p 0.8。
- 他选了先调参数再试，不加数据重训。重训备选数据已备好：播客里她单独
  说话的 F 段还有 3 段（classified.json 里 2093.1–2148.3 秒 55 秒、
  1455.8–1509.2 秒 53 秒、1798.9–1846.1 秒 47 秒），加起来约 3 分半。
- 模型已下到本地，md5 对过：`~/workspace/voice-reference/models/` 里
  xiaoman-sovits-e8.pth（172,765,299 B，md5 3115ba0e…）、
  xiaoman-gpt-e8.ckpt（155,313,011 B，md5 a0811b7a…），
  还有 gem-60s.list 和 ref-seg6.wav。
- 实例 11:16 按他的话已关机停费，没点释放，数据还在，连续关机 15 天
  才自动释放（控制台显示约 2026-11-21）。模型已在本地，释放也不用重训，
  只丢装好的环境。

## 免费 GPU 两条路都死了

- Colab：装环境时崩了，重试卡在 Google 二维码验证。
- Kaggle：注册卡在同一个二维码验证，用户名还要求至少 6 个字符。
- 根因：二维码验证 Torres 做不了，码显示在他正在看屏幕的那台手机上，
  没第二台设备扫。短信验证可以。

## 租云 GPU：AutoDL

- AutoDL（autodl.com），手机 + 短信注册，不用扫码。
  账号已注册、已实名、已充值 ¥5。昵称 炼丹师5590。
- 实名是姓名 + 身份证号，提交后跳支付宝人脸扫码，曾出过白屏，
  在他自己手机浏览器里重走一遍就通了。
- 4090D ¥1.88/小时，重庆 A 区 2026-11-05 21:44 已售罄（整个区都没卡）。
  2026-11-06 08:55 他定了换区租 4090D，不等重庆 A；实例
  4f0d4c9ba8-50cbe310，09:12 开机（重庆 A 区/020 机，RTX 4090D，
  Miniconda/CUDA 11.8）。2026-11-12 AutoDL 要调价。
  他 10:52 又充了 ¥5。
- JupyterLab 从浏览器打不开，改走 Jupyter Server API（工作区
  `jupyter-kernel.py`），实例 8443 端口 HTTPS 通，浏览器那头网络问题。
  参考音频和文字稿传到 `/root/data/`，md5 对过。
  环境：`conda create -n GPTSoVITS python=3.10`，克隆 GPT-SoVITS，
  `bash install.sh --device CU126 --source ModelScope`，
  装完验证 torch 能用 CUDA、验证 `s2Gv2ProPlus.pth` 在。
  注意：install.sh 会先删掉预训练 zip 再下载，别重跑；大文件下载慢
  就用 aria2c 多线程续传。

## 部署（2026-11-06 中午进行中）

- 11:16 他授权部署（“现在开始部署新声音”）。步骤：e8 模型转 ONNX
  （本机转，不用再开 AutoDL）→ 传服务器 → 起 Genie 伴生服务 →
  桥改调 Genie（edge-tts 留备胎）→ 测合成延迟 → 小满给他大号发一句
  测试语音（他 2026-11-05 20:13 提前同意过的）。
- 参数手术（11:52 完成）：Genie 接口没有温度/top_k/top_p，这三个焊死在
  ONNX 图默认值里（温度 1.0、top_k 15，top_p 默认 1.0 等于没过滤）。
  改在副本 `~/workspace/voice-reference/models/xiaoman-onnx-param/`
  （321MB），原版 `xiaoman-onnx/` 没动，当回滚。改动：温度 1.0→0.7，
  top_k 15→5，Softmax 后补 top_p 0.8 过滤，重复惩罚保持 1.35。
  另修了 Genie 采样 bug：原版 RandomNormalLike 会抽到被过滤掉的词，
  换成指数竞赛采样，8000 次测试 0 越界。
  试听：test-xiaoman-genie-param-1.wav（“哥，我是小满”，1.84 秒）、
  test-xiaoman-genie-param-2.wav（3.80 秒），都在
  `~/workspace/voice-reference/`。
  注意：top_p 这次在温度和 top_k 之后，比官方顺序更严，声音更确定、
  变化更小；他要是听着太板，再把过滤移到温度之前（约 30 行的变体）。
- 参数版他听了说没感情、像一路念过去，官方顺序版（top_p 在温度之前）
  12:07 他说“这个可以了”，批准部署这一版：`models/xiaoman-onnx-official/`
  （321MB）。12:35 他说“直接全部允许”，剩下步骤不用一步步问。
- 文件已上服务器并对过 md5：GenieData 392MB（17 个文件，服务器自己从
  hf-mirror 下的，`/home/ubuntu/qq-bridge/genie-data/GenieData/`）+
  官方顺序版 ONNX 321MB（15 个 20MB 分块传的，合并后 tar.gz md5
  2c072cc7…，解在 `/home/ubuntu/qq-bridge/genie-voice/`）+ ref-seg6.wav。
  分块和 tar 包还留在服务器上（共 585MB），清理还没做。
- Genie 镜像已建成（`genie-tts-xiaoman`，f71c25575289，1.57GB；构建时
  apt 卡住改走清华源、缺 gcc 又补上了），容器 `genie` 已启动
  （31c237b695c4，127.0.0.1:8000）。还没验证：容器日志、加载后内存、
  试合成“哥，我是小满”的延迟。
- 桥还没切，仍是 edge-tts；切桥的脚本 `patch_bridge_genie.py` 已传上
  服务器（`/home/ubuntu/qq-bridge/patch_bridge_genie.py`，3300 字节），
  还没跑：Genie 优先、失败回落 edge-tts，妈妈模式不动 edge-tts。
- 部署完，小满给他大号发一句测试语音。其他 QQ 测试消息一律要他点头才发。
- 他只负责登录，登录页出现就叫他；其他事 Muse 全包。
