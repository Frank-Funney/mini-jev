#!/usr/bin/env python3
"""MiniJEV CLI入口"""

import argparse
import json
import sys


def main():
    """CLI主入口"""
    parser = argparse.ArgumentParser(
        description="MiniJEV - 超轻量级结构化决策引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基础决策
  mini-jev decide --state "客户说系统崩溃了" --question "紧急程度" --options "低,中,高,紧急"

  # 批量决策
  mini-jev batch --input requests.json

  # 查看版本
  mini-jev --version
        """
    )

    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")

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
    from mini_jev import MiniJEV, DecisionType

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
            bar = chr(9608) * int(prob * 20)
            print(f"    {opt:20s} {prob:.2%} {bar}")
        print(f"  耗时: {result.latency_ms:.2f}ms\n")


def _handle_batch(args):
    """处理batch命令"""
    from mini_jev import MiniJEV, DecisionType

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
