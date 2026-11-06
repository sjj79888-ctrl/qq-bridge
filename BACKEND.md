# BACKEND — 模型后端

## 现在在用

- 中转：https://ly.77625.xyz/v1
- 模型：x-deepseek-v4.1-flash
- 2026-11-05 18:00 切回来的，只重建了 qq-bridge，napcat 没动。
- 启动日志确认过：`x-deepseek-v4.1-flash @ https://ly.77625.xyz/v1`，没有 Traceback。

## 另一条线

- gemini-3.8-flash，同一个中转。
- 2026-11-04 两条线都不太稳：gemini 慢、还被限流，DeepSeek 偶尔 502。
  11-04 晚上最后先留在 gemini 上。

## 2026-11-05 那次故障

- 13:20:49 开始，中转持续报 HTTP 500，两条线都挂。
  桥和 NapCat 本身没事，fallback 消息照常发出去了。
- 13:37 切到 x-deepseek-v4.1-flash，13:41 再测，还是 500。
  证明不是模型的问题，是中转后端的问题，再换线也没用。
- 17:55 左右，拿原来的 key 直接测，两条线都回 200 了：
  gemini 回了 “Hello! How can I help you today?”（11 token），
  DeepSeek 正常回了（125 token）。
- 注意：第一次直接测的时候，Python 默认 User-Agent 被 Cloudflare 拦了，
  报 403 error 1010。换浏览器 User-Agent 才通。
- 所以 Torres 选了切回原来的中转。真消息验证还没做，等他发消息测。

## 备胎：GLM

- 模型：glm-5.3-flash
- 地址：https://www.kamente.com/v1
- 额度：1,000,000 token。Torres 2026-11-05 找到的，他确认有 key。
- 每次调用约 1000–1500 token，100 万 token 大概能用 2 周到 4 个月
  （每天 10–40 次回复）。
- 状态：只在 `.env` 里改了地址和模型两行，key 那行没动，容器没重建，
  GLM 还没上线。key 后来也没写进去。
- 换 key 的过程卡住了：粘贴进命令行被当成命令执行，进 nano 退不出来，
  他在手机上按不了 Ctrl+X，文件管理器看不到隐藏的 `.env`。
  浏览器还重启过一次。`read -s` 那套办法在服务器上也没跑通。
- 终端历史里可能还留着他误粘贴的 key，记得清掉：
  `history -c; history -w`。
- GLM 配置留着当备胎，别删。

## 备份（别删）

服务器 `/home/ubuntu/qq-bridge/` 里：

- `.env.bak-20261105-glms` — 切 GLM 之前的完整配置（中转 + DeepSeek + 原来的 key）
- `.env.bak-20261105-deepseek` — gemini 那套
- `.env.bak-20261105-kamente` — GLM 地址 + 模型 + 原来的 key（key 那行当时没换）
- `bridge.py.bak-20261105-*` — 每次改动前的 bridge.py 备份
