#!/usr/bin/env python3
"""Direct test of MockLLM functionality"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from mini_jev_v3_optimized import MockLLM, JevConfig

# Create a simple test case
config = JevConfig()
llm = MockLLM(config)

# Test prompt
test_prompt = """你是结构化决策专家，具备风险感知能力。

核心原则：
1. 识别关键信息，分析风险等级
2. 高风险场景优先选择激进策略
3. 保守策略仅在风险明确低时使用
4. 返回JSON格式，包含reasoning字段

输出格式：
{"reasoning": "推理过程", "choice": "选项", "confidence": 0.0-1.0}

领域规则：
|- 系统故障/崩溃 → 紧急处理，不犹豫
|- 数据安全风险 → 高优先级，提前防御
|- 性能瓶颈 → 及时扩容，避免雪崩
|- 用户投诉累积 → 立即介入，防止扩散
|- 订单异常 → 立即告警处理
|- 并发增长 → 主动扩容策略

【当前任务】
状态: 用户反馈系统返回错误500
问题: 问题类型
可选答案:
1. 功能咨询
2. 技术支持
3. bug报告
4. 功能需求

请按思考链格式返回JSON:"""

print("=== MockLLM Test ===")
print(f"Prompt length: {len(test_prompt)}")

# Test the _smart_mock method directly
result = llm._smart_mock(test_prompt)
print(f"Result: {result}")

# Try to parse the result
try:
    import json
    parsed = json.loads(result)
    print(f"Parsed successfully: {parsed}")
except json.JSONDecodeError as e:
    print(f"JSON decode error: {e}")