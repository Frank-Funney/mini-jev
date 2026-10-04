#!/usr/bin/env python3
"""
MiniJEV 国际推广工具
支持平台：Dev.to, Hashnode, Twitter/X
"""

import os
import sys
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional

# 配置
PLATFORMS = {
    "devto": {
        "name": "DEV Community",
        "url": "https://dev.to",
        "api_base": "https://dev.to/api/articles",
        "required_keys": ["DEVTO_API_KEY"]
    },
    "hashnode": {
        "name": "Hashnode",
        "url": "https://hashnode.com",
        "api_base": "https://api.hashnode.com",
        "required_keys": ["HASHNODE_API_KEY", "HASHNODE_PUBLICATION_ID"]
    },
    "twitter": {
        "name": "Twitter/X",
        "url": "https://twitter.com",
        "api_base": "https://api.twitter.com/2/tweets",
        "required_keys": ["TWITTER_BEARER_TOKEN"]
    }
}

class MiniJEVPromoter:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.articles = {
            "technical": self._load_article("article_csdn_v2.md"),
            "intro": self._load_article("article_zhihu_v2.md")
        }
    
    def _load_article(self, filename: str) -> str:
        """加载文章"""
        article_path = self.project_root / filename
        if article_path.exists():
            return article_path.read_text(encoding="utf-8")
        return ""
    
    def check_environment(self) -> Dict[str, bool]:
        """检查环境变量"""
        status = {}
        for platform, config in PLATFORMS.items():
            status[platform] = all(
                os.getenv(key) for key in config["required_keys"]
            )
        return status
    
    def format_for_devto(self, content: str) -> Dict:
        """格式化为Dev.to文章"""
        lines = content.split("\n")
        title = lines[0].replace("# ", "").strip()
        body = "\n".join(lines[1:]).strip()
        
        return {
            "title": title,
            "body_markdown": body,
            "published": True,
            "tags": ["javascript", "python", "ai", "machinelearning", "opensource"],
            "canonical_url": "https://github.com/Frank-Funney/mini-jev"
        }
    
    def publish_to_devto(self, article_type: str = "technical") -> Dict:
        """发布到Dev.to"""
        if not os.getenv("DEVTO_API_KEY"):
            return {"success": False, "error": "DEVTO_API_KEY not set"}
        
        content = self.articles.get(article_type, self.articles["technical"])
        payload = self.format_for_devto(content)
        
        try:
            response = requests.post(
                PLATFORMS["devto"]["api_base"],
                json={"article": payload},
                headers={"api-key": os.getenv("DEVTO_API_KEY")}
            )
            return {
                "success": response.status_code == 201,
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 201 else None,
                "error": response.text if response.status_code != 201 else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def generate_twitter_threads(self) -> List[str]:
        """生成Twitter推文系列"""
        threads = [
            "🚀 Just released MiniJEV - a zero-dependency decision engine for AI Agents!\n\nInspired by TypeSafe Jev, but built for old machines and small budgets.\n\n✅ 26KB code\n✅ Zero dependencies  \n✅ 87.5% accuracy\n\nCheck it out: https://github.com/Frank-Funney/mini-jev",
            "\nThread: Why I built MiniJEV 🧵\n\n1/ TypeSafe Jev API costs $42/M tokens\n2/ Von needs 395MB + PyTorch\n3/ Both require good internet\n\nI wanted something simpler...",
            "\nMiniJEV solution:\n\n• Use prompt engineering instead of massive models\n• Leverage existing LLM APIs you already have\n• Keep it under 1MB\n\nResult: 87.5% accuracy with zero extra dependencies!",
            "\nPerfect for:\n• AI Agent skill routing\n• Customer support classification\n• Log anomaly detection\n• Code review risk assessment\n\nAll with your existing LLM backend.\n\n#opensource #ai #python"
        ]
        return threads
    
    def run_full_promotion(self) -> Dict:
        """运行完整推广流程"""
        results = {
            "platforms_checked": self.check_environment(),
            "devto": None,
            "twitter_drafts": self.generate_twitter_threads()
        }
        
        # 尝试发布到DEV.to
        if results["platforms_checked"].get("devto"):
            print("📝 Publishing to DEV.to...")
            results["devto"] = self.publish_to_devto()
        
        return results


def main():
    """主入口"""
    promoter = MiniJEVPromoter()
    
    print("=" * 60)
    print("MiniJEV International Promotion Tool")
    print("=" * 60)
    print()
    
    # 检查环境
    print("🔍 Checking platform availability...")
    status = promoter.check_environment()
    for platform, available in status.items():
        icon = "✅" if available else "❌"
        print(f"  {icon} {platform}: {'Available' if available else 'Need API key'}")
    print()
    
    # 生成Twitter草稿
    print("🐦 Twitter thread drafts:")
    for i, tweet in enumerate(promoter.generate_twitter_threads(), 1):
        print(f"\n--- Tweet {i} ---")
        print(tweet[:280] + "..." if len(tweet) > 280 else tweet)
    print()
    
    # 运行完整推广
    print("=" * 60)
    print("Running full promotion...")
    results = promoter.run_full_promotion()
    
    print("\n📊 Results:")
    if results["devto"]:
        print(f"  DEV.to: {results['devto']['success']}")
        if results["devto"]["success"]:
            print(f"    URL: {results['devto']['data'].get('path', 'N/A')}")
    
    print("\n💡 Next steps:")
    print("  1. Set required API keys in .env file")
    print("  2. Run this script again to publish")
    print("  3. Share Twitter threads manually")
    print()


if __name__ == "__main__":
    main()
