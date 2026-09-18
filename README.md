# TGMedia

跑在飞牛 fnOS 上的 Telegram 频道媒体下载工具。订阅频道、按规则过滤、排队下载，Web 界面看进度。

## 安装

1. 打开 [Releases](https://github.com/iStarCc/TGMedia/releases)，下载 `tgmedia.fpk`
2. 飞牛应用中心 → 手动安装，选这个 fpk
3. 按向导选存储目录，装完从桌面打开 TGMedia
4. 设置里添加 Telegram 账号（需要 [api_id / api_hash](https://my.telegram.org)），再添加订阅源

依赖飞牛自带的 **Python 3.12** 运行时。首次启动会在后台装 Python 依赖，可能要等一两分钟。

## 开发

```bash
# 本地跑前后端（后端 :8000，前端 :5173）
./scripts/dev.sh

# 停掉
./scripts/dev.sh stop
```

打 fpk 包：

```bash
./scripts/build.sh
# 产物：Apps/tgmedia/tgmedia.fpk
```

本地没有 `fnpack` 时会用仓库根目录下的二进制；也可以自己装：[fnpack 下载](https://static2.fnnas.com/fnpack/fnpack-1.2.3-linux-amd64)

## 目录

```
backend/          FastAPI + TDLib，下载和任务调度
frontend/         Vue 3 前端
Apps/tgmedia/     飞牛应用包（manifest、cmd、wizard 等）
scripts/          build.sh、dev.sh
fnnas-developer/  飞牛开发文档（git submodule）
version.json      版本号和 changelog，应用内更新检测也读这个
```

## 发版

1. 改 `version.json` 里的 `version`，在 `changelog` 最前面加一条
2. 提交到 `main`
3. 打 tag 并推送，GitHub Actions 会自动构建 fpk 并创建 Release：

```bash
git tag v1.0.5
git push origin v1.0.5
```

tag 名必须和 `version.json` 里的版本一致（带 `v` 前缀，如 `v1.0.4` 对应 `"version": "1.0.4"`）。

## 开发文档

飞牛应用开发文档在 submodule 里：

```bash
git submodule update --init --recursive
```

在线版：[fnnas-developer](https://github.com/iStarCc/fnnas-developer)
