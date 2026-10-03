#!/usr/bin/env python3
"""
MiniJEV v2.0 真实场景测试
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mini_jev_v2 import MiniJEV, JevConfig, DecisionType

# ========== 测试用例 ==========
TEST_CASES = [
    {
        "name": "客服工单分类",
        "state": "用户反馈系统返回错误500",
        "question": "问题类型",
        "options": ["功能咨询", "技术支持", "bug报告", "功能需求"],
        "expected": "bug报告"
    },
    {
        "name": "紧急程度判断",
        "state": "服务器CPU占用率达到95%，持续告警",
        "question": "紧急程度",
        "options": ["低", "中", "高", "紧急"],
        "expected": "紧急"
    },
    {
        "name": "变更风险评级",
        "state": "修改核心模块的函数签名",
        "question": "风险等级",
        "options": ["低", "中", "高", "极高"],
        "expected": "高"
    },
    {
        "name": "Skill路由",
        "state": "用户需要生成一份PPT演示文稿",
        "question": "skill路由",
        "options": ["pptx", "content-creation", "data-analysis", "docx"],
        "expected": "pptx"
    },
    {
        "name": "人工介入判断",
        "state": "系统连续收到3次以上用户投诉",
        "question": "是否需要人工介入",
        "options": ["是", "否"],
        "expected": "是"
    },
    {
        "name": "优先级排序",
        "state": "任务1：数据库备份；任务2：API接口测试",
        "question": "哪个优先级更高",
        "options": ["数据库备份", "API接口测试", "同等重要"],
        "expected": "数据库备份"
    },
    {
        "name": "异常告警判断",
        "state": "订单量同比上周下降80%",
        "question": "是否触发异常告警",
        "options": ["是", "否"],
        "expected": "是"
    },
    {
        "name": "扩容策略",
        "state": "当前并发5万，预计增长到10万",
        "question": "扩容策略",
        "options": ["扩容100%", "扩容50%", "不扩容", "先观察"],
        "expected": "扩容100%"
    }
]


def run_tests():
    """运行测试"""
    print(f"\n{'='*60}")
    print("MiniJEV v2.0 真实场景测试 - 思考链推理框架")
    print(f"{'='*60}\n")
    
    # 使用Mock LLM进行测试
    jev = MiniJEV()
    
    results = []
    correct = 0
    total = len(TEST_CASES)
    
    for i, case in enumerate(TEST_CASES, 1):
        print(f"[{i}/{total}] {case['name']}")
        print(f"  状态: {case['state']}")
        print(f"  期望: {case['expected']}")
        
        start = time.time()
        result = jev.decide(
            state=case["state"],
            question=case["question"],
            options=case["options"]
        )
        latency = (time.time() - start) * 1000
        
        passed = result.choice == case["expected"]
        if passed:
            correct += 1
            status = "✅"
        else:
            status = "❌"
        
        print(f"  {status} 结果: {result.choice} (置信度: {result.confidence:.2f}, 耗时: {latency:.0f}ms)")
        if result.reasoning:
            print(f"     推理: {result.reasoning[:80]}...")
        
        results.append({
            "name": case["name"],
            "expected": case["expected"],
            "actual": result.choice,
            "passed": passed,
            "confidence": result.confidence,
            "latency_ms": latency,
            "reasoning": result.reasoning
        })
        print()
    
    # 统计
    accuracy = correct / total * 100
    avg_latency = sum(r["latency_ms"] for r in results) / total
    
    print(f"{'='*60}")
    print("测试结果汇总")
    print(f"{'='*60}")
    print(f"准确率: {correct}/{total} ({accuracy:.1f}%)")
    print(f"平均耗时: {avg_latency:.0f}ms/决策")
    
    # 失败分析
    failed = [r for r in results if not r["passed"]]
    if failed:
        print(f"\n失败用例:")
        for r in failed:
            print(f"  - {r['name']}: 期望 {r['expected']}, 实际 {r['actual']}")
    
    # 保存结果
    output_file = Path(__file__).parent / f"test_results_v2_{int(time.time())}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "version": "2.0",
            "timestamp": time.time(),
            "accuracy": accuracy,
            "total": total,
            "correct": correct,
            "avg_latency_ms": avg_latency,
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存: {output_file}")
    
    return accuracy


if __name__ == "__main__":
    run_tests()
