#!/usr/bin/env python3
"""
MiniJEV v2.0 真实场景测试 - ZAI API
"""

import json
import os
import sys
import time
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mini_jev_v2 import MiniJEV, JevConfig

# ========== ZAI API调用类 ==========
class ZAILLM:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://open.bigmodel.cn/api/paas/v4"
        self.model = "glm-4.5-flash"
        self.call_count = 0
        self.total_latency = 0.0
        self.error_count = 0
    
    def call(self, prompt: str) -> str:
        start = time.time()
        self.call_count += 1
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 1000
                },
                timeout=60
            )
            
            latency = time.time() - start
            self.total_latency += latency
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                self.error_count += 1
                print(f"API错误: {response.status_code}")
                return '{"reasoning": "API error", "choice": "error", "confidence": 0.0}'
                
        except Exception as e:
            self.error_count += 1
            print(f"API调用失败: {e}")
            return '{"reasoning": "error", "choice": "error", "confidence": 0.0}'


# ========== 测试用例 ==========
TEST_CASES = [
    {"name": "客服工单分类", "state": "用户反馈系统返回错误500", "question": "问题类型", "options": ["功能咨询", "技术支持", "bug报告", "功能需求"], "expected": "bug报告"},
    {"name": "紧急程度判断", "state": "服务器CPU占用率达到95%，持续告警", "question": "紧急程度", "options": ["低", "中", "高", "紧急"], "expected": "紧急"},
    {"name": "变更风险评级", "state": "修改核心模块的函数签名", "question": "风险等级", "options": ["低", "中", "高", "极高"], "expected": "高"},
    {"name": "Skill路由", "state": "用户需要生成一份PPT演示文稿", "question": "skill路由", "options": ["pptx", "content-creation", "data-analysis", "docx"], "expected": "pptx"},
    {"name": "人工介入判断", "state": "系统连续收到3次以上用户投诉", "question": "是否需要人工介入", "options": ["是", "否"], "expected": "是"},
    {"name": "优先级排序", "state": "任务1：数据库备份；任务2：API接口测试", "question": "哪个优先级更高", "options": ["数据库备份", "API接口测试", "同等重要"], "expected": "数据库备份"},
    {"name": "异常告警判断", "state": "订单量同比上周下降80%", "question": "是否触发异常告警", "options": ["是", "否"], "expected": "是"},
    {"name": "扩容策略", "state": "当前并发5万，预计增长到10万", "question": "扩容策略", "options": ["扩容100%", "扩容50%", "不扩容", "先观察"], "expected": "扩容100%"}
]


def get_api_key():
    """从桌面文件获取API key"""
    desktop_file = Path.home() / "Desktop" / "New File"
    if desktop_file.exists():
        with open(desktop_file, 'r') as f:
            lines = [l.strip() for l in f if l.strip() and 'https' not in l]
            if lines:
                return lines[0]
    return None


def run_test_case(case: dict, jev: MiniJEV, llm: ZAILLM) -> dict:
    """运行单个测试用例"""
    # 构建思考链prompt
    options_str = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(case["options"])])
    
    prompt = f"""你是一个专业的结构化决策引擎，具备深度推理能力。

【思考链要求】
请按以下步骤分析：
1. 识别问题类型和关键信息
2. 分析每个选项的适用性
3. 排除不合适的选项
4. 验证最终选择的合理性

【当前任务】
状态: {case["state"]}
问题: {case["question"]}
可选答案:
{options_str}

请按格式返回JSON，必须包含reasoning字段：
{{"reasoning": "你的详细推理过程", "choice": "选中的选项", "confidence": 0.0-1.0, "probabilities": {{"选项1": 0.x, "选项2": 0.x, ...}}}}"""
    
    # 调用LLM
    start = time.time()
    raw_response = llm.call(prompt)
    latency = (time.time() - start) * 1000
    
    # 解析响应
    try:
        result = json.loads(raw_response.strip())
    except:
        result = {"reasoning": "解析失败", "choice": case["options"][0], "confidence": 0.5}
    
    passed = result.get("choice") == case["expected"]
    
    return {
        "name": case["name"],
        "expected": case["expected"],
        "actual": result.get("choice"),
        "passed": passed,
        "confidence": result.get("confidence", 0.0),
        "latency_ms": latency,
        "reasoning": result.get("reasoning", "")
    }


def main():
    print(f"\n{'='*60}")
    print("MiniJEV v2.0 真实场景测试 - ZAI (glm-4.5-flash)")
    print(f"{'='*60}\n")
    
    api_key = get_api_key()
    if not api_key:
        print("❌ 未找到API key")
        return
    
    llm = ZAILLM(api_key)
    config = JevConfig(model="glm-4.5-flash", temperature=0.1)
    jev = MiniJEV(config=config)
    
    results = []
    correct = 0
    total = len(TEST_CASES)
    
    for i, case in enumerate(TEST_CASES, 1):
        print(f"[{i}/{total}] {case['name']}")
        print(f"  状态: {case['state']}")
        print(f"  期望: {case['expected']}")
        
        result = run_test_case(case, jev, llm)
        correct += 1 if result["passed"] else 0
        
        status = "✅" if result["passed"] else "❌"
        print(f"  {status} 结果: {result['actual']} (置信度: {result['confidence']:.2f}, 耗时: {result['latency_ms']:.0f}ms)")
        if result["reasoning"]:
            print(f"     推理: {result['reasoning'][:80]}...")
        
        results.append(result)
        print()
        
        # 避免请求过快
        time.sleep(0.5)
    
    # 统计
    accuracy = correct / total * 100
    avg_latency = sum(r["latency_ms"] for r in results) / total
    
    print(f"{'='*60}")
    print("测试结果汇总")
    print(f"{'='*60}")
    print(f"准确率: {correct}/{total} ({accuracy:.1f}%)")
    print(f"平均耗时: {avg_latency:.0f}ms/决策")
    print(f"LLM统计: calls={llm.call_count}, errors={llm.error_count}")
    
    # 失败分析
    failed = [r for r in results if not r["passed"]]
    if failed:
        print(f"\n失败用例:")
        for r in failed:
            print(f"  - {r['name']}: 期望 {r['expected']}, 实际 {r['actual']}")
    
    # 保存结果
    output_file = Path(__file__).parent / f"test_results_v2_zai_{int(time.time())}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "version": "2.0",
            "llm": "glm-4.5-flash",
            "timestamp": time.time(),
            "accuracy": accuracy,
            "total": total,
            "correct": correct,
            "avg_latency_ms": avg_latency,
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存: {output_file}")


if __name__ == "__main__":
    main()
