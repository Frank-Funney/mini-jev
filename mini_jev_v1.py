#!/usr/bin/env python3
"""
MiniJEV v1.0 - 超轻量级结构化决策引擎
完整实现版本
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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============ 数据类型定义 ============

class DecisionType(Enum):
    """决策类型枚举"""
    CHOICE = "choice"      # 从多个选项中选一个
    SCORE = "score"        # 在有序刻度上评分
    NOUL = "noul"          # Yes/No概率判断


@dataclass
class DecisionResult:
    """决策结果数据类"""
    choice: str                           # 选择的选项
    confidence: float                     # 置信度 0-1
    probabilities: Dict[str, float]       # 各选项概率
    decision_type: str                    # 决策类型
    raw_response: str                     # 原始响应
    latency_ms: float                     # 耗时（毫秒）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"Decision(choice='{self.choice}', confidence={self.confidence:.2f}, type={self.decision_type})"
    
    def __repr__(self) -> str:
        return self.__str__()


# ============ 配置类 ============

class JevConfig:
    """JEV配置类"""
    
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
                    for opt in reversed(options):
                        if "紧急" in opt or "高" in opt:
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


# ============ CLI入口 ============

def main():
    """CLI主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="MiniJEV - 超轻量级结构化决策引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基础决策
  python3 mini_jev.py decide --state "客户说系统崩溃了" --question "紧急程度" --options "低,中,高,紧急"
  
  # 批量决策
  python3 mini_jev.py batch --input requests.json
  
  # 查看版本
  python3 mini_jev.py --version
        """
    )
    
    parser.add_argument("--version", action="version", version="MiniJEV 1.0.0")
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # decide命令
    decide_parser = subparsers.add_parser("decide", help="单次决策")
    decide_parser.add_argument("--state", required=True, help="输入状态")
    decide_parser.add_argument("--question", required=True, help="问题描述")
    decide_parser.add_argument("--options", required=True, help="可选答案（逗号分隔）")
    decide_parser.add_argument("--type", choices=["choice", "score", "noul"], default="choice", help="决策类型")
    decide_parser.add_argument("--json", action="store_true", help="以JSON格式输出")
    
    # batch命令
    batch_parser = subparsers.add_parser("batch", help="批量决策")
    batch_parser.add_argument("--input", required=True, help="JSON文件路径")
    batch_parser.add_argument("--type", choices=["choice", "score", "noul"], default="choice", help="决策类型")
    batch_parser.add_argument("--json", action="store_true", help="以JSON格式输出")
    
    args = parser.parse_args()
    
    if args.command == "decide":
        _handle_decide(args)
    elif args.command == "batch":
        _handle_batch(args)
    else:
        parser.print_help()


def _handle_decide(args):
    """处理decide命令"""
    options = [opt.strip() for opt in args.options.split(",")]
    
    jev = MiniJEV()
    decision_type = DecisionType(args.type)
    
    result = jev.decide(
        state=args.state,
        question=args.question,
        options=options,
        decision_type=decision_type
    )
    
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"\n决策结果:")
        print(f"  选择: {result.choice}")
        print(f"  置信度: {result.confidence:.2f}")
        print(f"  概率分布:")
        for opt, prob in result.probabilities.items():
            bar = "█" * int(prob * 20)
            print(f"    {opt:20s} {prob:.2%} {bar}")
        print(f"  耗时: {result.latency_ms:.2f}ms\n")


def _handle_batch(args):
    """处理batch命令"""
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            requests = json.load(f)
    except Exception as e:
        print(f"错误: 无法读取文件 - {e}", file=sys.stderr)
        sys.exit(1)
    
    # 确保requests是列表
    if isinstance(requests, str):
        try:
            requests = json.loads(requests)
        except:
            requests = [requests]
    
    if not isinstance(requests, list):
        requests = [requests]
    
    jev = MiniJEV()
    decision_type = DecisionType(args.type)
    
    results = jev.batch_decide(requests, decision_type=decision_type)
    
    if args.json:
        output = [r.to_dict() for r in results]
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"\n批量决策结果 ({len(results)}个):")
        for i, (req, res) in enumerate(zip(requests, results), 1):
            state_short = req['state'][:30] + "..." if len(req['state']) > 30 else req['state']
            print(f"  {i}. {state_short} → {res.choice} ({res.confidence:.2f})")
        print()


if __name__ == "__main__":
    main()
