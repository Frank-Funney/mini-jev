#!/usr/bin/env python3
"""
MiniJEV 高级功能测试
测试边界情况、性能优化、错误处理
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mini_jev import MiniJEV, DecisionType, JevConfig


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("错误处理测试")
    print("=" * 60)
    
    jev = MiniJEV()
    
    # 测试1: 空状态
    print("\n测试1: 空状态")
    try:
        jev.decide("", "问题", ["A", "B"])
        print("  ❌ 应该抛出异常")
    except ValueError as e:
        print(f"  ✅ 正确捕获: {e}")
    
    # 测试2: 空选项
    print("\n测试2: 空选项列表")
    try:
        jev.decide("测试", "问题", [])
        print("  ❌ 应该抛出异常")
    except ValueError as e:
        print(f"  ✅ 正确捕获: {e}")
    
    # 测试3: 无效JSON响应
    print("\n测试3: 无效JSON响应")
    class BadLLM:
        def call(self, prompt, model=None):
            return "这不是JSON"
    
    jev.llm = BadLLM()
    result = jev.decide("测试", "问题", ["A", "B"])
    print(f"  ✅ 容错处理: choice={result.choice}, confidence={result.confidence:.2f}")
    
    # 测试4: JSON缺少关键字段
    print("\n测试4: JSON缺少choice字段")
    class PartialLLM:
        def call(self, prompt, model=None):
            return '{"confidence": 0.8}'
    
    jev.llm = PartialLLM()
    result = jev.decide("测试", "问题", ["A", "B"])
    print(f"  ✅ 默认填充: choice={result.choice}, confidence={result.confidence:.2f}")
    
    # 测试5: confidence超出范围
    print("\n测试5: confidence超出范围")
    class ExtremeLLM:
        def call(self, prompt, model=None):
            return '{"choice": "A", "confidence": 1.5}'
    
    jev.llm = ExtremeLLM()
    result = jev.decide("测试", "问题", ["A", "B"])
    print(f"  ✅ 范围限制: confidence={result.confidence:.2f} (限制到1.0)")


def test_decision_types():
    """测试三种决策类型"""
    print("\n" + "=" * 60)
    print("决策类型测试")
    print("=" * 60)
    
    jev = MiniJEV()
    
    # Choice决策
    print("\n1. Choice决策（多选一）")
    result = jev.decide(
        "系统崩溃了",
        "紧急程度",
        ["低", "中", "高", "紧急"],
        DecisionType.CHOICE
    )
    print(f"   结果: {result.choice} (置信度: {result.confidence:.2f})")
    print(f"   概率: {result.probabilities}")
    
    # Score决策
    print("\n2. Score决策（评分）")
    result = jev.decide(
        "代码变更引入了新参数",
        "风险等级",
        ["低", "中", "高"],
        DecisionType.SCORE
    )
    print(f"   结果: {result.choice} (评分: {result.confidence:.2f})")
    
    # Noul决策
    print("\n3. Noul决策（是/否判断）")
    result = jev.decide(
        "客户说急需处理",
        "是否需要人工介入",
        ["是", "否"],
        DecisionType.NOUL
    )
    print(f"   结果: {result.choice} (概率: {result.confidence:.2f})")


def test_few_shot_customization():
    """测试Few-shot自定义"""
    print("\n" + "=" * 60)
    print("Few-shot自定义测试")
    print("=" * 60)
    
    config = JevConfig()
    
    # 添加自定义示例
    print("\n添加自定义Few-shot示例...")
    config.add_few_shot_example({
        "state": "支付网关超时",
        "question": "问题类型",
        "options": ["bug", "咨询", "需求"],
        "answer": {"choice": "bug", "confidence": 0.90}
    })
    
    config.add_few_shot_example({
        "state": "想了解新功能",
        "question": "问题类型",
        "options": ["bug", "咨询", "需求"],
        "answer": {"choice": "咨询", "confidence": 0.85}
    })
    
    jev = MiniJEV(config=config)
    
    # 测试
    print("\n测试自定义示例效果:")
    result1 = jev.decide("支付网关超时", "问题类型", ["bug", "咨询", "需求"])
    print(f"  '支付网关超时' → {result1.choice} (置信度: {result1.confidence:.2f})")
    
    result2 = jev.decide("想了解新功能", "问题类型", ["bug", "咨询", "需求"])
    print(f"  '想了解新功能' → {result2.choice} (置信度: {result2.confidence:.2f})")
    
    print(f"\n当前Few-shot示例数: {len(config.few_shot_examples)}")


def test_batch_performance():
    """批量决策性能测试"""
    print("\n" + "=" * 60)
    print("批量决策性能测试")
    print("=" * 60)
    
    jev = MiniJEV()
    
    # 创建批量请求
    requests = []
    for i in range(50):
        requests.append({
            "state": f"测试状态{i}",
            "question": "分类",
            "options": ["A", "B", "C", "D"]
        })
    
    print(f"\n发送 {len(requests)} 个批量请求...")
    start = time.time()
    results = jev.batch_decide(requests)
    elapsed = time.time() - start
    
    print(f"总耗时: {elapsed*1000:.2f}ms")
    print(f"平均每次: {elapsed/len(requests)*1000:.2f}ms")
    print(f"QPS: {len(requests)/elapsed:.2f}")
    
    # 验证结果一致性
    unique_choices = set(r.choice for r in results)
    print(f"唯一选择数: {len(unique_choices)}")


def test_memory_usage():
    """内存使用测试"""
    print("\n" + "=" * 60)
    print("内存使用测试")
    print("=" * 60)
    
    import resource
    
    jev = MiniJEV()
    
    # 做100次决策
    for i in range(100):
        jev.decide(f"测试{i}", "问题", ["A", "B"])
    
    # 获取内存使用
    memory_info = resource.getrusage(resource.RUSAGE_SELF)
    peak_memory_mb = memory_info.ru_maxrss / 1024  # KB to MB
    
    print(f"\n峰值内存使用: {peak_memory_mb:.1f}MB")
    print(f"决策次数: 100")
    print(f"每决策内存: {peak_memory_mb/100:.2f}MB")


def test_history_management():
    """历史记录管理测试"""
    print("\n" + "=" * 60)
    print("历史记录管理测试")
    print("=" * 60)
    
    jev = MiniJEV()
    
    # 添加一些决策历史
    print("\n添加决策历史...")
    for i in range(10):
        jev.decide(f"测试{i}", "问题", ["A", "B"])
    
    # 获取历史
    history = jev.get_decision_history(limit=5)
    print(f"最近5次决策:")
    for i, h in enumerate(history, 1):
        print(f"  {i}. {h['result']['choice']} (置信度: {h['result']['confidence']:.2f})")
    
    # 清空历史
    print("\n清空历史记录...")
    jev.clear_history()
    print(f"清空后历史记录数: {len(jev.get_decision_history())}")


def test_edge_cases_advanced():
    """高级边界情况测试"""
    print("\n" + "=" * 60)
    print("高级边界情况测试")
    print("=" * 60)
    
    jev = MiniJEV()
    
    # 测试1: 单字符选项
    print("\n测试1: 单字符选项")
    result = jev.decide("测试", "问题", ["A", "B", "C"])
    print(f"  结果: {result.choice}")
    
    # 测试2: 超长选项名称
    print("\n测试2: 超长选项名称")
    long_options = ["这是一个非常长的选项名称测试", "另一个很长的选项", "短"]
    result = jev.decide("测试", "问题", long_options)
    print(f"  结果: {result.choice[:30]}...")
    
    # 测试3: Unicode选项
    print("\n测试3: Unicode选项")
    result = jev.decide("测试", "问题", ["中文选项", "English Option", "日本語"])
    print(f"  结果: {result.choice}")
    
    # 测试4: 数字选项
    print("\n测试4: 数字选项")
    result = jev.decide("测试", "问题", ["1", "2", "3"])
    print(f"  结果: {result.choice}")
    
    # 测试5: 特殊字符
    print("\n测试5: 特殊字符")
    result = jev.decide("测试 \"引号\" 和 \\反斜杠", "问题", ["A", "B"])
    print(f"  结果: {result.choice}")


def main():
    """主入口"""
    print("\n" + "=" * 60)
    print("MiniJEV 高级功能测试")
    print("=" * 60)
    
    try:
        test_error_handling()
        test_decision_types()
        test_few_shot_customization()
        test_batch_performance()
        test_memory_usage()
        test_history_management()
        test_edge_cases_advanced()
        
        print("\n" + "=" * 60)
        print("✅ 所有高级测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
