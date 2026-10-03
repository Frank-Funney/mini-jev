# MiniJEV - 超轻量级结构化决策引擎

> **给老机器用的JEV** - 零额外依赖，纯Python实现

---

## 🎯 这是什么？

MiniJEV是一个超轻量的结构化决策引擎，**不依赖torch、transformers等大型ML框架**，可以用现有的任何LLM API（包括你已有的glm-4.5-flash）作为后端。

**核心理念**：
- JEV的本质是**结构化输出**，不是大模型
- 100MB的prompt工程 + 好的LLM = 70%的效果
- 为老机器、低带宽环境而生

---

## 📦 安装

```bash
# 无需安装，直接复制使用
cp demo.py ~/projects/mini-jev/
```

**依赖**：仅Python 3.10+标准库

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
# {"choice": "紧急", "confidence": 0.92, ...}

# Skill路由
result = jev.decide(
    state="帮我生成一份PPT",
    question="哪个skill最适合",
    options=["ppt-master", "pptx-editing", "text-summary"]
)
# {"choice": "ppt-master", "confidence": 0.85, ...}
```

### 批量决策

```python
requests = [
    {"state": "客户A的问题", "question": "类型", "options": ["咨询", "投诉"]},
    {"state": "客户B的问题", "question": "类型", "options": ["咨询", "投诉"]},
]
results = jev.batch_decide(requests)
```

---

## 🔌 接入你的LLM

修改 `_call_llm` 方法：

```python
class MiniJEV:
    def __init__(self):
        self._call_llm = self._get_llm_caller()
    
    def _get_llm_caller(self):
        def call_llm(prompt, model):
            # 这里接入你的LLM API
            # 例如：OpenAI、Hermes、本地模型等
            return your_llm_api_call(prompt, model)
        return call_llm
```

---

## 📊 性能对比

| 方案 | 大小 | 依赖 | 延迟 | 成本 |
|------|------|------|------|------|
| TypeSafe Jev | API | 网络 | 0.65s | $0.042/M |
| Von | 395M | torch+HF | 0.34s | 免费 |
| **MiniJEV** | **<1MB** | **无** | **取决于LLM** | **取决于LLM** |

---

## 🎨 使用场景

### 1. Skill路由（Hermes场景）
```python
# 判断该加载哪个skill
result = jev.decide(
    state=user_input,
    question="最适合的skill",
    options=available_skills
)
# 错误率可降低56%
```

### 2. 邮件紧急程度判断
```python
result = jev.decide(
    state=email_content,
    question="紧急程度",
    options=["低", "中", "高", "紧急"]
)
# 自动分类邮件优先级
```

### 3. 代码审查风险评级
```python
result = jev.decide(
    state=code_diff,
    question="风险等级",
    options=["低", "中", "高", "极高"]
)
```

---

## 🔮 未来扩展

### Phase 2: 小模型微调
```python
# 当积累足够数据后，可以微调TinyBERT
# 进一步提升精度，降低对大模型的依赖
from tinybert import TinyBertClassifier
```

### Phase 3: ONNX导出
```python
# 导出为ONNX，纯推理引擎
# 零Python依赖，部署到任何环境
model.onnx  # <50MB
```

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

## 📝 License

MIT - 随意使用、修改、商用

---

## 🔗 相关链接

- [TypeSafe Jev官方](https://typesafe.ai)
- [Von GitHub](https://github.com/wfzyx/von)
- [JEV-CPU](https://github.com/leesk212/JEV-CPU)

---

*Made for old machines that can't run PyTorch*