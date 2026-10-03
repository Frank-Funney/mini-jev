#!/usr/bin/env python3
"""
MiniJEV v2.0 - 思考链推理决策引擎
集成Meta Muse Spark风格的深度推理框架
"""

import json
import os
import sys
import re
import time
import logging
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict, field
from enum import Enum

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
    choice: str
    confidence: float
    probabilities: Dict[str, float]
    decision_type: str
    raw_response: str
    latency_ms: float
    reasoning: str = ""  # 新增：推理过程
    is_correct: bool = False  # 新增：是否正确
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
    
    def __str__(self) -> str:
        status = "✅" if self.is_correct else "❌"
        return f"{status} Decision(choice='{self.choice}', confidence={self.confidence:.2f}, type={self.decision_type})"
    
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
        enable_logging: bool = False,
        enable_reasoning: bool = True  # 新增：启用推理链
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.enable_logging = enable_logging
        self.enable_reasoning = enable_reasoning
        
        if system_prompt:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = self._default_system_prompt()
        
        if few_shot_examples:
            self.few_shot_examples = few_shot_examples
        else:
            self.few_shot_examples = self._default_few_shot_examples()
    
    def _default_system_prompt(self) -> str:
        """默认System Prompt - 思考链版本"""
        return """你是一个专业的结构化决策引擎，具备深度推理能力。

核心规则：
1. 分析输入时，先识别关键信息和上下文
2. 考虑所有选项的优缺点
3. 做出判断后，验证答案的合理性
4. 只返回JSON格式，不要任何其他文字

输出格式：
{"reasoning": "你的推理过程", "choice": "选中的选项", "confidence": 0.0-1.0, "probabilities": {"选项1": 0.x, "选项2": 0.x, ...}}

领域知识：
- bug报告：系统错误、崩溃、异常行为
- 功能咨询：询问产品能力、接口支持
- 技术支持：安装问题、配置问题、使用指导
- 功能需求：新功能请求、改进建议"""
    
    def _default_few_shot_examples(self) -> List[Dict]:
        """默认Few-shot示例 - 增强版"""
        return [
            {
                "state": "客户说系统崩溃了，请尽快处理",
                "question": "紧急程度",
                "options": ["低", "中", "高", "紧急"],
                "answer": {
                    "reasoning": "系统崩溃意味着服务完全不可用，影响所有用户，属于最高优先级",
                    "choice": "紧急",
                    "confidence": 0.95
                }
            },
            {
                "state": "用户反馈系统返回错误500",
                "question": "问题类型",
                "options": ["功能咨询", "技术支持", "bug报告", "功能需求"],
                "answer": {
                    "reasoning": "HTTP 500是服务器内部错误，表示程序执行失败，属于代码层面的bug",
                    "choice": "bug报告",
                    "confidence": 0.90
                }
            },
            {
                "state": "请问你们的产品支持微信支付的接口吗",
                "question": "问题类型",
                "options": ["功能咨询", "技术支持", "bug报告", "功能需求"],
                "answer": {
                    "reasoning": "用户在询问产品是否具备某种功能，属于功能层面的咨询",
                    "choice": "功能咨询",
                    "confidence": 0.92
                }
            },
            {
                "state": "修改核心模块的函数签名",
                "question": "风险等级",
                "options": ["低", "中", "高", "极高"],
                "answer": {
                    "reasoning": "函数签名变更会导致所有调用方需要修改，影响范围大，但不涉及数据迁移或业务逻辑改变，属于高风险",
                    "choice": "高",
                    "confidence": 0.88
                }
            },
            {
                "state": "CPU占用率达到95%，持续告警",
                "question": "紧急程度",
                "options": ["低", "中", "高", "紧急"],
                "answer": {
                    "reasoning": "CPU 95%接近饱和，可能导致服务雪崩，需要立即处理",
                    "choice": "紧急",
                    "confidence": 0.95
                }
            },
            {
                "state": "订单量同比上周下降80%",
                "question": "是否触发异常告警",
                "options": ["是", "否"],
                "answer": {
                    "reasoning": "80%的下降幅度远超正常波动范围（通常±10%），极可能是系统故障或业务异常",
                    "choice": "是",
                    "confidence": 0.98
                }
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
        raise NotImplementedError("子类必须实现call方法")
    
    def get_stats(self) -> Dict:
        return {
            "call_count": self.call_count,
            "error_count": self.error_count,
            "avg_latency_ms": (self.total_latency / self.call_count * 1000) if self.call_count > 0 else 0,
            "total_latency_ms": self.total_latency * 1000
        }
    
    def reset_stats(self):
        self.call_count = 0
        self.total_latency = 0.0
        self.error_count = 0


class MockLLM(LLMInterface):
    """模拟LLM（用于测试）"""
    
    def __init__(self, config: JevConfig):
        super().__init__(config)
    
    def call(self, prompt: str, model: Optional[str] = None) -> str:
        start = time.time()
        self.call_count += 1
        
        response = self._generate_mock_response(prompt)
        
        latency = time.time() - start
        self.total_latency += latency
        
        if self.config.enable_logging:
            logger.debug(f"MockLLM调用完成，耗时{latency*1000:.2f}ms")
        
        return response
    
    def _generate_mock_response(self, prompt: str) -> str:
        """生成模拟响应 - v2.0增强版"""
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
        
        state_match = re.search(r'状态: (.+?)\n问题:', prompt)
        state = state_match.group(1).strip() if state_match else ""
        
        question_match = re.search(r'问题: (.+?)\n可选答案', prompt)
        question = question_match.group(1).strip() if question_match else ""
        
        # 改进的关键词匹配逻辑
        choice, confidence, reasoning = self._match_keywords_v2(state, question, options)
        
        probabilities = self._generate_probabilities(choice, options, confidence)
        
        result = {
            "choice": choice,
            "confidence": round(confidence, 2),
            "reasoning": reasoning,
            "probabilities": probabilities
        }
        
        return json.dumps(result, ensure_ascii=False)
    
    def _match_keywords_v2(self, state: str, question: str, options: List[str]) -> tuple:
        """v2.0增强的关键词匹配逻辑"""
        
        # 紧急程度判断 - 改进阈值
        if "紧急程度" in question or "urgency" in question.lower():
            critical_keywords = ["崩溃", "紧急", "尽快", "马上", "立即", "严重", "故障", "95%"]
            high_keywords = ["高", "慢", "超时", "错误"]
            
            for kw in critical_keywords:
                if kw in state:
                    for opt in reversed(options):
                        if "紧急" in opt or "高" in opt:
                            return opt, 0.95, f"检测到关键指标 '{kw}'，属于紧急情况"
            
            for kw in high_keywords:
                if kw in state:
                    for opt in reversed(options):
                        if "高" in opt:
                            return opt, 0.85, f"检测到 '{kw}' 相关描述"
            
            return options[0], 0.5, "无明显紧急信号"
        
        # 问题类型判断 - 改进边界
        if "问题类型" in question or "type" in question.lower():
            # bug报告特征
            bug_signals = ["错误", "崩溃", "异常", "500", "404", "报错", "失败", "bug"]
            for sig in bug_signals:
                if sig in state:
                    for opt in options:
                        if "bug" in opt.lower() or "bug报告" in opt:
                            return opt, 0.90, f"检测到bug信号: '{sig}'"
            
            # 功能咨询特征
            consult_signals = ["支持", "接口", "是否", "能否", "有没有", "查询"]
            for sig in consult_signals:
                if sig in state:
                    for opt in options:
                        if "咨询" in opt:
                            return opt, 0.88, f"检测到咨询特征: '{sig}'"
            
            return options[0], 0.6, "无法明确分类"
        
        # 风险等级判断 - 改进逻辑
        if "风险" in question or "risk" in question.lower():
            critical_signals = ["核心", "生产", "数据库", "资金", "用户数据", "签名变更"]
            for sig in critical_signals:
                if sig in state:
                    for opt in options:
                        if "高" in opt or "极高" in opt:
                            return opt, 0.88, f"检测到高风险信号: '{sig}'"
            
            return options[0], 0.5, "无明显风险信号"
        
        # Skill路由判断
        if "skill" in question.lower() or "路由" in question:
            skill_mapping = {
                "ppt": "pptx",
                "演示文稿": "pptx",
                "word": "docx",
                "文档": "docx",
                "文章": "content-creation",
                "生成": "content-creation",
                "数据": "data-analysis",
                "分析": "data-analysis"
            }
            for key, value in skill_mapping.items():
                if key in state.lower():
                    for opt in options:
                        if value in opt.lower():
                            return opt, 0.90, f"匹配到skill: {value}"
            
            return options[0], 0.6, "无法确定skill路由"
        
        # 默认返回第一个选项
        return options[0], 0.75, "使用默认策略"
    
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
    MiniJEV v2.0 - 思考链推理决策引擎
    
    特点：
    1. 思考链推理框架（Inspired by Meta Muse Spark）
    2. 自验证机制
    3. 领域知识库
    4. 自适应few-shot
    """
    
    def __init__(
        self,
        config: Optional[JevConfig] = None,
        llm: Optional[LLMInterface] = None
    ):
        self.config = config or JevConfig()
        self.llm = llm or MockLLM(self.config)
        self._decision_history = []
        self._domain_knowledge = self._load_domain_knowledge()
    
    def _load_domain_knowledge(self) -> Dict:
        """加载领域知识库"""
        return {
            "bug_report": {
                "keywords": ["错误", "崩溃", "异常", "500", "404", "报错", "bug", "失败"],
                "confidence_boost": 0.90
            },
            "feature_consult": {
                "keywords": ["支持", "接口", "是否", "能否", "查询", "有没有"],
                "confidence_boost": 0.88
            },
            "tech_support": {
                "keywords": ["安装", "配置", "使用", "不会", "如何", "教程"],
                "confidence_boost": 0.85
            },
            "feature_request": {
                "keywords": ["想要", "建议", "功能", "改进", "希望"],
                "confidence_boost": 0.82
            },
            "critical_risk": {
                "keywords": ["核心", "生产", "数据库", "资金", "签名", "影响范围"],
                "confidence_boost": 0.95
            },
            "urgent": {
                "keywords": ["崩溃", "紧急", "95%", "马上", "立即", "雪崩"],
                "confidence_boost": 0.95
            }
        }
    
    def decide(
        self,
        state: str,
        question: str,
        options: List[str],
        decision_type: Union[str, DecisionType] = DecisionType.CHOICE,
        force_correct: bool = False  # 调试用：强制正确答案
    ) -> DecisionResult:
        """
        做出决策（带思考链）
        """
        start_time = time.time()
        
        if not state or not state.strip():
            raise ValueError("state不能为空")
        if not options or len(options) == 0:
            raise ValueError("options不能为空")
        
        # 构建思考链prompt
        prompt = self._build_chain_of_thought_prompt(state, question, options, decision_type)
        
        # 调用LLM
        raw_response = self.llm.call(prompt, self.config.model)
        
        # 解析结果
        result_dict = self._parse_chain_response(raw_response, options)
        
        # 自验证
        if self.config.enable_reasoning:
            result_dict = self._self_verify(result_dict, state, question, options)
        
        # 计算耗时
        latency_ms = (time.time() - start_time) * 1000
        
        # 创建DecisionResult
        result = DecisionResult(
            choice=result_dict.get("choice", options[0]),
            confidence=result_dict.get("confidence", 0.5),
            probabilities=result_dict.get("probabilities", {}),
            decision_type=str(decision_type) if isinstance(decision_type, DecisionType) else decision_type,
            raw_response=raw_response,
            latency_ms=latency_ms,
            reasoning=result_dict.get("reasoning", "")
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
            logger.info(f"决策完成: {result.choice} (置信度: {result.confidence:.2f}, 推理: {result.reasoning[:50]}...)")
        
        return result
    
    def _build_chain_of_thought_prompt(
        self,
        state: str,
        question: str,
        options: List[str],
        decision_type: Union[str, DecisionType]
    ) -> str:
        """构建思考链Prompt"""
        
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
            few_shot_str = "【参考示例】\n"
            for ex in self.config.few_shot_examples:
                few_shot_str += f"状态: {ex['state']}\n"
                few_shot_str += f"问题: {ex['question']}\n"
                answer = ex['answer']
                reasoning = answer.get('reasoning', '')
                few_shot_str += f"思考: {reasoning}\n"
                few_shot_str += f"答案: {json.dumps(answer, ensure_ascii=False)}\n\n"
        
        # 思考链指令
        thinking_instruction = """
【思考链要求】
请在回答前，按以下步骤思考：
1. 识别问题类型和关键信息
2. 分析每个选项的适用性
3. 排除不合适的选项
4. 验证最终选择的合理性

输出格式必须包含reasoning字段（推理过程）：
{"reasoning": "你的详细推理", "choice": "选中的选项", "confidence": 0.0-1.0, "probabilities": {"选项1": 0.x, "选项2": 0.x, ...}}
"""
        
        prompt = f"""{self.config.system_prompt}
{type_hint}
{thinking_instruction}

{few_shot_str}【当前任务】
状态: {state}
问题: {question}
可选答案:
{options_str}

请按思考链格式返回JSON:"""
        
        return prompt
    
    def _parse_chain_response(self, raw: str, options: List[str]) -> Dict[str, Any]:
        """解析思考链响应"""
        try:
            # 尝试直接解析
            result = json.loads(raw.strip())
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {e}, 原始响应: {raw[:200]}")
            # 尝试从文本中提取JSON
            match = re.search(r'\{[^}]+reasoning[^}]+\}', raw, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group())
                except json.JSONDecodeError:
                    result = None
            else:
                result = None
            
            if result is None:
                # fallback
                result = {
                    "choice": options[0],
                    "confidence": 0.5,
                    "reasoning": "解析失败，使用默认值",
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
        
        # 确保reasoning存在
        if "reasoning" not in result:
            result["reasoning"] = ""
        
        # 确保probabilities存在且和为1
        if "probabilities" not in result or not result["probabilities"]:
            result["probabilities"] = {opt: 1.0/len(options) for opt in options}
        else:
            probs = result["probabilities"]
            total = sum(probs.values())
            if total > 0 and abs(total - 1.0) > 0.01:
                result["probabilities"] = {k: round(v/total, 2) for k, v in probs.items()}
        
        return result
    
    def _self_verify(self, result: Dict, state: str, question: str, options: List[str]) -> Dict:
        """自验证机制"""
        choice = result.get("choice", options[0])
        reasoning = result.get("reasoning", "")
        
        # 检查关键词一致性
        domain_checks = {
            "bug报告": ["错误", "崩溃", "异常", "500", "404", "bug"],
            "功能咨询": ["支持", "接口", "是否", "能否"],
            "紧急": ["崩溃", "紧急", "95%", "马上", "立即"],
            "高": ["核心", "生产", "数据库", "资金"]
        }
        
        for expected_choice, keywords in domain_checks.items():
            if choice == expected_choice:
                matches = [kw for kw in keywords if kw in state]
                if not matches:
                    result["confidence"] = min(result["confidence"] * 0.8, 1.0)
                    result["reasoning"] += f"\n[警告] 选择'{expected_choice}'但状态中未检测到预期关键词"
        
        return result
    
    def batch_decide(
        self,
        requests: List[Dict],
        decision_type: Union[str, DecisionType] = DecisionType.CHOICE
    ) -> List[DecisionResult]:
        """批量决策"""
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
        description="MiniJEV v2.0 - 思考链推理决策引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基础决策
  python3 mini_jev_v2.py decide --state "用户反馈系统返回错误500" --question "问题类型" --options "功能咨询,技术支持,bug报告,功能需求"
  
  # 批量决策
  python3 mini_jev_v2.py batch --input requests.json
  
  # 查看版本
  python3 mini_jev_v2.py --version
        """
    )
    
    parser.add_argument("--version", action="version", version="MiniJEV 2.0.0")
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # decide命令
    decide_parser = subparsers.add_parser("decide", help="单次决策")
    decide_parser.add_argument("--state", required=True, help="输入状态")
    decide_parser.add_argument("--question", required=True, help="问题描述")
    decide_parser.add_argument("--options", required=True, help="可选答案（逗号分隔）")
    decide_parser.add_argument("--type", choices=["choice", "score", "noul"], default="choice", help="决策类型")
    decide_parser.add_argument("--json", action="store_true", help="以JSON格式输出")
    decide_parser.add_argument("--reasoning", action="store_true", help="显示推理过程")
    
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
        print(f"  耗时: {result.latency_ms:.0f}ms")
        if args.reasoning and result.reasoning:
            print(f"  推理: {result.reasoning[:100]}...")
        print(f"\n概率分布:")
        for opt, prob in result.probabilities.items():
            bar = "█" * int(prob * 20)
            print(f"    {opt:20s} {prob:.2%} {bar}")
        print()


def _handle_batch(args):
    """处理batch命令"""
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            requests = json.load(f)
    except Exception as e:
        print(f"错误: 无法读取文件 - {e}", file=sys.stderr)
        sys.exit(1)
    
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
