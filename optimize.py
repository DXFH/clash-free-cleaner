import asyncio
import aiohttp
import yaml
import os
import re
from datetime import datetime

print(f"当前工作目录: {os.getcwd()}")
print("列出根目录文件:", os.listdir('.'))
print("列出 sub/protocols 目录:", os.listdir('sub/protocols') if os.path.exists('sub/protocols') else "目录不存在")

async def latency_test(proxy_url: str) -> float:
    try:
        async with aiohttp.ClientSession() as session:
            start = asyncio.get_event_loop().time()
            async with session.get("https://cp.cloudflare.com/generate_204", timeout=8) as resp:
                await resp.read()
                latency = round(1000 * (asyncio.get_event_loop().time() - start))
                print(f"测试 {proxy_url[:50]}... 延迟: {latency}ms")
                return latency
    except Exception as e:
        print(f"测试失败 {proxy_url[:50]}...: {str(e)}")
        return 9999

async def main():
    print("🚀 开始优化 FastNodes Hysteria2...")

    txt_path = "sub/protocols/hysteria2.txt"
    nodes_text = ""

    if os.path.exists(txt_path):
        print(f"使用本地文件: {txt_path}")
        with open(txt_path, "r", encoding="utf-8") as f:
            nodes_text = f.read()
    else:
        print(f"本地 {txt_path} 不存在，回退拉取上游")
        try:
            async with aiohttp.ClientSession() as s:
                url = "https://raw.githubusercontent.com/rtwo2/FastNodes/main/sub/protocols/hysteria2.txt"
                async with s.get(url, timeout=20) as r:
                    if r.status == 200:
                        nodes_text = await r.text()
                        print("上游拉取成功")
                    else:
                        print(f"上游拉取失败: HTTP {r.status}")
        except Exception as e:
            print(f"拉取上游异常: {str(e)}")

    if not nodes_text.strip():
        print("❌ 节点列表为空！无法继续")
        # 生成空 config 防止 commit 失败
        with open("config.yaml", "w", encoding="utf-8") as f:
            f.write("# 节点拉取失败，空配置\n")
        return

    nodes = [line.strip() for line in nodes_text.strip().split("\n") if line.strip()]
    print(f"拉取到 {len(nodes)} 个节点")

    # 只测前 50 个节省时间
    tasks = [latency_test(node) for node in nodes[:50]]
    latencies = await asyncio.gather(*tasks, return_exceptions=True)

    ranked = []
    for i, node in enumerate(nodes[:50]):
        lat = latencies[i] if not isinstance(latencies[i], Exception) else 9999
        remark_match = re.search(r"#(.+)", node)
        remark = remark_match.group(1).upper() if remark_match else ""
        multiplier = 5 if "5X" in remark else 2 if "2X" in remark else 1
        if lat < 800:
            ranked.append((node, lat, multiplier))

    ranked.sort(key=lambda x: (-x[2], x[1]))
    top_nodes = [n[0] for n in ranked[:30]]  # 减少到30个防超长
    print(f"筛选后优质节点: {len(top_nodes)} 个")

    repo = os.getenv('GITHUB_REPOSITORY', 'DXFH/clash-free-cleaner')
    config = {
        "mixed-port": 7890,
        "mode": "rule",
        "dns": {"enable": True, "ipv6": False},
        "proxy-providers": {
            "hysteria2_clean": {
                "type": "http",
                "url": f"https://raw.githubusercontent.com/{repo}/main/sub/protocols/hysteria2.txt",
                "interval": 1800,
                "health-check": {"enable": True, "url": "https://cp.cloudflare.com/generate_204", "timeout": 3000}
            }
        },
        "proxy-groups": [
            {
                "name": "🚀 免费Hysteria2下载王",
                "type": "url-test",
                "use": ["hysteria2_clean"],
                "filter": "(?i)1X|2X|5X|hysteria2|hy2",
                "url": "https://cp.cloudflare.com/generate_204",
                "interval": 180,
                "tolerance": 50
            }
        ],
        "rules": [
            "PROCESS-NAME,qBittorrent,🚀 免费Hysteria2下载王",
            "PROCESS-NAME,aria2c,🚀 免费Hysteria2下载王",
            "PROCESS-NAME,Thunder,🚀 免费Hysteria2下载王",
            "MATCH,🚀 免费Hysteria2下载王"
        ]
    }

    with open("config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False)
    print("✅ config.yaml 已生成！")
    print(f"订阅 URL: https://raw.githubusercontent.com/{repo}/main/config.yaml")

asyncio.run(main())
