#!/usr/bin/env python3
"""
MiniJEV - 超轻量级结构化决策引擎

测试版本：使用Mock LLM进行测试
"""

import json
import os
import sys
import re
import time
from typing import Dict, List, Optional, Any

# ============ 配置 ============

class JevConfig:
    """JEV配置"""
    DEFAULT_MODEL = os.getenv("JEV_MODEL", "glm-4.5-flash")
    
    SYSTEM_PROMPT = """你是一个结构化决策引擎。你的任务是对输入进行分类、评分或判断。

规则：
1. 只返回JSON格式，不要其他文字
2. choice字段必须是options中的其中一个
3. confidence是0.0到1.0之间的数字
4. 如果有probabilities字段，所有值加起来应该是1.0"""
    
    FEW_SHOT_EXAMPLES = [
        {
            "state": "客户说系统崩溃了，请尽快处理",
            "question": "紧急程度",
            "options": ["低", "中", "高"],
            "answer": {"choice": "高", "confidence": 0.95}
        },
        {
            "state": "请问你们的产品支持微信支付的接口吗",
            "question": "问题类型",
            "options": ["咨询", "投诉", "bug", "需求"],
            "answer": {"choice": "咨询", "confidence": 0.88}
        }
    ]


# ============ Mock LLM（用于测试）============

class MockLLM:
    """模拟LLM响应（用于测试）"""
    
    def __init__(self):
        self.call_count = 0
        self.total_latency = 0.0
    
    def call(self, prompt: str, model: str) -> str:
        """模拟LLM调用"""
        self.call_count += 1
        start = time.time()
        
        # 根据prompt内容生成模拟响应
        response = self._generate_mock_response(prompt)
        
        latency = time.time() - start
        self.total_latency += latency
        
        return response
    
    def _generate_mock_response(self, prompt: str) -> str:
        """根据prompt生成模拟响应"""
        # 解析options
        options_match = re.search(r'可选答案:\n(.+?)\n\n请返回', prompt, re.DOTALL)
        if not options_match:
            return '{"choice": "unknown", "confidence": 0.5}'
        
        options_text = options_match.group(1).strip()
        options = []
        for line in options_text.split('\n'):
            line = line.strip()
            if line and re.match(r'^\d+\.', line):
                option = re.sub(r'^\d+\.\s*', '', line)
                options.append(option)
        
        if not options:
            return '{"choice": "unknown", "confidence": 0.5}'
        
        # 根据关键词模拟决策
        state_match = re.search(r'状态: (.+?)\n问题:', prompt)
        state = state_match.group(1).strip() if state_match else ""
        
        question_match = re.search(r'问题: (.+?)\n可选答案', prompt)
        question = question_match.group(1).strip() if question_match else ""
        
        # 简单的关键词匹配逻辑
        if "崩溃" in state or "紧急" in state or "尽快" in state:
            choice = "紧急" if "紧急" in options else options[-1]
            confidence = 0.92
        elif "支付" in state or "账单" in state or "退款" in state:
            choice = "billing" if "billing" in options else options[0]
            confidence = 0.88
        elif "API" in state or "WebSocket" in state or "支持" in state:
            choice = "功能咨询" if "功能咨询" in options else options[0]
            confidence = 0.85
        elif "PPT" in state or "演示文稿" in state:
            choice = "ppt-master" if "ppt-master" in options else options[0]
            confidence = 0.90
        else:
            choice = options[0]
            confidence = 0.75
        
        # 生成概率分布
        probabilities = {}
        for i, opt in enumerate(options):
            if opt == choice:
                probabilities[opt] = confidence
            else:
                probabilities[opt] = (1 - confidence) / (len(options) - 1) if len(options) > 1 else 0
        
        return json.dumps({
            "choice": choice,
            "confidence": round(confidence, 2),
            "probabilities": {k: round(v, 2) for k, v in probabilities.items()}
        }, ensure_ascii=False)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "call_count": self.call_count,
            "avg_latency": self.total_latency / self.call_count if self.call_count > 0 else 0,
            "total_latency": self.total_latency
        }


# ============ 核心类 ============

class MiniJEV:
    """超轻量JEV实现"""
    
    def __init__(self, config: Optional[JevConfig] = None, llm=None):
        self.config = config or JevConfig()
        self.llm = llm or MockLLM()
    
    def decide(
        self,
        state: str,
        question: str,
        options: List[str],
        question_type: str = "choice"
    ) -> Dict[str, Any]:
        """
        做出决策
        
        Args:
            state: 输入状态（文本描述）
            question: 问题描述
            options: 可选答案列表
            question_type: 问题类型 ("choice"/"score"/"noul")
            
        Returns:
            {"choice": "...", "confidence": 0.0-1.0, "probabilities": {...}}
        """
        # 构建prompt
        prompt = self._build_prompt(state, question, options, question_type)
        
        # 调用LLM
        raw_response = self.llm.call(prompt, self.config.DEFAULT_MODEL)
        
        # 解析结果
        return self._parse_response(raw_response, options)
    
    def _build_prompt(self, state: str, question: str, options: List[str], question_type: str) -> str:
        """构建结构化Prompt"""
        
        # 格式化选项
        options_str = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
        
        # 构建few-shot示例
        few_shot_str = ""
        if len(self.config.FEW_SHOT_EXAMPLES) > 0:
            few_shot_str = "【示例】\n"
            for ex in self.config.FEW_SHOT_EXAMPLES:
                few_shot_str += f"状态: {ex['state']}\n"
                few_shot_str += f"问题: {ex['question']}\n"
                few_shot_str += f"答案: {json.dumps(ex['answer'], ensure_ascii=False)}\n\n"
        
        prompt = f"""{self.config.SYSTEM_PROMPT}

{few_shot_str}【当前任务】
状态: {state}
问题: {question}
可选答案:
{options_str}

请返回JSON格式：
{{"choice": "选中的选项", "confidence": 0.0-1.0, "probabilities": {{"选项1": 0.x, "选项2": 0.x, ...}}}}"""
        
        return prompt
    
    def _parse_response(self, raw: str, options: List[str]) -> Dict[str, Any]:
        """解析LLM返回的JSON"""
        try:
            # 尝试直接解析
            result = json.loads(raw.strip())
        except json.JSONDecodeError:
            # 尝试从文本中提取JSON
            match = re.search(r'\{[^}]+\}', raw)
            if match:
                result = json.loads(match.group())
            else:
                # fallback: 返回默认值
                result = {
                    "choice": options[0] if options else "unknown",
                    "confidence": 0.5,
                    "probabilities": {opt: 1.0/len(options) if options else 0.5 for opt in options}
                }
        
        # 确保必须有choice字段
        if "choice" not in result:
            result["choice"] = options[0] if options else "unknown"
        
        # 确保confidence在0-1之间
        if "confidence" not in result:
            result["confidence"] = 0.5
        else:
            result["confidence"] = min(1.0, max(0.0, float(result["confidence"])))
        
        return result
    
    def batch_decide(self, requests: List[Dict]) -> List[Dict]:
        """批量决策"""
        return [self.decide(**req) for req in requests]
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        if hasattr(self.llm, 'get_stats'):
            return self.llm.get_stats()
        return {}


# ============ 测试函数 ============

def test_basic_decision():
    """基础决策测试"""
    print("\n" + "=" * 60)
    print("测试1: 基础决策")
    print("=" * 60)
    
    jev = MiniJEV()
    
    # 测试用例
    test_cases = [
        {
            "name": "邮件紧急程度",
            "state": "客户说系统崩溃了，请尽快处理",
            "question": "紧急程度",
            "options": ["低", "中", "高", "紧急"]
        },
        {
            "name": "问题类型分类",
            "state": "你们的API支持 WebSocket 吗",
            "question": "问题类型",
            "options": ["功能咨询", "技术支持", "bug报告", "功能需求"]
        },
        {
            "name": "Skill路由",
            "state": "帮我生成一份PPT",
            "question": "应该加载哪个skill",
            "options": ["ppt-master", "pptx-editing", "text-summary"]
        },
        {
            "name": "代码审查风险",
            "state": "新增了discount参数，改变了函数签名",
            "question": "风险等级",
            "options": ["低", "中", "高", "极高"]
        }
    ]
    
    results = []
    for i, tc in enumerate(test_cases, 1):
        print(f"\n测试{i}: {tc['name']}")
        print(f"  输入: {tc['state']}")
        
        try:
            result = jev.decide(
                state=tc["state"],
                question=tc["question"],
                options=tc["options"]
            )
            print(f"  结果: {json.dumps(result, ensure_ascii=False)}")
            results.append({"test": tc["name"], "result": result, "success": True})
        except Exception as e:
            print(f"  错误: {e}")
            results.append({"test": tc["name"], "error": str(e), "success": False})
    
    return results


def test_batch_decision():
    """批量决策测试"""
    print("\n" + "=" * 60)
    print("测试2: 批量决策")
    print("=" * 60)
    
    jev = MiniJEV()
    
    requests = [
        {"state": "邮件A", "question": "紧急程度", "options": ["低", "高"]},
        {"state": "邮件B", "question": "紧急程度", "options": ["低", "高"]},
        {"state": "邮件C", "question": "紧急程度", "options": ["低", "高"]}
    ]
    
    print(f"\n发送 {len(requests)} 个请求...")
    start = time.time()
    results = jev.batch_decide(requests)
    elapsed = time.time() - start
    
    for i, (req, res) in enumerate(zip(requests, results), 1):
        print(f"  请求{i}: {res}")
    
    print(f"\n批量决策耗时: {elapsed:.3f}秒")
    print(f"平均每请求: {elapsed/len(requests):.3f}秒")
    
    return results


def test_edge_cases():
    """边界情况测试"""
    print("\n" + "=" * 60)
    print("测试3: 边界情况")
    print("=" * 60)
    
    jev = MiniJEV()
    
    # 测试1: 空选项
    print("\n测试3.1: 空选项列表")
    try:
        result = jev.decide("测试", "问题", [])
        print(f"  结果: {result}")
    except Exception as e:
        print(f"  预期错误: {e}")
    
    # 测试2: 单个选项
    print("\n测试3.2: 单个选项")
    result = jev.decide("测试", "问题", ["只有这个"])
    print(f"  结果: {result}")
    
    # 测试3: 超长文本
    print("\n测试3.3: 超长文本")
    long_text = "测试文本 " * 100
    result = jev.decide(long_text, "问题", ["A", "B"])
    print(f"  结果: {result}")
    
    # 测试4: 特殊字符
    print("\n测试3.4: 特殊字符")
    special_text = "测试 \"引号\" 和 \\反斜杠\\ 和\n换行"
    result = jev.decide(special_text, "问题", ["A", "B"])
    print(f"  结果: {result}")


def test_performance():
    """性能测试"""
    print("\n" + "=" * 60)
    print("测试4: 性能测试")
    print("=" * 60)
    
    jev = MiniJEV()
    
    # 测试100次决策
    iterations = 100
    print(f"\n执行 {iterations} 次决策...")
    
    start = time.time()
    for i in range(iterations):
        jev.decide("测试文本", "问题", ["选项A", "选项B", "选项C"])
    elapsed = time.time() - start
    
    stats = jev.get_stats()
    
    print(f"总耗时: {elapsed:.3f}秒")
    print(f"平均每次: {elapsed/iterations*1000:.2f}毫秒")
    print(f"QPS: {iterations/elapsed:.2f}")
    print(f"LLM调用次数: {stats.get('call_count', 0)}")
    print(f"LLM平均延迟: {stats.get('avg_latency', 0)*1000:.2f}毫秒")


def demo():
    """完整演示"""
    print("\n" + "=" * 60)
    print("MiniJEV 完整演示")
    print("=" * 60)
    
    # 运行所有测试
    test_basic_decision()
    test_batch_decision()
    test_edge_cases()
    test_performance()
    
    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


def main():
    """主入口"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--demo":
            demo()
        elif sys.argv[1] == "--test-basic":
            test_basic_decision()
        elif sys.argv[1] == "--test-batch":
            test_batch_decision()
        elif sys.argv[1] == "--test-edge":
            test_edge_cases()
        elif sys.argv[1] == "--test-perf":
            test_performance()
        else:
            print(f"未知参数: {sys.argv[1]}")
            print("用法: python mini_jev_test.py [--demo|--test-basic|--test-batch|--test-edge|--test-perf]")
    else:
        demo()


if __name__ == "__main__":
    main()
