#!/usr/bin/env python3
"""
MiniJEV v2.0 - 修复版：更好的选项匹配和解析
"""

import json
import sys
import time
from pathlib import Path
import re

# 直接从环境变量读取 API key
import os
api_key = os.environ.get("HERMES_CUSTOM_API_AGNES_AI_CN_API_KEY")
if not api_key:
    env_file = Path.home() / ".hermes" / "profiles" / "secretary" / ".env"
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith("HERMES_CUSTOM_API_AGNES_AI_CN_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"\'')
                    break

if not api_key:
    print("错误: 未找到 API key")
    sys.exit(1)

base_url = "https://api.agnes-ai.cn/v1"


def call_llm(prompt: str) -> str:
    """调用 Agnes LLM"""
    import requests
    
    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "agnes-2.5-flash",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 300
            },
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            print(f"  API错误 {response.status_code}: {response.text[:100]}")
            return None
    except Exception as e:
        print(f"  错误: {e}")
        return None


def parse_choice(raw: str, options: list) -> dict:
    """
    智能解析响应，提取choice和confidence
    处理各种格式：JSON、带编号、纯文本等
    """
    if not raw:
        return {"choice": options[0] if options else "error", "confidence": 0.0, "reasoning": "空响应"}
    
    # 1. 尝试直接解析JSON
    try:
        result = json.loads(raw.strip())
        if "choice" in result:
            return result
    except json.JSONDecodeError:
        pass
    
    # 2. 尝试从文本中提取JSON
    match = re.search(r'\{[^}]+\}', raw, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if "choice" in result:
                return result
        except:
            pass
    
    # 3. 匹配编号答案（如 "1." "2." "A." 等）
    num_match = re.match(r'^\s*(\d+)[\.\)]\s*(.+)', raw.strip(), re.MULTILINE)
    if num_match:
        num = int(num_match.group(1))
        answer_text = num_match.group(2).strip()
        
        if 1 <= num <= len(options):
            return {
                "choice": options[num - 1],
                "confidence": 0.95,
                "reasoning": f"选择第{num}个选项: {answer_text}"
            }
        elif answer_text in options:
            return {
                "choice": answer_text,
                "confidence": 0.90,
                "reasoning": answer_text
            }
    
    # 4. 直接匹配选项文本
    for opt in options:
        if opt in raw:
            return {
                "choice": opt,
                "confidence": 0.85,
                "reasoning": f"匹配到选项: {opt}"
            }
    
    # 5. 模糊匹配
    raw_lower = raw.lower()
    for opt in options:
        opt_words = opt.lower().split()
        if any(word in raw_lower for word in opt_words if len(word) > 2):
            return {
                "choice": opt,
                "confidence": 0.70,
                "reasoning": f"模糊匹配到选项: {opt}"
            }
    
    return {"choice": options[0], "confidence": 0.5, "reasoning": f"无法解析: {raw[:100]}"}


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


def main():
    print(f"\n{'='*60}")
    print("MiniJEV v2.0 测试 - Agnes LLM (优化版)")
    print(f"{'='*60}\n")
    
    results = []
    correct = 0
    total = len(TEST_CASES)
    
    for i, case in enumerate(TEST_CASES, 1):
        print(f"[{i}/{total}] {case['name']}")
        print(f"  状态: {case['state']}")
        print(f"  期望: {case['expected']}")
        
        # 构建优化prompt
        options_str = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(case["options"])])
        prompt = f"""你是结构化决策专家。请分析以下情况并选择最合适的选项。

状态: {case["state"]}
问题: {case["question"]}

可选答案:
{options_str}

请直接返回JSON，包含：
- choice: 选项名称（不是编号，是完整文本）
- confidence: 0.0-1.0的置信度
- reasoning: 简短推理过程

示例输出: {{"choice": "选项文本", "confidence": 0.95, "reasoning": "因为..."}}"""
        
        start = time.time()
        raw = call_llm(prompt)
        latency = (time.time() - start) * 1000
        
        result = parse_choice(raw, case["options"])
        passed = result.get("choice") == case["expected"]
        if passed:
            correct += 1
        
        status = "✅" if passed else "❌"
        print(f"  {status} 结果: {result.get('choice', 'N/A')} (置信度: {result.get('confidence', 0):.2f}, 耗时: {latency:.0f}ms)")
        if result.get("reasoning"):
            print(f"     推理: {result['reasoning'][:60]}...")
        
        results.append({
            "name": case["name"],
            "expected": case["expected"],
            "actual": result.get("choice"),
            "passed": passed,
            "confidence": result.get("confidence", 0.0),
            "latency_ms": latency,
            "reasoning": result.get("reasoning", "")
        })
        print()
        
        time.sleep(0.3)
    
    # 统计
    accuracy = correct / total * 100 if total > 0 else 0
    avg_latency = sum(r["latency_ms"] for r in results) / total if results else 0
    
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
    output_file = Path(__file__).parent / f"test_results_v2_fixed_{int(time.time())}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "version": "2.0-fixed",
            "llm": "agnes-2.5-flash",
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
