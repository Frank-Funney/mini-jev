#!/usr/bin/env python3
"""
MiniJEV 真实场景测试 - 使用 Hermes 当前配置的 LLM
"""

import json
import os
import sys
import time
from pathlib import Path

# 添加 mini_jev.py 所在目录
sys.path.insert(0, str(Path(__file__).parent))
from mini_jev_v1 import MiniJEV, JevConfig, LLMInterface

# ========== 真实 API 调用类 ==========
class HermesLLM(LLMInterface):
    """使用 Hermes Agent 配置的 LLM"""
    
    def __init__(self, config: JevConfig):
        super().__init__(config)
        
        # 从环境变量获取 API key
        self.api_key = os.environ.get("HERMES_CUSTOM_API_AGNES_AI_CN_API_KEY") or \
                       os.environ.get("AGNES_API_KEY_A") or \
                       os.environ.get("AGNES_API_KEY_B") or \
                       os.environ.get("AGNES_API_KEY_C")
        
        self.base_url = "https://api.agnes-ai.cn/v1"
        self.model = "agnes-2.5-flash"
        
        if not self.api_key:
            raise ValueError("未找到 API key")
    
    def call(self, prompt: str, model: str = None) -> str:
        """调用 API"""
        import requests
        
        start = time.time()
        self.call_count += 1
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model or self.model,
                    "messages": [
                        {"role": "system", "content": "你是一个专业的结构化决策引擎"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 500
                },
                timeout=30
            )
            
            latency = time.time() - start
            self.total_latency += latency
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                print(f"API 错误: {response.status_code} - {response.text[:200]}")
                self.error_count += 1
                return '{"choice": "error", "confidence": 0.0, "probabilities": {}}'
                
        except Exception as e:
            print(f"API 调用失败: {e}")
            self.error_count += 1
            return '{"choice": "error", "confidence": 0.0, "probabilities": {}}'


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
    print("MiniJEV 真实场景测试 - Hermes LLM (agnes-2.5-flash)")
    print(f"{'='*60}\n")
    
    # 检查 API key
    api_key = os.environ.get("HERMES_CUSTOM_API_AGNES_AI_CN_API_KEY") or \
              os.environ.get("AGNES_API_KEY_A") or \
              os.environ.get("AGNES_API_KEY_B") or \
              os.environ.get("AGNES_API_KEY_C")
    
    if not api_key:
        print("❌ 未找到 API key")
        print("请设置环境变量: HERMES_CUSTOM_API_AGNES_AI_CN_API_KEY")
        return 0
    
    try:
        config = JevConfig(model="agnes-2.5-flash", temperature=0.1)
        jev = MiniJEV(config=config, llm=HermesLLM(config))
        print("✅ 已接入 Hermes LLM (agnes-2.5-flash)\n")
    except Exception as e:
        print(f"❌ 无法初始化: {e}")
        return 0
    
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
        
        results.append({
            "name": case["name"],
            "expected": case["expected"],
            "actual": result.choice,
            "passed": passed,
            "confidence": result.confidence,
            "latency_ms": latency
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
    print(f"LLM统计: {json.dumps(jev.llm.get_stats(), indent=2)}")
    
    # 失败分析
    failed = [r for r in results if not r["passed"]]
    if failed:
        print(f"\n失败用例:")
        for r in failed:
            print(f"  - {r['name']}: 期望 {r['expected']}, 实际 {r['actual']}")
    
    # 保存结果
    output_file = Path(__file__).parent / f"test_results_{int(time.time())}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.time(),
            "llm_type": "agnes-2.5-flash",
            "accuracy": accuracy,
            "total": total,
            "correct": correct,
            "avg_latency_ms": avg_latency,
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存: {output_file}")
    
    return accuracy


if __name__ == "__main__":
    accuracy = run_tests()
