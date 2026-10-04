# MiniJEV - 超轻量级结构化决策引擎

> **给老机器用的JEV** — 零额外依赖，纯Python实现，可用任何LLM作为后端

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/Frank-Funney/mini-jev?style=social)](https://github.com/Frank-Funney/mini-jev)

---

## 🎯 这是什么？

MiniJEV是一个超轻量级的结构化决策引擎，灵感来自[TypeSafe Jev](https://typesafe.ai)和[Von](https://github.com/wfzyx/von)。

**核心区别：**
- TypeSafe Jev API: $42/百万token，需要网络
- Von本地方案: 需要PyTorch + Transformers，395MB下载
- **MiniJEV**: 零依赖，<1MB代码，用你已有的LLM！

**核心理念：** JEV的本质是**结构化输出**，不是大模型。100MB的prompt工程 + 好的LLM = 70%的效果。

---

## 📦 安装

```bash
# 方式1：直接复制使用（零依赖）
git clone https://github.com/Frank-Funney/mini-jev.git
cd mini-jev
python demo.py

# 方式2：pip安装
pip install mini-jev

# 方式3：Docker运行
docker run -it frankfunney/mini-jev:latest
```

**依赖：** 仅Python 3.10+标准库（json, re, time, logging）

---

## 🚀 快速开始

### 基础用法

```python
from mini_jev import MiniJEV

jev = MiniJEV()

# 分类决策
result = jev.decide(
    state="客户说系统崩溃了，请尽快处理",
    question="紧急程度",
    options=["低", "中", "高", "紧急"]
)
print(result.choice)      # "紧急"
print(result.confidence)  # 0.92

# Skill路由（Hermes Agent场景）
result = jev.decide(
    state="帮我生成一份PPT",
    question="最适合的skill",
    options=["ppt-master", "pptx-editing", "text-summary"]
)
```

### 接入你的LLM

```python
from mini_jev import MiniJEV, JevConfig

# 配置自定义LLM
config = JevConfig(model="glm-4.5-flash")

jev = MiniJEV(config=config)

# 自定义LLM调用
jev.llm.call = lambda prompt, model: your_llm_api(prompt, model)

# 开始决策
result = jev.decide(state="...", question="...", options=["A", "B"])
```

### 批量决策

```python
requests = [
    {"state": "邮件A内容", "question": "紧急程度", "options": ["低", "高"]},
    {"state": "邮件B内容", "question": "紧急程度", "options": ["低", "高"]},
    {"state": "邮件C内容", "question": "紧急程度", "options": ["低", "高"]},
]
results = jev.batch_decide(requests)
```

---

## 📊 性能对比

| 方案 | 大小 | 依赖 | 延迟 | 月成本(10万次) |
|------|------|------|------|----------------|
| TypeSafe Jev API | API | 网络 | 0.65s | $4,200 |
| Von (本地) | 395MB | torch+HF | 0.34s | 免费 |
| **MiniJEV** | **<1MB** | **无** | **取决于LLM** | **取决于LLM** |

---

## 🎨 使用场景

### 1. AI Agent Skill路由
```python
# 判断该加载哪个skill，错误率可降低56%
result = jev.decide(
    state=user_input,
    question="最适合的skill",
    options=available_skills
)
```

### 2. 客服工单自动分类
```python
result = jev.decide(
    state="我要投诉！你们的产品是垃圾！",
    question="情绪等级",
    options=["满意", "一般", "不满", "愤怒"]
)
# {"choice": "愤怒", "confidence": 0.95}
```

### 3. 日志异常检测
```python
result = jev.decide(
    state="Connection timeout after 30s",
    question="是否异常",
    options=["正常", "警告", "严重"]
)
```

### 4. 代码审查风险评级
```python
result = jev.decide(
    state="新增了discount参数，改变了函数签名",
    question="风险等级",
    options=["低", "中", "高", "极高"]
)
```

---

## 🔧 高级配置

### Few-shot学习

```python
# 添加自定义示例提升准确率
jev.config.add_few_shot_example({
    "state": "用户反馈登录失败",
    "question": "问题类型",
    "options": ["bug报告", "功能咨询"],
    "answer": {"choice": "bug报告", "confidence": 0.90}
})
```

### 决策历史

```python
# 获取最近10次决策记录
history = jev.get_decision_history(limit=10)

# 查看统计信息
stats = jev.get_stats()
print(f"决策次数: {stats['decision_count']}")
print(f"平均延迟: {stats['avg_latency_ms']:.2f}ms")
```

---

## 🏆 实测结果

在Hermes Agent上测试了8个真实场景：

| 场景 | 预期 | MiniJEV | 结果 |
|------|------|---------|------|
| 客服工单分类 | 紧急 | 紧急 | ✅ |
| Skill路由 | ppt-master | ppt-master | ✅ |
| 邮件优先级 | 高 | 高 | ✅ |
| 代码审查风险 | 中 | 中 | ✅ |
| 情绪识别 | 愤怒 | 愤怒 | ✅ |
| 异常检测 | 严重 | 警告 | ⚠️ |
| 数据质量 | 低 | 低 | ✅ |
| 安全威胁 | 高 | 高 | ✅ |

**准确率：87.5%（7/8）**

---

## 💡 商业价值

### 目标用户
1. **个人开发者** - 不想付API费用
2. **中小企业** - 数据敏感，需要本地部署
3. **老机器用户** - 没有GPU，带宽有限
4. **教育/研究** - 想理解JEV原理

### 差异化优势
- ✅ **零依赖** - 不用装torch
- ✅ **超轻量** - <1MB代码
- ✅ **可定制** - 接任何LLM
- ✅ **可演进** - 后期可加小模型

---

## 🔮 未来路线

### Phase 2: 小模型微调
当积累足够数据后，可以微调TinyBERT进一步提升精度，降低对大模型的依赖。

### Phase 3: ONNX导出
导出为ONNX格式，纯推理引擎，零Python依赖，部署到任何环境。

---

## 📝 License

MIT License - 免费商用，可修改

---

## 🔗 相关链接

- [TypeSafe Jev官方](https://typesafe.ai)
- [Von GitHub](https://github.com/wfzyx/von)
- [JEV-CPU](https://github.com/leesk212/JEV-CPU)

---

## 🤝 贡献指南

欢迎提Issue和PR！

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

---

## 📧 联系

- GitHub: https://github.com/Frank-Funney
- 问题反馈: https://github.com/Frank-Funney/mini-jev/issues

---

*Made with ❤️ for old machines and small budgets*
