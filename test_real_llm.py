#!/usr/bin/env python3
"""
MiniJEV 真实场景测试 - 使用真实 LLM
"""

import json
import os
import sys
import time
from pathlib import Path

# 添加 mini_jev.py 所在目录
sys.path.insert(0, str(Path(__file__).parent))
from mini_jev_v1 import MiniJEV, JevConfig, LLMInterface

# ========== ZAI API 真实调用类 ==========
class ZAILLM(LLMInterface):
    """使用 ZAI (glm-4.5-flash) 真实 API"""
    
    def __init__(self, config: JevConfig, api_key: str = None):
        super().__init__(config)
        
        # 获取 API key（优先参数，其次环境变量）
        self.api_key = api_key or os.environ.get("ZAI_API_KEY") or os.environ.get("ZHIPU_API_KEY")
        
        if not self.api_key:
            raise ValueError("需要设置 ZAI_API_KEY 或 ZHIPU_API_KEY 环境变量")
        
        # ZAI/GLM API 端点
        self.base_url = "https://open.bigmodel.cn/api/paas/v4"
        self.model = "glm-4.5-flash"
        
        # 使用 requests 或 httpx
        try:
            import requests
            self.session = requests.Session()
        except ImportError:
            self.session = None
    
    def call(self, prompt: str, model: str = None) -> str:
        """调用 ZAI API"""
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


def run_tests(use_mock=True):
    """运行测试"""
    
    llm_type = "Mock" if use_mock else "ZAI"
    print(f"\n{'='*60}")
    print(f"MiniJEV 真实场景测试 - 使用 {llm_type} LLM")
    print(f"{'='*60}\n")
    
    if use_mock:
        # Mock 模式
        jev = MiniJEV()
    else:
        # 真实 ZAI API
        try:
            config = JevConfig(model="glm-4.5-flash", temperature=0.1)
            jev = MiniJEV(config=config, llm=ZAILLM(config))
            print("✅ 已接入 ZAI (glm-4.5-flash) 真实 API\n")
        except Exception as e:
            print(f"❌ 无法接入 ZAI API: {e}")
            print("回退到 Mock 模式进行测试\n")
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
    print(f"测试结果汇总")
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
            "llm_type": llm_type,
            "accuracy": accuracy,
            "total": total,
            "correct": correct,
            "avg_latency_ms": avg_latency,
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存: {output_file}")
    
    return accuracy


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="MiniJEV 真实场景测试")
    parser.add_argument("--real", action="store_true", help="使用真实 ZAI API")
    args = parser.parse_args()
    
    # 先跑 Mock 测试（快速验证框架）
    accuracy_mock = run_tests(use_mock=True)
    
    # 如果有真实 API key，再跑真实测试
    if args.real and ("ZAI_API_KEY" in os.environ or "ZHIPU_API_KEY" in os.environ):
        accuracy_real = run_tests(use_mock=False)
        print(f"\n{'='*60}")
        print(f"对比结果")
        print(f"{'='*60}")
        print(f"Mock 准确率: {accuracy_mock:.1f}%")
        print(f"真实 API 准确率: {accuracy_real:.1f}%")
    elif not args.real:
        print(f"\n提示: 设置 ZAI_API_KEY 环境变量后可使用真实 LLM 测试")
        print(f"      python3 test_real_llm.py --real")
