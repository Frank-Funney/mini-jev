#!/usr/bin/env python3
"""
MiniJEV v1.0 - 超轻量级结构化决策引擎

特性:
- 零额外依赖（纯Python标准库）
- 支持Choice/Score/Noul三种决策类型
- Few-shot学习提升准确率
- JSON容错解析
- 批量决策支持
- 性能监控

使用示例:
    from mini_jev import MiniJEV
    
    jev = MiniJEV()
    result = jev.decide(
        state="客户说系统崩溃了",
        question="紧急程度",
        options=["低", "中", "高", "紧急"]
    )
    print(result["choice"])  # "紧急"
    print(result["confidence"])  # 0.92
"""

import json
import os
import sys
import re
import time
import logging
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============ 数据类型 ============

class DecisionType(Enum):
    """决策类型"""
    CHOICE = "choice"      # 从多个选项中选一个
    SCORE = "score"        # 在有序刻度上评分
    NOUL = "noul"          # Yes/No概率判断


@dataclass
class DecisionResult:
    """决策结果"""
    choice: str              # 选择的选项
    confidence: float        # 置信度 0-1
    probabilities: Dict[str, float]  # 各选项概率
    decision_type: str       # 决策类型
    raw_response: str        # 原始响应
    latency_ms: float        # 耗时（毫秒）
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"Decision(choice='{self.choice}', confidence={self.confidence:.2f}, type={self.decision_type})"


# ============ 配置类 ============

class JevConfig:
    """JEV配置"""
    
    def __init__(
        self,
        model: str = "default",
        system_prompt: Optional[str] = None,
        few_shot_examples: Optional[List[Dict]] = None,
        max_tokens: int = 500,
        temperature: float = 0.1,
        enable_logging: bool = False
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.enable_logging = enable_logging
        
        # System prompt
        if system_prompt:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = self._default_system_prompt()
        
        # Few-shot examples
        if few_shot_examples:
            self.few_shot_examples = few_shot_examples
        else:
            self.few_shot_examples = self._default_few_shot_examples()
    
    def _default_system_prompt(self) -> str:
        """默认System Prompt"""
        return """你是一个专业的结构化决策引擎。你的任务是对输入进行精准分类、评分或判断。

核心规则：
1. 只返回JSON格式，不要任何其他文字
2. choice字段必须是options中的其中一个
3. confidence是0.0到1.0之间的数字，表示置信度
4. probabilities字段中所有值加起来应该等于1.0
5. 基于输入内容做出最合理的判断

输出格式：
{"choice": "选中的选项", "confidence": 0.0-1.0, "probabilities": {"选项1": 0.x, "选项2": 0.x, ...}}"""
    
    def _default_few_shot_examples(self) -> List[Dict]:
        """默认Few-shot示例"""
        return [
            {
                "state": "客户说系统崩溃了，请尽快处理",
                "question": "紧急程度",
                "options": ["低", "中", "高", "紧急"],
                "answer": {"choice": "紧急", "confidence": 0.95}
            },
            {
                "state": "请问你们的产品支持微信支付的接口吗",
                "question": "问题类型",
                "options": ["功能咨询", "技术支持", "bug报告", "功能需求"],
                "answer": {"choice": "功能咨询", "confidence": 0.88}
            },
            {
                "state": "这段代码有内存泄漏风险",
                "question": "风险等级",
                "options": ["低", "中", "高", "极高"],
                "answer": {"choice": "高", "confidence": 0.82}
            }
        ]
    
    def add_few_shot_example(self, example: Dict):
        """添加few-shot示例"""
        self.few_shot_examples.append(example)
    
    def clear_few_shot_examples(self):
        """清空few-shot示例"""
        self.few_shot_examples = []
    
    def get_prompt_stats(self) -> Dict:
        """获取prompt统计"""
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "few_shot_count": len(self.few_shot_examples),
            "system_prompt_length": len(self.system_prompt)
        }


# ============ LLM接口类 ============

class LLMInterface:
    """LLM接口基类"""
    
    def __init__(self, config: JevConfig):
        self.config = config
        self.call_count = 0
        self.total_latency = 0.0
        self.error_count = 0
    
    def call(self, prompt: str, model: Optional[str] = None) -> str:
        """调用LLM（子类实现）"""
        raise NotImplementedError("子类必须实现call方法")
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "call_count": self.call_count,
            "error_count": self.error_count,
            "avg_latency_ms": (self.total_latency / self.call_count * 1000) if self.call_count > 0 else 0,
            "total_latency_ms": self.total_latency * 1000
        }
    
    def reset_stats(self):
        """重置统计"""
        self.call_count = 0
        self.total_latency = 0.0
        self.error_count = 0


class MockLLM(LLMInterface):
    """模拟LLM（用于测试）"""
    
    def __init__(self, config: JevConfig):
        super().__init__(config)
        self._response_cache = {}
    
    def call(self, prompt: str, model: Optional[str] = None) -> str:
        """模拟LLM调用"""
        start = time.time()
        self.call_count += 1
        
        # 根据prompt生成模拟响应
        response = self._generate_mock_response(prompt)
        
        latency = time.time() - start
        self.total_latency += latency
        
        if self.config.enable_logging:
            logger.debug(f"MockLLM调用完成，耗时{latency*1000:.2f}ms")
        
        return response
    
    def _generate_mock_response(self, prompt: str) -> str:
        """生成模拟响应"""
        # 解析options
        options_match = re.search(r'可选答案:\n(.+?)\n\n请返回', prompt, re.DOTALL)
        if not options_match:
            return '{"choice": "unknown", "confidence": 0.5, "probabilities": {}}'
        
        options_text = options_match.group(1).strip()
        options = []
        for line in options_text.split('\n'):
            line = line.strip()
            if line and re.match(r'^\d+\.', line):
                option = re.sub(r'^\d+\.\s*', '', line)
                options.append(option)
        
        if not options:
            return '{"choice": "unknown", "confidence": 0.5, "probabilities": {}}'
        
        # 解析state和question
        state_match = re.search(r'状态: (.+?)\n问题:', prompt)
        state = state_match.group(1).strip() if state_match else ""
        
        question_match = re.search(r'问题: (.+?)\n可选答案', prompt)
        question = question_match.group(1).strip() if question_match else ""
        
        # 关键词匹配逻辑
        choice, confidence = self._match_keywords(state, question, options)
        
        # 生成概率分布
        probabilities = self._generate_probabilities(choice, options, confidence)
        
        return json.dumps({
            "choice": choice,
            "confidence": round(confidence, 2),
            "probabilities": probabilities
        }, ensure_ascii=False)
    
    def _match_keywords(self, state: str, question: str, options: List[str]) -> tuple:
        """关键词匹配"""
        # 紧急程度判断
        if "紧急程度" in question or "urgency" in question.lower():
            urgency_keywords = ["崩溃", "紧急", "尽快", "马上", "立即", "严重", "故障"]
            for kw in urgency_keywords:
                if kw in state:
                    # 找最高的紧急级别
                    for opt in reversed(options):
                        if "紧急" in opt or "高" in opt or "高" in opt:
                            return opt, 0.92
            return options[0], 0.5
        
        # 问题类型判断
        if "问题类型" in question or "type" in question.lower():
            if any(kw in state for kw in ["API", "WebSocket", "支持", "接口"]):
                for opt in options:
                    if "咨询" in opt:
                        return opt, 0.88
            elif any(kw in state for kw in ["bug", "错误", "崩溃", "故障"]):
                for opt in options:
                    if "bug" in opt.lower() or "故障" in opt:
                        return opt, 0.85
            elif any(kw in state for kw in ["需求", "功能", "想要"]):
                for opt in options:
                    if "需求" in opt:
                        return opt, 0.82
            return options[0], 0.6
        
        # Skill路由判断
        if "skill" in question.lower() or "路由" in question:
            if "PPT" in state or "演示文稿" in state:
                for opt in options:
                    if "ppt" in opt.lower():
                        return opt, 0.90
            elif "文本" in state or "总结" in state:
                for opt in options:
                    if "text" in opt.lower() or "总结" in opt:
                        return opt, 0.88
            return options[0], 0.6
        
        # 默认：返回第一个选项
        return options[0], 0.75
    
    def _generate_probabilities(self, choice: str, options: List[str], confidence: float) -> Dict[str, float]:
        """生成概率分布"""
        probabilities = {}
        for i, opt in enumerate(options):
            if opt == choice:
                probabilities[opt] = confidence
            else:
                remaining = 1.0 - confidence
                probabilities[opt] = remaining / (len(options) - 1) if len(options) > 1 else 0
        
        # 归一化
        total = sum(probabilities.values())
        if total > 0:
            probabilities = {k: round(v/total, 2) for k, v in probabilities.items()}
        
        return probabilities


# ============ 核心决策类 ============

class MiniJEV:
    """
    MiniJEV - 超轻量级结构化决策引擎
    
    用法:
        jev = MiniJEV()
        result = jev.decide(
            state="客户说系统崩溃了",
            question="紧急程度",
            options=["低", "中", "高", "紧急"]
        )
        print(result.choice)  # "紧急"
        print(result.confidence)  # 0.92
    """
    
    def __init__(
        self,
        config: Optional[JevConfig] = None,
        llm: Optional[LLMInterface] = None
    ):
        self.config = config or JevConfig()
        self.llm = llm or MockLLM(self.config)
        self._decision_history = []
    
    def decide(
        self,
        state: str,
        question: str,
        options: List[str],
        decision_type: Union[str, DecisionType] = DecisionType.CHOICE
    ) -> DecisionResult:
        """
        做出决策
        
        Args:
            state: 输入状态（文本描述）
            question: 问题描述
            options: 可选答案列表
            decision_type: 决策类型 ("choice"/"score"/"noul")
            
        Returns:
            DecisionResult对象
        """
        start_time = time.time()
        
        # 参数验证
        if not state or not state.strip():
            raise ValueError("state不能为空")
        if not options or len(options) == 0:
            raise ValueError("options不能为空")
        
        # 构建prompt
        prompt = self._build_prompt(state, question, options, decision_type)
        
        # 调用LLM
        raw_response = self.llm.call(prompt, self.config.model)
        
        # 解析结果
        result_dict = self._parse_response(raw_response, options)
        
        # 计算耗时
        latency_ms = (time.time() - start_time) * 1000
        
        # 创建DecisionResult
        result = DecisionResult(
            choice=result_dict.get("choice", options[0]),
            confidence=result_dict.get("confidence", 0.5),
            probabilities=result_dict.get("probabilities", {}),
            decision_type=str(decision_type) if isinstance(decision_type, DecisionType) else decision_type,
            raw_response=raw_response,
            latency_ms=latency_ms
        )
        
        # 记录历史
        self._decision_history.append({
            "timestamp": time.time(),
            "state": state,
            "question": question,
            "options": options,
            "result": result.to_dict()
        })
        
        # 限制历史记录大小
        if len(self._decision_history) > 1000:
            self._decision_history = self._decision_history[-500:]
        
        if self.config.enable_logging:
            logger.info(f"决策完成: {result.choice} (置信度: {result.confidence:.2f}, 耗时: {latency_ms:.2f}ms)")
        
        return result
    
    def batch_decide(
        self,
        requests: List[Dict],
        decision_type: Union[str, DecisionType] = DecisionType.CHOICE
    ) -> List[DecisionResult]:
        """
        批量决策
        
        Args:
            requests: 请求列表，每个元素包含state/question/options
            decision_type: 决策类型
            
        Returns:
            决策结果列表
        """
        results = []
        for req in requests:
            result = self.decide(
                state=req["state"],
                question=req.get("question", "分类"),
                options=req["options"],
                decision_type=decision_type
            )
            results.append(result)
        return results
    
    def _build_prompt(
        self,
        state: str,
        question: str,
        options: List[str],
        decision_type: Union[str, DecisionType]
    ) -> str:
        """构建结构化Prompt"""
        
        # 格式化选项
        options_str = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
        
        # 决策类型说明
        type_hint = ""
        if decision_type == DecisionType.SCORE or decision_type == "score":
            type_hint = "\n【评分说明】请根据有序刻度进行评分"
        elif decision_type == DecisionType.NOUL or decision_type == "noul":
            type_hint = "\n【判断说明】请判断条件是否成立（是/否）"
        
        # 构建few-shot示例
        few_shot_str = ""
        if len(self.config.few_shot_examples) > 0:
            few_shot_str = "【示例】\n"
            for ex in self.config.few_shot_examples:
                few_shot_str += f"状态: {ex['state']}\n"
                few_shot_str += f"问题: {ex['question']}\n"
                few_shot_str += f"答案: {json.dumps(ex['answer'], ensure_ascii=False)}\n\n"
        
        prompt = f"""{self.config.system_prompt}
{type_hint}

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
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {e}, 原始响应: {raw[:200]}")
            # 尝试从文本中提取JSON
            match = re.search(r'\{[^}]+\}', raw)
            if match:
                try:
                    result = json.loads(match.group())
                except json.JSONDecodeError:
                    result = None
            else:
                result = None
            
            if result is None:
                # fallback: 返回默认值
                result = {
                    "choice": options[0],
                    "confidence": 0.5,
                    "probabilities": {opt: 1.0/len(options) for opt in options}
                }
        
        # 确保必须有choice字段
        if "choice" not in result:
            result["choice"] = options[0]
        
        # 确保choice在options中
        if result["choice"] not in options:
            result["choice"] = options[0]
        
        # 确保confidence在0-1之间
        if "confidence" not in result:
            result["confidence"] = 0.5
        else:
            result["confidence"] = min(1.0, max(0.0, float(result["confidence"])))
        
        # 确保probabilities存在且和为1
        if "probabilities" not in result or not result["probabilities"]:
            result["probabilities"] = {opt: 1.0/len(options) for opt in options}
        else:
            # 归一化
            probs = result["probabilities"]
            total = sum(probs.values())
            if total > 0 and abs(total - 1.0) > 0.01:
                result["probabilities"] = {k: round(v/total, 2) for k, v in probs.items()}
        
        return result
    
    def get_decision_history(self, limit: int = 10) -> List[Dict]:
        """获取决策历史"""
        return self._decision_history[-limit:]
    
    def clear_history(self):
        """清空决策历史"""
        self._decision_history = []
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        llm_stats = self.llm.get_stats() if hasattr(self.llm, 'get_stats') else {}
        config_stats = self.config.get_prompt_stats()
        
        return {
            "llm": llm_stats,
            "config": config_stats,
            "decision_count": len(self._decision_history),
            "avg_latency_ms": sum(d["result"]["latency_ms"] for d in self._decision_history) / len(self._decision_history) if self._decision_history else 0
        }
    
    def reset_stats(self):
        """重置统计"""
        if hasattr(self.llm, 'reset_stats'):
            self.llm.reset_stats()
        self._decision_history = []


# ============ 便捷函数 ============

def quick_decide(state: str, question: str, options: List[str]) -> Dict:
    """快速决策函数"""
    jev = MiniJEV()
    result = jev.decide(state, question, options)
    return result.to_dict()


def batch_quick_decide(requests: List[Dict]) -> List[Dict]:
    """批量快速决策"""
    jev = MiniJEV()
    results = jev.batch_decide(requests)
    return [r.to_dict() for r in results]


# ============ 测试代码 ============

def test_basic():
    """基础功能测试"""
    print("\n" + "=" * 60)
    print("测试1: 基础功能")
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
            "name": "代码风险评级",
            "state": "新增了discount参数，改变了函数签名",
            "question": "风险等级",
            "options": ["低", "中", "高", "极高"]
        }
    ]
    
    for i, tc in enumerate(test_cases, 1):
        print(f"\n测试{i}: {tc['name']}")
        print(f"  输入: {tc['state'][:50]}...")
        
        result = jev.decide(
            state=tc["state"],
            question=tc["question"],
            options=tc["options"]
        )
        
        print(f"  结果: {result}")
        print(f"  详情: {json.dumps(result.to_dict(), ensure_ascii=False, indent=4)}")
    
    return jev


def test_batch():
    """批量决策测试"""
    print("\n" + "=" * 60)
    print("测试2: 批量决策")
    print("=" * 60)
    
    jev = MiniJEV()
    
    requests = [
        {"state": "邮件A：系统崩溃了", "question": "紧急程度", "options": ["低", "高"]},
        {"state": "邮件B：一般咨询", "question": "紧急程度", "options": ["低", "高"]},
        {"state": "邮件C：紧急问题", "question": "紧急程度", "options": ["低", "高"]}
    ]
    
    print(f"\n发送 {len(requests)} 个请求...")
    start = time.time()
    results = jev.batch_decide(requests)
    elapsed = time.time() - start
    
    for i, (req, res) in enumerate(zip(requests, results), 1):
        print(f"  请求{i}: {res.choice} (置信度: {res.confidence:.2f})")
    
    print(f"\n批量决策耗时: {elapsed*1000:.2f}ms")
    print(f"平均每请求: {elapsed/len(requests)*1000:.2f}ms")
    
    return jev


def test_edge_cases():
    """边界情况测试"""
    print("\n" + "=" * 60)
    print("测试3: 边界情况")
    print("=" * 60)
    
    jev = MiniJEV()
    
    # 测试1: 空选项
    print("\n测试3.1: 空选项列表")
    try:
        jev.decide("测试", "问题", [])
        print("  错误: 应该抛出异常")
    except ValueError as e:
        print(f"  正确捕获: {e}")
    
    # 测试2: 单个选项
    print("\n测试3.2: 单个选项")
    result = jev.decide("测试", "问题", ["只有这个"])
    print(f"  结果: {result.choice} (置信度: {result.confidence:.2f})")
    
    # 测试3: 超长文本
    print("\n测试3.3: 超长文本")
    long_text = "测试文本 " * 200
    result = jev.decide(long_text, "问题", ["A", "B", "C"])
    print(f"  结果: {result.choice} (耗时: {result.latency_ms:.2f}ms)")
    
    # 测试4: 特殊字符
    print("\n测试3.4: 特殊字符")
    special_text = '测试 "引号" 和 \\反斜杠\\ 和\n换行'
    result = jev.decide(special_text, "问题", ["A", "B"])
    print(f"  结果: {result.choice}")
    
    # 测试5: 中文选项
    print("\n测试3.5: 中文选项")
    result = jev.decide("测试中文", "问题", ["选项一", "选项二", "选项三"])
    print(f"  结果: {result.choice}")


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
    
    print(f"总耗时: {elapsed*1000:.2f}ms")
    print(f"平均每次: {elapsed/iterations*1000:.2f}ms")
    print(f"QPS: {iterations/elapsed:.2f}")
    print(f"LLM调用次数: {stats['llm']['call_count']}")
    print(f"LLM平均延迟: {stats['llm']['avg_latency_ms']:.2f}ms")


def test_history():
    """历史记录测试"""
    print("\n" + "=" * 60)
    print("测试5: 历史记录")
    print("=" * 60)
    
    jev = MiniJEV()
    
    # 做一些决策
    for i in range(5):
        jev.decide(f"测试状态{i}", "问题", ["A", "B"])
    
    # 获取历史
    history = jev.get_decision_history(limit=3)
    print(f"\n最近3次决策:")
    for i, h in enumerate(history, 1):
        print(f"  {i}. {h['result']['choice']} (置信度: {h['result']['confidence']:.2f})")
    
    # 清空历史
    jev.clear_history()
    print(f"\n清空后历史记录数: {len(jev.get_decision_history())}")


def demo():
    """完整演示"""
    print("\n" + "=" * 60)
    print("MiniJEV v1.0 完整演示")
    print("=" * 60)
    
    # 运行所有测试
    jev1 = test_basic()
    jev2 = test_batch()
    test_edge_cases()
    test_performance()
    test_history()
    
    # 打印统计
    print("\n" + "=" * 60)
    print("最终统计")
    print("=" * 60)
    stats = jev1.get_stats()
    print(f"决策次数: {stats['decision_count']}")
    print(f"LLM调用: {stats['llm']['call_count']}")
    print(f"平均延迟: {stats['avg_latency_ms']:.2f}ms")
    print(f"Few-shot示例数: {stats['config']['few_shot_count']}")
    
    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


def main():
    """主入口"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--demo":
            demo()
        elif sys.argv[1] == "--test-basic":
            test_basic()
        elif sys.argv[1] == "--test-batch":
            test_batch()
        elif sys.argv[1] == "--test-edge":
            test_edge_cases()
        elif sys.argv[1] == "--test-perf":
            test_performance()
        elif sys.argv[1] == "--test-history":
            test_history()
        else:
            print(f"未知参数: {sys.argv[1]}")
            print("用法: python mini_jev.py [--demo|--test-basic|--test-batch|--test-edge|--test-perf|--test-history]")
    else:
        demo()


if __name__ == "__main__":
    main()
