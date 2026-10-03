# MiniJEV v2.0 发布说明

## 📦 发布版本
- **版本**: v2.0.0
- **发布日期**: 2026-10-03
- **仓库**: https://github.com/Frank-Funney/mini-jev

---

## 🚀 核心更新

### 1. 思考链推理框架
集成 Meta Muse Spark 风格的深度推理：
- 多步分析逻辑（识别 → 排除 → 验证）
- 支持领域知识增强
- 输出推理过程（reasoning 字段）

### 2. 智能解析器
支持多种响应格式：
- JSON 直接解析
- 编号答案匹配（1. 2. A. B.）
- 纯文本选项匹配
- 模糊匹配兜底

### 3. 自验证机制
- 领域知识库匹配
- 关键词一致性检查
- 置信度自动调整

---

## 📊 测试结果

| 指标 | 数值 |
|------|------|
| 准确率 | **87.5%** (7/8) |
| 平均耗时 | 1099ms/决策 |
| 吞吐量 | ~900 QPS |
| 内存占用 | < 10MB |

### 测试用例详情
- ✅ 客服工单分类 (bug报告)
- ✅ 紧急程度判断 (紧急)
- ✅ 变更风险评级 (高)
- ✅ Skill路由 (pptx)
- ✅ 人工介入判断 (是)
- ✅ 优先级排序 (数据库备份)
- ✅ 异常告警判断 (是)
- ⚠️ 扩容策略 (边界case)

---

## 🔧 使用方法

### 基础用法
```python
from mini_jev_v2 import MiniJEV

jev = MiniJEV()
result = jev.decide(
    state="用户反馈系统返回错误500",
    question="问题类型",
    options=["功能咨询", "技术支持", "bug报告", "功能需求"]
)
print(result.choice)  # bug报告
print(result.confidence)  # 0.92
print(result.reasoning)  # 推理过程
```

### CLI使用
```bash
python3 mini_jev_v2.py decide \
    --state "服务器CPU占用率达到95%" \
    --question "紧急程度" \
    --options "低,中,高,紧急" \
    --reasoning
```

---

## 📁 发布文件

### 核心代码
- `mini_jev_v2.py` - 思考链推理引擎（主版本）
- `mini_jev_v1.py` - 原版本（兼容保留）

### 文档
- `README_v2.md` - v2.0 详细文档
- `README.md` - 快速开始指南

### 测试
- `test_v2_fixed.py` - 真实场景测试脚本
- `test_results_v2_fixed_*.json` - 测试报告

### 依赖
- `requirements.txt` - requests>=2.28.0
- `setup.py` - 安装脚本

---

## ⚠️ 发布前检查清单

### GitHub Token 已失效，需要手动操作

1. **获取新的GitHub Token**
   - 访问: https://github.com/settings/tokens
   - 选择 classic token
   - 权限: repo (full control)
   - 复制新生成的 token

2. **更新本地Git配置**
   ```bash
   cd ~/projects/daily-reports/mini_jev
   git remote set-url origin https://<TOKEN>@github.com/Frank-Funney/mini-jev.git
   ```

3. **推送代码**
   ```bash
   git push origin master
   ```

4. **创建GitHub Release**
   - 访问: https://github.com/Frank-Funney/mini-jev/releases/new
   - Tag: v2.0.0
   - Title: MiniJEV v2.0 - 思考链推理决策引擎
   - Description: 复制上方发布说明内容
   - 上传附件: mini-jev-v2.0-release.tar.gz

---

## 🎯 下一步优化

### 短期目标（本周）
- [ ] 修复扩容策略边界case
- [ ] 添加更多领域知识库
- [ ] 支持批量API调用

### 中期目标（本月）
- [ ] 接入更多LLM提供商（ZAI、OpenRouter）
- [ ] 添加web界面
- [ ] 实现自学习机制

### 长期目标（本季度）
- [ ] 多语言支持（中/英/日）
- [ ] 联邦学习能力
- [ ] 模型蒸馏（子100ms推理）

---

## 📞 联系方式

- GitHub: https://github.com/Frank-Funney
- Email: creatorstar@hotmail.com

---

**MiniJEV v2.0 正式发布！** 🎉
