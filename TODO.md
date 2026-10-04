# MiniJEV v3.0 发布待办

## 当前状态
- ✅ 代码开发完成：mini_jev_v3.py
- ✅ 测试通过：87.5%准确率（7/8用例）
- ⏸️ GitHub推送：等待网络恢复

## 待完成事项

### 1. Token准备
- [ ] 生成新的GitHub Personal Access Token
- [ ] 确保勾选 `repo` 权限
- [ ] 有效期建议：7天
- [ ] 立即复制保存（只显示一次）

### 2. 推送代码
```bash
cd ~/projects/daily-reports/mini_jev
git remote set-url origin https://<TOKEN>@github.com/Frank-Funney/mini-jev.git
git push origin master
```

### 3. 创建Release
- Tag: v3.0.0
- Title: MiniJEV v3.0 - 风险加权决策引擎
- 上传附件: mini-jev-v3.0-release.tar.gz

## 关键文件位置
- 核心代码：`~/projects/daily-reports/mini_jev/mini_jev_v3.py`
- 测试脚本：`~/projects/daily-reports/mini_jev/test_v3.py`
- 发布包：`~/projects/daily-reports/mini-jev-v3.0-release.tar.gz` (268KB)

## v3.0 改进内容
1. 风险加权机制（risk_factor参数）
2. 修复扩容策略边界case
3. 增强领域知识库
4. Few-shot示例优化
