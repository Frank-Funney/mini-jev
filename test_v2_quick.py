#!/usr/bin/env python3
"""
MiniJEV v2.0 快速测试 - ZAI API (带重试)
"""

import json
import sys
import time
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mini_jev_v2 import MiniJEV, JevConfig

# ========== 测试用例 ==========
TEST_CASES = [
    {"name": "客服工单分类", "state": "用户反馈系统返回错误500", "question": "问题类型", "options": ["功能咨询", "技术支持", "bug报告", "功能需求"], "expected": "bug报告"},
    {"name": "紧急程度判断", "state": "服务器CPU占用率达到95%，持续告警", "question": "紧急程度", "options": ["低", "中", "高", "紧急"], "expected": "紧急"},
    {"name": "变更风险评级", "state": "修改核心模块的函数签名", "question": "风险等级", "options": ["低", "中", "高", "极高"], "expected": "高"},
    {"name": "Skill路由", "state": "用户需要生成一份PPT演示文稿", "question": "skill路由", "options": ["pptx", "content-creation", "data-analysis", "docx"], "expected": "pptx"}
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


def call_llm(prompt: str, api_key: str, retries=3) -> dict:
    """调用LLM，带重试"""
    base_url = "https://open.bigmodel.cn/api/paas/v4"
    
    for attempt in range(retries):
        try:
            response = requests.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "glm-4.5-flash",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 500
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                print(f"  API错误 {response.status_code}: {response.text[:100]}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                    continue
                return '{"reasoning": "API error", "choice": "error", "confidence": 0.0}'
                
        except requests.exceptions.Timeout:
            print(f"  超时 (attempt {attempt+1})")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            return '{"reasoning": "timeout", "choice": "error", "confidence": 0.0}'
        except Exception as e:
            print(f"  错误: {e}")
            return '{"reasoning": "error", "choice": "error", "confidence": 0.0}'
    
    return '{"reasoning": "max retries", "choice": "error", "confidence": 0.0}'


def parse_response(raw: str) -> dict:
    """解析响应"""
    try:
        result = json.loads(raw.strip())
        if "choice" not in result:
            result["choice"] = "error"
        if "confidence" not in result:
            result["confidence"] = 0.0
        if "reasoning" not in result:
            result["reasoning"] = ""
        return result
    except json.JSONDecodeError:
        # 尝试提取JSON
        match = __import__('re').search(r'\{[^}]+\}', raw)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        return {"reasoning": "parse error", "choice": "error", "confidence": 0.0}


def run_test():
    """运行测试"""
    print(f"\n{'='*60}")
    print("MiniJEV v2.0 快速测试 - ZAI (glm-4.5-flash)")
    print(f"{'='*60}\n")
    
    api_key = get_api_key()
    if not api_key:
        print("❌ 未找到API key")
        return
    
    print(f"✅ API key已加载\n")
    
    results = []
    correct = 0
    total = len(TEST_CASES)
    
    for i, case in enumerate(TEST_CASES, 1):
        print(f"[{i}/{total}] {case['name']}")
        print(f"  状态: {case['state']}")
        print(f"  期望: {case['expected']}")
        
        # 构建思考链prompt
        options_str = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(case["options"])])
        prompt = f"""你是结构化决策专家。请分析以下情况并给出判断。

状态: {case["state"]}
问题: {case["question"]}
选项:
{options_str}

请按思考链分析：
1. 识别关键信息
2. 排除不合适的选项
3. 选择最合适的答案

返回JSON格式：
{{"reasoning": "你的推理", "choice": "选项", "confidence": 0.0-1.0}}"""
        
        start = time.time()
        raw = call_llm(prompt, api_key)
        latency = (time.time() - start) * 1000
        
        result = parse_response(raw)
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
        
        time.sleep(1)  # 避免速率限制
    
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
    output_file = Path(__file__).parent / f"test_results_v2_quick_{int(time.time())}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "version": "2.0-quick",
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
    run_test()
