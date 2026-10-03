#!/usr/bin/env python3
"""
MiniJEV Hermes集成测试
测试接入Hermes Agent的glm-4.5-flash模型
"""

import json
import sys
import os
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from mini_jev import MiniJEV, DecisionType, LLMInterface


class HermesLLM(LLMInterface):
    """Hermes Agent LLM接口"""
    
    def __init__(self, config=None, model="glm-4.5-flash"):
        super().__init__(config)
        self.model = model
        self.api_key = os.getenv("HERMES_CUSTOM_API_AGNES_AI_CN_API_KEY", "")
    
    def call(self, prompt: str, model: str = None) -> str:
        """调用Hermes LLM"""
        import subprocess
        
        self.call_count += 1
        start = time.time()
        
        # 构建hermes命令
        cmd = [
            "hermes",
            "-m", model or self.model,
            "-z", prompt,
            "--cli"
        ]
        
        try:
            # 执行hermes命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            latency = time.time() - start
            self.total_latency += latency
            
            # 提取响应
            response = result.stdout.strip()
            
            if self.config.enable_logging:
                logger.info(f"Hermes LLM调用完成，耗时{latency*1000:.2f}ms")
            
            return response
            
        except subprocess.TimeoutExpired:
            self.error_count += 1
            return '{"choice": "timeout", "confidence": 0.0}'
        except Exception as e:
            self.error_count += 1
            logger.error(f"Hermes LLM调用失败: {e}")
            return '{"choice": "error", "confidence": 0.0}'
    
    def get_stats(self):
        stats = super().get_stats()
        stats["model"] = self.model
        return stats


def test_hermes_integration():
    """测试Hermes集成"""
    print("\n" + "=" * 60)
    print("Hermes LLM集成测试")
    print("=" * 60)
    
    # 检查API Key
    api_key = os.getenv("HERMES_CUSTOM_API_AGNES_AI_CN_API_KEY", "")
    if not api_key:
        print("❌ 未找到Hermes API Key")
        print("请设置环境变量: export HERMES_CUSTOM_API_AGNES_AI_CN_API_KEY=***")
        return
    
    print(f"\nAPI Key: {api_key[:10]}...")
    
    # 创建JEV实例
    from mini_jev import JevConfig
    config = JevConfig(enable_logging=True)
    jev = MiniJEV(config=config)
    
    # 替换LLM为Hermes
    jev.llm = HermesLLM(config=config)
    
    # 测试用例
    test_cases = [
        {
            "name": "邮件紧急程度",
            "state": "客户说系统崩溃了，请尽快处理",
            "question": "紧急程度",
            "options": ["低", "中", "高", "紧急"]
        },
        {
            "name": "Skill路由",
            "state": "帮我生成一份PPT",
            "question": "应该加载哪个skill",
            "options": ["ppt-master", "pptx-editing", "text-summary"]
        },
        {
            "name": "问题分类",
            "state": "你们的API支持 WebSocket 吗",
            "question": "问题类型",
            "options": ["功能咨询", "技术支持", "bug报告", "功能需求"]
        }
    ]
    
    print("\n开始测试...")
    results = []
    
    for i, tc in enumerate(test_cases, 1):
        print(f"\n测试{i}: {tc['name']}")
        print(f"  输入: {tc['state'][:40]}...")
        
        try:
            result = jev.decide(
                state=tc["state"],
                question=tc["question"],
                options=tc["options"]
            )
            print(f"  结果: {result.choice} (置信度: {result.confidence:.2f})")
            print(f"  概率: {result.probabilities}")
            print(f"  耗时: {result.latency_ms:.2f}ms")
            results.append({"test": tc["name"], "result": result.to_dict()})
        except Exception as e:
            print(f"  错误: {e}")
            results.append({"test": tc["name"], "error": str(e)})
    
    # 打印统计
    print("\n" + "=" * 60)
    print("测试统计")
    print("=" * 60)
    stats = jev.get_stats()
    print(f"  决策次数: {stats['decision_count']}")
    print(f"  LLM调用: {stats['llm']['call_count']}")
    print(f"  LLM错误: {stats['llm']['error_count']}")
    print(f"  平均延迟: {stats['avg_latency_ms']:.2f}ms")
    
    return results


def compare_mock_vs_hermes():
    """对比Mock LLM和Hermes LLM"""
    print("\n" + "=" * 60)
    print("Mock LLM vs Hermes LLM 对比测试")
    print("=" * 60)
    
    test_state = "客户说系统崩溃了，请尽快处理"
    test_question = "紧急程度"
    test_options = ["低", "中", "高", "紧急"]
    
    # Mock LLM
    print("\n1. Mock LLM测试结果:")
    mock_jev = MiniJEV()
    mock_result = mock_jev.decide(test_state, test_question, test_options)
    print(f"   选择: {mock_result.choice}")
    print(f"   置信度: {mock_result.confidence:.2f}")
    print(f"   耗时: {mock_result.latency_ms:.2f}ms")
    
    # Hermes LLM（如果可用）
    api_key = os.getenv("HERMES_CUSTOM_API_AGNES_AI_CN_API_KEY", "")
    if api_key:
        print("\n2. Hermes LLM测试结果:")
        hermes_jev = MiniJEV()
        hermes_jev.llm = HermesLLM()
        try:
            hermes_result = hermes_jev.decide(test_state, test_question, test_options)
            print(f"   选择: {hermes_result.choice}")
            print(f"   置信度: {hermes_result.confidence:.2f}")
            print(f"   耗时: {hermes_result.latency_ms:.2f}ms")
        except Exception as e:
            print(f"   错误: {e}")
    else:
        print("\n2. Hermes LLM: 未配置API Key，跳过")
    
    print("\n" + "=" * 60)


def main():
    """主入口"""
    import time
    
    print("\n" + "=" * 60)
    print("MiniJEV Hermes集成测试")
    print("=" * 60)
    
    # 检查是否有API Key
    api_key = os.getenv("HERMES_CUSTOM_API_AGNES_AI_CN_API_KEY", "")
    
    if api_key:
        print(f"\n✅ 检测到Hermes API Key")
        test_hermes_integration()
        compare_mock_vs_hermes()
    else:
        print("\n⚠️  未检测到Hermes API Key")
        print("将使用Mock LLM进行测试")
        
        # 使用Mock LLM测试
        jev = MiniJEV()
        
        print("\nMock LLM测试结果:")
        test_cases = [
            ("邮件紧急程度", "客户说系统崩溃了", "紧急程度", ["低", "中", "高", "紧急"]),
            ("Skill路由", "帮我生成一份PPT", "应该加载哪个skill", ["ppt-master", "pptx-editing", "text-summary"]),
            ("问题分类", "你们的API支持 WebSocket 吗", "问题类型", ["功能咨询", "技术支持", "bug报告", "功能需求"]),
        ]
        
        for name, state, question, options in test_cases:
            result = jev.decide(state, question, options)
            print(f"\n{name}:")
            print(f"  选择: {result.choice}")
            print(f"  置信度: {result.confidence:.2f}")
            print(f"  耗时: {result.latency_ms:.2f}ms")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
