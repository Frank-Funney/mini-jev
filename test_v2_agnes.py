#!/usr/bin/env python3
"""
MiniJEV v2.0 测试 - Agnes LLM (无速率限制)
"""

import json
import sys
import time
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent))
from mini_jev_v2 import MiniJEV, JevConfig


def call_agnes(prompt: str, retries=2) -> str:
    """使用Agnes LLM调用（通过子进程调用Hermes）"""
    import subprocess
    
    for attempt in range(retries):
        try:
            # 使用hermes chat -q
            result = subprocess.run(
                ["hermes", "chat", "-q", prompt],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(Path.home() / "projects" / "daily-reports" / "mini_jev")
            )
            
            if result.returncode == 0 and result.stdout:
                # 清理输出，提取JSON
                output = result.stdout.strip()
                # 尝试提取JSON
                match = re.search(r'\{[^}]+\}', output, re.DOTALL)
                if match:
                    return match.group()
                return output
            else:
                if attempt < retries - 1:
                    time.sleep(1)
                    continue
                return '{"reasoning": "subprocess error", "choice": "error", "confidence": 0.0}'
                
        except subprocess.TimeoutExpired:
            print(f"  超时 (attempt {attempt+1})")
            if attempt < retries - 1:
                time.sleep(2)
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
        match = re.search(r'\{[^}]+\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        return {"reasoning": "parse error", "choice": "error", "confidence": 0.0}


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
    print("MiniJEV v2.0 测试 - Agnes LLM (思考链框架)")
    print(f"{'='*60}\n")
    
    results = []
    correct = 0
    total = len(TEST_CASES)
    
    for i, case in enumerate(TEST_CASES, 1):
        print(f"[{i}/{total}] {case['name']}")
        print(f"  状态: {case['state']}")
        print(f"  期望: {case['expected']}")
        
        # 构建思考链prompt
        options_str = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(case["options"])])
        prompt = f"""你是一个专业的结构化决策引擎。

状态: {case["state"]}
问题: {case["question"]}
可选答案:
{options_str}

请先思考推理过程，然后返回JSON：
{{"reasoning": "推理过程", "choice": "选项", "confidence": 0.0-1.0}}"""
        
        start = time.time()
        raw = call_agnes(prompt)
        latency = (time.time() - start) * 1000
        
        result = parse_response(raw)
        passed = result.get("choice") == case["expected"]
        if passed:
            correct += 1
        
        status = "✅" if passed else "❌"
        print(f"  {status} 结果: {result.get('choice', 'N/A')} (置信度: {result.get('confidence', 0):.2f}, 耗时: {latency:.0f}ms)")
        if result.get("reasoning"):
            print(f"     推理: {result['reasoning'][:80]}...")
        
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
        
        time.sleep(1)  # 避免过快请求
    
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
    output_file = Path(__file__).parent / f"test_results_v2_agnes_{int(time.time())}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "version": "2.0",
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
