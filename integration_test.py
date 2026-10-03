#!/usr/bin/env python3
"""
MiniJEV 集成测试
测试与Hermes Agent的集成
"""

import json
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from mini_jev import MiniJEV, DecisionType, JevConfig


def test_hermes_integration():
    """测试与Hermes的集成场景"""
    print("\n" + "=" * 60)
    print("Hermes集成测试")
    print("=" * 60)
    
    jev = MiniJEV()
    
    # 测试1: Skill路由
    print("\n测试1: Skill路由")
    test_cases = [
        ("帮我生成一份PPT", "应该加载哪个skill", ["ppt-master", "pptx-editing", "text-summary"]),
        ("分析一下这份报告", "应该加载哪个skill", ["data-analysis", "text-summary", "code-review"]),
        ("修复这段代码", "应该加载哪个skill", ["code-review", "debug", "refactor"]),
    ]
    
    for state, question, options in test_cases:
        result = jev.decide(state, question, options)
        print(f"  '{state[:20]}...' → {result.choice} (置信度: {result.confidence:.2f})")
    
    # 测试2: 任务分类
    print("\n测试2: 任务分类")
    tasks = [
        ("每日报告生成", ["content-creation", "data-collection", "system-monitoring"]),
        ("ETF监测任务", ["data-collection", "analysis", "reporting"]),
        ("代码审查", ["code-review", "security-audit", "performance"]),
    ]
    
    for task, options in tasks:
        result = jev.decide(task, "任务类型", options)
        print(f"  '{task}' → {result.choice} (置信度: {result.confidence:.2f})")
    
    # 测试3: 紧急程度判断
    print("\n测试3: 紧急程度判断")
    messages = [
        "系统崩溃了，请尽快处理",
        "有个小问题，有空看看",
        "客户投诉，需要立即响应",
        "常规咨询，按顺序处理",
    ]
    
    for msg in messages:
        result = jev.decide(msg, "紧急程度", ["低", "中", "高", "紧急"])
        print(f"  '{msg[:25]}...' → {result.choice} (置信度: {result.confidence:.2f})")
    
    # 测试4: 批量决策（模拟Hermes定时任务调度）
    print("\n测试4: 批量决策（定时任务调度）")
    requests = [
        {"state": "每日报告任务", "question": "优先级", "options": ["低", "中", "高"]},
        {"state": "紧急报警任务", "question": "优先级", "options": ["低", "中", "高"]},
        {"state": "定期维护任务", "question": "优先级", "options": ["低", "中", "高"]},
    ]
    
    results = jev.batch_decide(requests)
    for req, res in zip(requests, results):
        print(f"  {req['state']} → {res.choice} (置信度: {res.confidence:.2f})")
    
    # 打印统计
    print("\n统计信息:")
    stats = jev.get_stats()
    print(f"  决策次数: {stats['decision_count']}")
    print(f"  LLM调用: {stats['llm']['call_count']}")
    print(f"  平均延迟: {stats['avg_latency_ms']:.2f}ms")


def test_custom_llm():
    """测试自定义LLM接入"""
    print("\n" + "=" * 60)
    print("自定义LLM接入测试")
    print("=" * 60)
    
    # 模拟一个自定义LLM
    class MockCustomLLM:
        def call(self, prompt, model=None):
            # 简单的关键词匹配逻辑
            if "崩溃" in prompt or "紧急" in prompt:
                return '{"choice": "紧急", "confidence": 0.95, "probabilities": {"低": 0.01, "中": 0.02, "高": 0.02, "紧急": 0.95}}'
            elif "PPT" in prompt:
                return '{"choice": "ppt-master", "confidence": 0.90, "probabilities": {"ppt-master": 0.90, "pptx-editing": 0.05, "text-summary": 0.05}}'
            else:
                return '{"choice": "选项1", "confidence": 0.75, "probabilities": {"选项1": 0.75, "选项2": 0.25}}'
    
    jev = MiniJEV()
    jev.llm = MockCustomLLM()
    
    print("\n测试自定义LLM:")
    result = jev.decide("系统崩溃了", "紧急程度", ["低", "中", "高", "紧急"])
    print(f"  结果: {result.choice} (置信度: {result.confidence:.2f})")
    
    result = jev.decide("帮我生成PPT", "Skill路由", ["ppt-master", "pptx-editing"])
    print(f"  结果: {result.choice} (置信度: {result.confidence:.2f})")


def test_few_shot_learning():
    """测试Few-shot学习"""
    print("\n" + "=" * 60)
    print("Few-shot学习测试")
    print("=" * 60)
    
    config = JevConfig()
    
    # 添加自定义示例
    config.add_few_shot_example({
        "state": "用户反馈支付失败",
        "question": "问题类型",
        "options": ["bug", "咨询", "投诉"],
        "answer": {"choice": "bug", "confidence": 0.88}
    })
    
    config.add_few_shot_example({
        "state": "询问产品功能",
        "question": "问题类型",
        "options": ["bug", "咨询", "投诉"],
        "answer": {"choice": "咨询", "confidence": 0.92}
    })
    
    jev = MiniJEV(config=config)
    
    print("\n添加自定义示例后测试:")
    result = jev.decide("支付功能无法使用", "问题类型", ["bug", "咨询", "投诉"])
    print(f"  结果: {result.choice} (置信度: {result.confidence:.2f})")
    
    result = jev.decide("你们支持哪些功能", "问题类型", ["bug", "咨询", "投诉"])
    print(f"  结果: {result.choice} (置信度: {result.confidence:.2f})")
    
    print(f"\n当前Few-shot示例数: {len(config.few_shot_examples)}")


def test_performance_stress():
    """性能压力测试"""
    print("\n" + "=" * 60)
    print("性能压力测试")
    print("=" * 60)
    
    jev = MiniJEV()
    
    # 测试1000次决策
    iterations = 1000
    print(f"\n执行 {iterations} 次决策...")
    
    import time
    start = time.time()
    
    for i in range(iterations):
        jev.decide(f"测试状态{i}", "问题", ["选项A", "选项B", "选项C"])
    
    elapsed = time.time() - start
    
    stats = jev.get_stats()
    
    print(f"总耗时: {elapsed*1000:.2f}ms")
    print(f"平均每次: {elapsed/iterations*1000:.2f}ms")
    print(f"QPS: {iterations/elapsed:.2f}")
    print(f"LLM调用次数: {stats['llm']['call_count']}")
    print(f"LLM平均延迟: {stats['llm']['avg_latency_ms']:.2f}ms")
    
    # 检查内存使用
    import resource
    memory_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # KB to MB
    print(f"峰值内存使用: {memory_usage:.1f}MB")


def main():
    """主入口"""
    print("\n" + "=" * 60)
    print("MiniJEV 集成测试套件")
    print("=" * 60)
    
    try:
        test_hermes_integration()
        test_custom_llm()
        test_few_shot_learning()
        test_performance_stress()
        
        print("\n" + "=" * 60)
        print("✅ 所有集成测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
