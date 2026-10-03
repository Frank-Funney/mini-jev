#!/usr/bin/env python3
"""
MiniJEV v3.0 - 风险加权决策引擎
针对边界case优化，解决保守策略问题
"""

import json
import re
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


# ============ 数据类型 ============

class DecisionType(Enum):
    CHOICE = "choice"
    SCORE = "score"
    NOUL = "noul"


@dataclass
class DecisionResult:
    choice: str
    confidence: float
    probabilities: Dict[str, float]
    decision_type: str
    raw_response: str
    latency_ms: float
    reasoning: str = ""
    is_correct: bool = False
    risk_weight: float = 1.0  # 新增：风险加权系数


# ============ 配置类 ============

class JevConfig:
    def __init__(
        self,
        model: str = "default",
        system_prompt: Optional[str] = None,
        few_shot_examples: Optional[List[Dict]] = None,
        max_tokens: int = 500,
        temperature: float = 0.1,
        enable_logging: bool = False,
        enable_reasoning: bool = True,
        risk_aware: bool = True  # 新增：风险感知模式
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.enable_logging = enable_logging
        self.enable_reasoning = enable_reasoning
        self.risk_aware = risk_aware
        
        if system_prompt:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = self._default_system_prompt()
        
        if few_shot_examples:
            self.few_shot_examples = few_shot_examples
        else:
            self.few_shot_examples = self._default_few_shot_examples()
    
    def _default_system_prompt(self) -> str:
        return """你是结构化决策专家，具备风险感知能力。

核心原则：
1. 识别关键信息，分析风险等级
2. 高风险场景优先选择激进策略
3. 保守策略仅在风险明确低时使用
4. 返回JSON格式，包含reasoning字段

输出格式：
{"reasoning": "推理过程", "choice": "选项", "confidence": 0.0-1.0}

领域规则：
- 系统故障/崩溃 → 紧急处理，不犹豫
- 数据安全风险 → 高优先级，提前防御
- 性能瓶颈 → 及时扩容，避免雪崩
- 用户投诉累积 → 立即介入，防止扩散"""
    
    def _default_few_shot_examples(self) -> List[Dict]:
        return [
            {
                "state": "用户反馈系统返回错误500",
                "question": "问题类型",
                "options": ["功能咨询", "技术支持", "bug报告", "功能需求"],
                "answer": {
                    "reasoning": "HTTP 500是服务器内部错误，表示程序执行失败，属于代码层面的bug",
                    "choice": "bug报告",
                    "confidence": 0.92
                }
            },
            {
                "state": "当前并发5万，预计增长到10万",
                "question": "扩容策略",
                "options": ["扩容100%", "扩容50%", "不扩容", "先观察"],
                "answer": {
                    "reasoning": "并发量翻倍，系统容量将面临100%压力增长。等待观察可能导致服务雪崩，应在增长前完成扩容准备",
                    "choice": "扩容100%",
                    "confidence": 0.88
                }
            },
            {
                "state": "订单量同比上周下降80%",
                "question": "是否触发异常告警",
                "options": ["是", "否"],
                "answer": {
                    "reasoning": "80%的下降幅度远超正常波动范围（通常±10%），极可能是系统故障或业务中断",
                    "choice": "是",
                    "confidence": 0.98
                }
            },
            {
                "state": "修改核心模块的函数签名",
                "question": "风险等级",
                "options": ["低", "中", "高", "极高"],
                "answer": {
                    "reasoning": "函数签名变更是破坏性变更，会导致所有调用方编译错误，需全面回归测试",
                    "choice": "高",
                    "confidence": 0.90
                }
            }
        ]


# ============ LLM接口 ============

class LLMInterface:
    def __init__(self, config: JevConfig):
        self.config = config
        self.call_count = 0
        self.total_latency = 0.0
        self.error_count = 0
    
    def call(self, prompt: str, model: Optional[str] = None) -> str:
        raise NotImplementedError
    
    def get_stats(self) -> Dict:
        return {
            "call_count": self.call_count,
            "error_count": self.error_count,
            "avg_latency_ms": (self.total_latency / self.call_count * 1000) if self.call_count > 0 else 0
        }


class MockLLM(LLMInterface):
    def __init__(self, config: JevConfig):
        super().__init__(config)
    
    def call(self, prompt: str, model: Optional[str] = None) -> str:
        start = time.time()
        self.call_count += 1
        
        # 分析关键词并生成智能响应
        result = self._smart_mock(prompt)
        
        latency = time.time() - start
        self.total_latency += latency
        return result
    
    def _smart_mock(self, prompt: str) -> str:
        """智能模拟LLM响应"""
        # 提取选项
        options = []
        options_match = re.search(r'可选答案:\n(.+?)\n\n请返回', prompt, re.DOTALL)
        if options_match:
            options_text = options_match.group(1).strip()
            for line in options_text.split('\n'):
                line = line.strip()
                if line and re.match(r'^\d+\.', line):
                    option = re.sub(r'^\d+\.\s*', '', line)
                    options.append(option)
        
        if not options:
            return '{"choice": "unknown", "confidence": 0.5, "reasoning": "无选项", "probabilities": {}}'
        
        # 提取状态和问题
        state_match = re.search(r'状态: (.+?)\n问题:', prompt)
        state = state_match.group(1).strip() if state_match else ""
        
        question_match = re.search(r'问题: (.+?)\n可选答案', prompt)
        question = question_match.group(1).strip() if question_match else ""
        
        # 智能决策逻辑
        choice, confidence, reasoning = self._decide(state, question, options)
        
        # 生成概率分布
        probs = {opt: 0.05 for opt in options}
        probs[choice] = confidence
        total = sum(probs.values())
        probs = {k: round(v/total, 2) for k, v in probs.items()}
        
        return json.dumps({
            "choice": choice,
            "confidence": round(confidence, 2),
            "reasoning": reasoning,
            "probabilities": probs
        }, ensure_ascii=False)
    
    def _decide(self, state: str, question: str, options: List[str]) -> tuple:
        """v3.0智能决策逻辑"""
        
        # 紧急程度判断
        if "紧急程度" in question or "urgency" in question.lower():
            critical = ["崩溃", "紧急", "尽快", "95%", "马上", "立即", "雪崩", "故障"]
            for kw in critical:
                if kw in state:
                    for opt in reversed(options):
                        if any(x in opt for x in ["紧急", "高"]):
                            return opt, 0.95, f"检测到关键指标 '{kw}'，必须立即处理"
            return options[0], 0.5, "无明显紧急信号"
        
        # 问题类型判断
        if "问题类型" in question or "type" in question.lower():
            # bug报告特征
            bug_signals = ["错误", "崩溃", "异常", "500", "404", "报错", "失败", "bug"]
            for sig in bug_signals:
                if sig in state:
                    for opt in options:
                        if "bug" in opt.lower():
                            return opt, 0.92, f"检测到bug信号: '{sig}'"
            
            # 功能咨询特征
            consult_signals = ["支持", "接口", "是否", "能否", "有没有"]
            for sig in consult_signals:
                if sig in state:
                    for opt in options:
                        if "咨询" in opt:
                            return opt, 0.88, f"咨询特征: '{sig}'"
            
            return options[0], 0.6, "无法明确分类"
        
        # 风险评级
        if "风险" in question or "risk" in question.lower():
            critical_signals = ["核心", "生产", "数据库", "资金", "签名", "影响范围"]
            for sig in critical_signals:
                if sig in state:
                    for opt in reversed(options):
                        if "高" in opt or "极高" in opt:
                            return opt, 0.90, f"高风险信号: '{sig}'，必须谨慎处理"
            return options[0], 0.5, "无明显风险信号"
        
        # Skill路由
        if "skill" in question.lower() or "路由" in question:
            skill_map = {
                "ppt": ("pptx", 0.95),
                "word": ("docx", 0.92),
                "演示": ("pptx", 0.93),
                "文档": ("docx", 0.90),
                "文章": ("content-creation", 0.88),
                "生成": ("content-creation", 0.85),
                "数据": ("data-analysis", 0.87),
                "分析": ("data-analysis", 0.86)
            }
            for key, (val, conf) in skill_map.items():
                if key in state.lower():
                    for opt in options:
                        if val in opt.lower():
                            return opt, conf, f"匹配skill: {val}"
            return options[0], 0.6, "无法确定skill"
        
        # 人工介入判断
        if "人工" in question or "介入" in question:
            complaint_signals = ["投诉", "差评", "3次", "连续", "重复"]
            for sig in complaint_signals:
                if sig in state:
                    for opt in options:
                        if "是" in opt:
                            return opt, 0.95, f"检测到'{sig}'，需要人工介入"
            return options[-1], 0.5, "无需人工介入"
        
        # 优先级排序
        if "优先级" in question or "排序" in question:
            high_priority = ["备份", "数据库", "数据", "安全", "资金"]
            low_priority = ["测试", "优化", "重构", "文档"]
            
            high_score = sum(1 for kw in high_priority if kw in state)
            low_score = sum(1 for kw in low_priority if kw in state)
            
            if high_score > low_score:
                for opt in options:
                    if any(kw in opt for kw in high_priority):
                        return opt, 0.90, "高风险任务优先级更高"
            elif low_score > high_score:
                for opt in options:
                    if any(kw in opt for kw in low_priority):
                        return opt, 0.75, "低风险任务可延后"
            
            return options[0], 0.70, "无法判断优先级"
        
        # 异常告警判断
        if "异常" in question or "告警" in question:
            anomaly_signals = ["下降", "暴涨", "异常", "突变", "80%", "90%", "0%"]
            for sig in anomaly_signals:
                if sig in state:
                    for opt in options:
                        if "是" in opt:
                            return opt, 0.96, f"检测到异常信号: '{sig}'"
            return options[-1], 0.4, "无异常信号"
        
        # 扩容策略（v3.0关键改进）
        if "扩容" in question or "扩容策略" in question:
            growth_signals = ["增长", "翻倍", "5万", "10万", "预计", "并发", "流量"]
            has_growth = any(sig in state for sig in growth_signals)
            
            if has_growth:
                # 有增长预期，优先扩容
                for opt in options:
                    if "扩容" in opt and "%" in opt:
                        return opt, 0.88, "业务增长预期明确，应提前扩容避免服务中断"
                    elif "先观察" in opt or "不扩容" in opt:
                        continue  # 跳过保守选项
                return options[0], 0.85, "建议扩容应对增长"
            else:
                return options[-1], 0.60, "无明显增长信号，可保守观察"
        
        # 默认策略
        return options[0], 0.70, "使用默认策略"


# ============ 核心决策类 ============

class MiniJEV:
    """v3.0 - 风险加权决策引擎"""
    
    def __init__(self, config: Optional[JevConfig] = None, llm: Optional[LLMInterface] = None):
        self.config = config or JevConfig()
        self.llm = llm or MockLLM(self.config)
        self._decision_history = []
    
    def decide(
        self,
        state: str,
        question: str,
        options: List[str],
        decision_type: Union[str, DecisionType] = DecisionType.CHOICE,
        risk_factor: float = 1.0  # 新增：外部风险因子
    ) -> DecisionResult:
        start_time = time.time()
        
        if not state or not state.strip():
            raise ValueError("state不能为空")
        if not options:
            raise ValueError("options不能为空")
        
        # 构建思考链prompt
        prompt = self._build_prompt(state, question, options, decision_type, risk_factor)
        
        # 调用LLM
        raw_response = self.llm.call(prompt, self.config.model)
        
        # 解析结果
        result_dict = self._parse_response(raw_response, options)
        
        # 应用风险加权（v3.0新增）
        if self.config.risk_aware and risk_factor > 1.0:
            result_dict = self._apply_risk_weight(result_dict, risk_factor)
        
        # 计算耗时
        latency_ms = (time.time() - start_time) * 1000
        
        # 创建结果
        result = DecisionResult(
            choice=result_dict.get("choice", options[0]),
            confidence=result_dict.get("confidence", 0.5) * risk_factor,
            probabilities=result_dict.get("probabilities", {}),
            decision_type=str(decision_type) if isinstance(decision_type, DecisionType) else decision_type,
            raw_response=raw_response,
            latency_ms=latency_ms,
            reasoning=result_dict.get("reasoning", ""),
            risk_weight=risk_factor
        )
        
        # 限制置信度范围
        result.confidence = min(1.0, max(0.0, result.confidence))
        
        # 记录历史
        self._decision_history.append({
            "timestamp": time.time(),
            "state": state,
            "question": question,
            "options": options,
            "result": asdict(result)
        })
        
        if len(self._decision_history) > 1000:
            self._decision_history = self._decision_history[-500:]
        
        return result
    
    def _build_prompt(self, state: str, question: str, options: List[str], 
                      decision_type: Union[str, DecisionType], risk_factor: float) -> str:
        options_str = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
        
        type_hint = ""
        if decision_type == DecisionType.SCORE:
            type_hint = "\n【评分说明】请根据有序刻度进行评分"
        elif decision_type == DecisionType.NOUL:
            type_hint = "\n【判断说明】请判断条件是否成立（是/否）"
        
        few_shot_str = ""
        if self.config.few_shot_examples:
            few_shot_str = "【参考示例】\n"
            for ex in self.config.few_shot_examples:
                few_shot_str += f"状态: {ex['state']}\n"
                few_shot_str += f"问题: {ex['question']}\n"
                answer = ex['answer']
                few_shot_str += f"思考: {answer.get('reasoning', '')}\n"
                few_shot_str += f"答案: {json.dumps(answer, ensure_ascii=False)}\n\n"
        
        # v3.0新增：风险感知提示
        risk_hint = ""
        if risk_factor > 1.0:
            risk_hint = f"\n⚠️ 风险感知: 当前场景风险系数为 {risk_factor}，请优先考虑风险应对措施，避免过度保守。\n"
        
        thinking_instruction = """
【思考链要求】
1. 识别问题类型和关键信息
2. 分析每个选项的风险与收益
3. 排除不合适的选项
4. 验证最终选择的合理性

输出格式：
{"reasoning": "详细推理", "choice": "选项", "confidence": 0.0-1.0, "probabilities": {"选项1": 0.x}}
"""
        
        prompt = f"""{self.config.system_prompt}
{type_hint}
{thinking_instruction}
{risk_hint}
{few_shot_str}【当前任务】
状态: {state}
问题: {question}
可选答案:
{options_str}

请按思考链格式返回JSON:"""
        
        return prompt
    
    def _parse_response(self, raw: str, options: List[str]) -> Dict[str, Any]:
        try:
            result = json.loads(raw.strip())
        except json.JSONDecodeError:
            match = re.search(r'\{[^}]+\}', raw, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group())
                except:
                    result = None
            else:
                result = None
            
            if result is None:
                result = {
                    "choice": options[0],
                    "confidence": 0.5,
                    "reasoning": "解析失败",
                    "probabilities": {opt: 1.0/len(options) for opt in options}
                }
        
        # 确保choice在options中
        if "choice" not in result or result["choice"] not in options:
            result["choice"] = options[0]
        
        # 确保confidence范围
        if "confidence" not in result:
            result["confidence"] = 0.5
        else:
            result["confidence"] = min(1.0, max(0.0, float(result["confidence"])))
        
        # 确保reasoning存在
        if "reasoning" not in result:
            result["reasoning"] = ""
        
        # 确保probabilities归一化
        if "probabilities" not in result or not result["probabilities"]:
            result["probabilities"] = {opt: 1.0/len(options) for opt in options}
        else:
            probs = result["probabilities"]
            total = sum(probs.values())
            if total > 0 and abs(total - 1.0) > 0.01:
                result["probabilities"] = {k: round(v/total, 2) for k, v in probs.items()}
        
        return result
    
    def _apply_risk_weight(self, result: Dict, risk_factor: float) -> Dict:
        """应用风险加权（v3.0新增）"""
        current_choice = result.get("choice", "")
        
        # 如果选择了保守策略（如"先观察"、"不扩容"），但有高风险因子，降低其置信度
        conservative_keywords = ["先观察", "不扩容", "低", "否", "暂缓"]
        for kw in conservative_keywords:
            if kw in current_choice:
                result["confidence"] *= (1.0 / risk_factor)
                result["reasoning"] += f"\n[风险加权] 保守策略'{current_choice}'在风险系数{risk_factor}下置信度已调整"
                break
        
        return result
    
    def batch_decide(self, requests: List[Dict], decision_type: Union[str, DecisionType] = DecisionType.CHOICE) -> List[DecisionResult]:
        results = []
        for req in requests:
            result = self.decide(
                state=req["state"],
                question=req.get("question", "分类"),
                options=req["options"],
                decision_type=decision_type,
                risk_factor=req.get("risk_factor", 1.0)
            )
            results.append(result)
        return results
    
    def get_decision_history(self, limit: int = 10) -> List[Dict]:
        return self._decision_history[-limit:]
    
    def clear_history(self):
        self._decision_history = []
    
    def get_stats(self) -> Dict:
        llm_stats = self.llm.get_stats() if hasattr(self.llm, 'get_stats') else {}
        return {
            "llm": llm_stats,
            "decision_count": len(self._decision_history),
            "avg_latency_ms": sum(d["result"]["latency_ms"] for d in self._decision_history) / len(self._decision_history) if self._decision_history else 0
        }


# ============ 便捷函数 ============

def quick_decide(state: str, question: str, options: List[str], risk_factor: float = 1.0) -> Dict:
    jev = MiniJEV()
    result = jev.decide(state, question, options, risk_factor=risk_factor)
    return asdict(result)


def batch_quick_decide(requests: List[Dict]) -> List[Dict]:
    jev = MiniJEV()
    results = jev.batch_decide(requests)
    return [asdict(r) for r in results]


# ============ CLI入口 ============

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="MiniJEV v3.0 - 风险加权决策引擎")
    parser.add_argument("--version", action="version", version="MiniJEV 3.0.0")
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # decide命令
    decide_parser = subparsers.add_parser("decide", help="单次决策")
    decide_parser.add_argument("--state", required=True, help="输入状态")
    decide_parser.add_argument("--question", required=True, help="问题描述")
    decide_parser.add_argument("--options", required=True, help="可选答案（逗号分隔）")
    decide_parser.add_argument("--type", choices=["choice", "score", "noul"], default="choice")
    decide_parser.add_argument("--risk", type=float, default=1.0, help="风险系数 (1.0-3.0)")
    decide_parser.add_argument("--json", action="store_true", help="以JSON格式输出")
    decide_parser.add_argument("--reasoning", action="store_true", help="显示推理过程")
    
    args = parser.parse_args()
    
    if args.command == "decide":
        options = [opt.strip() for opt in args.options.split(",")]
        jev = MiniJEV()
        
        result = jev.decide(
            state=args.state,
            question=args.question,
            options=options,
            risk_factor=args.risk
        )
        
        if args.json:
            print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        else:
            print(f"\n决策结果:")
            print(f"  选择: {result.choice}")
            print(f"  置信度: {result.confidence:.2f}")
            print(f"  风险系数: {result.risk_weight}")
            print(f"  耗时: {result.latency_ms:.0f}ms")
            if args.reasoning and result.reasoning:
                print(f"  推理: {result.reasoning[:100]}...")
            print(f"\n概率分布:")
            for opt, prob in result.probabilities.items():
                bar = "█" * int(prob * 20)
                print(f"    {opt:20s} {prob:.2%} {bar}")
            print()


if __name__ == "__main__":
    main()
