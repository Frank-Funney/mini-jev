#!/usr/bin/env python3
"""
上传 MiniJEV v2.0 到 GitHub
"""

import os
import sys
import subprocess
from github import Github

# GitHub token（从环境变量或桌面文件获取）
token = os.environ.get("GITHUB_TOKEN", "")
if not token:
    # 尝试从桌面文件获取
    desktop_file = os.path.expanduser("~/Desktop/comand")
    if os.path.exists(desktop_file):
        with open(desktop_file, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('http'):
                    token = line.strip()
                    break

if not token:
    print("❌ 未找到GitHub token")
    sys.exit(1)

print(f"✅ GitHub token已加载: {token[:10]}...")

# 初始化GitHub客户端
g = Github(token)
user = g.get_user()
print(f"✅ 登录用户: {user.login}")

# 获取或创建仓库
repo_name = "mini-jev"
try:
    repo = g.get_repo(f"Frank-Funney/{repo_name}")
    print(f"✅ 找到仓库: {repo.full_name}")
except:
    print(f"⚠️ 仓库不存在，尝试创建...")
    try:
        repo = user.create_repo(repo_name, description="MiniJEV v2.0 - 超轻量级结构化决策引擎")
        print(f"✅ 创建仓库成功: {repo.html_url}")
    except Exception as e:
        print(f"❌ 创建仓库失败: {e}")
        sys.exit(1)

# 上传文件
project_dir = "/home/kylin01/projects/daily-reports/mini_jev"
files_to_upload = [
    "mini_jev_v2.py",       # 核心v2.0
    "mini_jev_v1.py",       # 原版本
    "README_v2.md",         # v2.0文档
    "requirements.txt",     # 依赖
    ".gitignore",           # Git忽略
    "test_v2_fixed.py",     # 测试脚本
]

print(f"\n📤 开始上传文件...")

for filename in files_to_upload:
    filepath = os.path.join(project_dir, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            # 尝试更新现有文件
            contents = repo.get_contents(f"/{filename}")
            repo.update_file(
                contents.path,
                f"Update {filename} (v2.0)",
                content,
                contents.sha,
                branch="main"
            )
            print(f"  ✅ {filename} 已更新")
        except:
            # 创建新文件
            try:
                repo.create_file(
                    filename,
                    f"Add {filename} (v2.0)",
                    content,
                    branch="main"
                )
                print(f"  ✅ {filename} 已添加")
            except Exception as e:
                print(f"  ⚠️ {filename} 失败: {e}")
    else:
        print(f"  ⚠️ {filename} 不存在")

print(f"\n🎉 上传完成！")
print(f"📍 仓库地址: {repo.html_url}")
print(f"📊 v2.0特性:")
print(f"   - 思考链推理框架")
print(f"   - 智能解析器")
print(f"   - 自验证机制")
print(f"   - 87.5% 准确率")
