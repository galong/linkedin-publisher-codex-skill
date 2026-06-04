# LinkedIn Publisher Codex Skill

`linkedin-publisher` 是一个 Codex Skill，用于在 Codex 中准备、预览并通过 LinkedIn Posts API 发布个人 LinkedIn 动态。

它支持：

- 发布到个人 LinkedIn 账号
- 纯文字动态
- 单张图片动态
- OAuth 授权辅助
- 本地 LinkedIn 风格 HTML 可视化预览
- 通过 `--publish --yes` 做发布确认，避免误发

当前版本不支持公司主页动态、定时发布、编辑、删除、评论、数据分析、视频、文档或轮播图。

## 环境要求

- Python 3.9+
- 一个 LinkedIn Developer 应用
- LinkedIn 产品和权限：
  - `Share on LinkedIn`
  - `Sign In with LinkedIn using OpenID Connect`
  - OAuth scope：`w_member_social`
- 在 LinkedIn Developer 后台配置 OAuth 回调地址：

```text
http://localhost:8080/callback
```

## 安装为 Codex Skill

克隆本仓库，然后把 skill 目录复制到 Codex skills 目录：

```bash
mkdir -p ~/.codex/skills
cp -R linkedin-publisher ~/.codex/skills/linkedin-publisher
```

重启 Codex，或新开一个 Codex 会话，让 skill 元数据重新加载。

## 配置

创建一个用户级配置文件。这个配置会被所有 Codex 工作区共享：

```bash
mkdir -p ~/.config/linkedin-publisher
cp linkedin-publisher/config.example.json ~/.config/linkedin-publisher/config.json
```

编辑：

```text
~/.config/linkedin-publisher/config.json
```

必填字段：

```json
{
  "client_id": "your-linkedin-client-id",
  "client_secret": "your-linkedin-client-secret",
  "redirect_uri": "http://localhost:8080/callback",
  "person_id": "your-linkedin-person-id",
  "token_file": "~/.config/linkedin-publisher/token.json"
}
```

环境变量仍然可用，并且优先级高于配置文件：

```bash
export LINKEDIN_CLIENT_ID="your-client-id"
export LINKEDIN_CLIENT_SECRET="your-client-secret"
export LINKEDIN_REDIRECT_URI="http://localhost:8080/callback"
```

不要提交 `~/.config/linkedin-publisher/config.json`、token 文件、access token、refresh token 或 client secret。

## LinkedIn 授权

运行本地 OAuth 回调流程：

```bash
python3 linkedin-publisher/scripts/linkedin_auth.py authorize \
  --state "linkedin-publisher-setup"
```

在浏览器里完成 LinkedIn 授权后，token 会保存到：

```text
~/.config/linkedin-publisher/token.json
```

查看 token 状态，不会打印 token 值：

```bash
python3 linkedin-publisher/scripts/linkedin_auth.py status
```

获取你的个人 author ID：

```bash
python3 linkedin-publisher/scripts/linkedin_auth.py userinfo
```

返回结果里的 `sub` 可以作为 `person_id`；也可以使用返回的 `person_urn` 配合 `--author-urn`。

如果你把 `person_id` 保存到 `~/.config/linkedin-publisher/config.json`，之后发布时就不需要再传 `--person-id`。

## 预览

生成纯文字 API 预览：

```bash
python3 linkedin-publisher/scripts/linkedin_publish.py \
  --text-file "./post.md"
```

生成单图 API 预览：

```bash
python3 linkedin-publisher/scripts/linkedin_publish.py \
  --text-file "./post.md" \
  --image "./cover.png"
```

生成本地可视化 HTML 预览：

```bash
python3 linkedin-publisher/scripts/linkedin_preview_html.py \
  --text-file "./post.md" \
  --image "./cover.png" \
  --output "./previews/linkedin-preview.html" \
  --name "Your Name" \
  --headline "Your LinkedIn headline"
```

用浏览器打开生成的 HTML 文件，即可查看接近 LinkedIn 动态卡片的本地预览效果。

## 发布

确认预览无误后再发布：

```bash
python3 linkedin-publisher/scripts/linkedin_publish.py \
  --text-file "./post.md" \
  --image "./cover.png" \
  --publish \
  --yes
```

发布成功后，脚本会打印 LinkedIn share URN。

## 安全说明

- 发布脚本只有在同时传入 `--publish` 和 `--yes` 时才会真正发布。
- token 状态和 userinfo 命令不会打印 access token。
- 图片上传失败时会停止发布，不会创建缺图动态。
- 当前版本有意不支持 LinkedIn 公司主页发布。

## Skill 文件结构

```text
linkedin-publisher/
├── SKILL.md
├── agents/openai.yaml
├── config.example.json
├── references/linkedin_api.md
└── scripts/
    ├── linkedin_auth.py
    ├── linkedin_preview_html.py
    └── linkedin_publish.py
```
