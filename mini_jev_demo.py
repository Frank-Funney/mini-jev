#!/usr/bin/env python3
"""
MiniJEV - 超轻量级结构化决策引擎

用法:
  python mini_jev_demo.py              # 交互式模式
  python mini_jev_demo.py --quick-test # 快速测试
"""

import json
import os
import sys
import re

# ============ 配置 ============

class JevConfig:
    """JEV配置"""
    # 默认使用哪个模型（通过环境变量切换）
    DEFAULT_MODEL = os.getenv("JEV_MODEL", "glm-4.5-flash")
    
    # 结构化输出的system prompt
    SYSTEM_PROMPT = """你是一个结构化决策引擎。你的任务是对输入进行分类、评分或判断。

规则：
1. 只返回JSON格式，不要其他文字
2. choice字段必须是options中的其中一个
3. confidence是0.0到1.0之间的数字
4. 如果有probabilities字段，所有值加起来应该是1.0"""
    
    # Few-shot示例（提升准确率）
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


# ============ 核心类 ============

class MiniJEV:
    """超轻量JEV实现"""
    
    def __init__(self, config=None):
        self.config = config or JevConfig()
        self._call_llm = self._get_llm_caller()
    
    def _get_llm_caller(self):
        """获取LLM调用函数"""
        # 这里可以根据实际情况接入不同的LLM API
        # 例如：Hermes Agent的内置模型、OpenAI API、本地模型等
        def default_caller(prompt, model):
            """默认调用函数 - 需要用户自己实现"""
            raise NotImplementedError(
                "请实现LLM调用函数，或设置HERMES_API_KEY等环境变量"
            )
        return default_caller
    
    def decide(
        self,
        state,
        question,
        options,
        question_type="choice"
    ):
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
        raw_response = self._call_llm(prompt, self.config.DEFAULT_MODEL)
        
        # 解析结果
        return self._parse_response(raw_response, options)
    
    def _build_prompt(self, state, question, options, question_type):
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
    
    def _parse_response(self, raw, options):
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
    
    def batch_decide(self, requests):
        """批量决策"""
        return [self.decide(**req) for req in requests]


# ============ 使用示例 ============

def demo():
    """演示用法"""
    print("=" * 60)
    print("MiniJEV 演示")
    print("=" * 60)
    
    jev = MiniJEV()
    
    # 示例1：邮件紧急程度判断
    print("\n【示例1】邮件紧急程度判断")
    result = jev.decide(
        state="客户说系统崩溃了，已经影响业务，请尽快处理！",
        question="紧急程度",
        options=["低", "中", "高", "紧急"]
    )
    print(f"结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # 示例2：问题类型分类
    print("\n【示例2】问题类型分类")
    result = jev.decide(
        state="你们的API支持 WebSocket 吗？我想实时接收推送",
        question="问题类型",
        options=["功能咨询", "技术支持", "bug报告", "功能需求"]
    )
    print(f"结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # 示例3：Skill路由（结合Hermes场景）
    print("\n【示例3】Skill路由判断")
    result = jev.decide(
        state="帮我生成一份PPT，关于AI发展趋势的",
        question="应该加载哪个skill",
        options=["ppt-master（从零生成）", "pptx-editing（编辑现有）", "text-summary（文字总结）"]
    )
    print(f"结果: {json.dumps(result, ensure_ascii=False, indent=2)}")


def quick_test():
    """快速测试"""
    print("\n快速测试MiniJEV...")
    print("-" * 40)
    
    # 测试用例
    test_cases = [
        {
            "name": "邮件紧急程度",
            "state": "客户说系统崩溃了，请尽快处理",
            "question": "紧急程度",
            "options": ["低", "中", "高", "紧急"]
        },
        {
            "name": "问题类型",
            "state": "你们的API支持 WebSocket 吗",
            "question": "问题类型",
            "options": ["功能咨询", "技术支持", "bug报告", "功能需求"]
        },
        {
            "name": "Skill路由",
            "state": "帮我生成一份PPT",
            "question": "应该加载哪个skill",
            "options": ["ppt-master", "pptx-editing", "text-summary"]
        }
    ]
    
    jev = MiniJEV()
    
    for i, tc in enumerate(test_cases, 1):
        print(f"\n测试{i}: {tc['name']}")
        try:
            result = jev.decide(
                state=tc["state"],
                question=tc["question"],
                options=tc["options"]
            )
            print(f"  结果: {json.dumps(result, ensure_ascii=False)}")
        except Exception as e:
            print(f"  错误: {e}")
    
    print("\n" + "=" * 40)
    print("测试完成")


def main():
    """主入口"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--demo":
            demo()
        elif sys.argv[1] == "--quick-test":
            quick_test()
        else:
            print(f"未知参数: {sys.argv[1]}")
            print("用法: python mini_jev_demo.py [--demo|--quick-test]")
    else:
        print("""
MiniJEV - 超轻量级结构化决策引擎

用法:
  python mini_jev_demo.py              # 交互式模式（待实现）
  python mini_jev_demo.py --demo       # 运行演示
  python mini_jev_demo.py --quick-test # 快速测试

注意: 需要实现LLM调用函数才能正常运行
      修改 _get_llm_caller() 方法即可接入你的LLM
        """)


if __name__ == "__main__":
    main()
