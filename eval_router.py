import time
from typing import List, Dict, Any
from graph import route_query  # Imports directly from your graph.py

# 50-Query Benchmark Dataset tailored for Infrastructure, SRE & Network Engineering
EVAL_DATASET: List[Dict[str, Any]] = [
    # ------------------------------------------------------------------
    # 1. AWS, VPC, Transit Gateway & Cloud Networking (Expected: local_db)
    # ------------------------------------------------------------------
    {"query": "What is the maximum MTU size for AWS Transit Gateway VPC attachments?", "expected": "local_db", "cat": "AWS Networking"},
    {"query": "How do I configure ECMP over multiple AWS Direct Connect virtual interfaces?", "expected": "local_db", "cat": "AWS Networking"},
    {"query": "How does AWS CloudWAN handle inter-region route propagation?", "expected": "local_db", "cat": "AWS Networking"},
    {"query": "What are the limitations of AWS Network Firewall stateful rules?", "expected": "local_db", "cat": "AWS Networking"},
    {"query": "Explain how overlay networking works in AWS VPC CNI for Kubernetes.", "expected": "local_db", "cat": "AWS Networking"},
    {"query": "Can an AWS Transit Gateway route between overlapping CIDR blocks?", "expected": "local_db", "cat": "AWS Networking"},

    # ------------------------------------------------------------------
    # 2. Enterprise Infrastructure, Nutanix, VMware & Storage (Expected: local_db)
    # ------------------------------------------------------------------
    {"query": "How does Nutanix AOS handle data deduplication on NVMe tiers?", "expected": "local_db", "cat": "Enterprise Systems"},
    {"query": "What is the difference between Nutanix AHV and VMware vSphere vMotion mechanisms?", "expected": "local_db", "cat": "Enterprise Systems"},
    {"query": "How do I configure affinity and anti-affinity rules in VMware DRS?", "expected": "local_db", "cat": "Enterprise Systems"},
    {"query": "Explain snapshot crash-consistency in Nutanix storage architecture.", "expected": "local_db", "cat": "Enterprise Systems"},
    {"query": "What are the latency penalties of using SFP+ vs RJ45 transceivers in high-density racks?", "expected": "local_db", "cat": "Hardware & Storage"},
    {"query": "How does RoCEv2 PFC (Priority Flow Control) prevent packet drop in lossless Ethernet?", "expected": "local_db", "cat": "Hardware & Storage"},

    # ------------------------------------------------------------------
    # 3. High-Performance Networking & Switching (Expected: local_db)
    # ------------------------------------------------------------------
    {"query": "How do I configure Arista 7060DX5 switches for VXLAN routing?", "expected": "local_db", "cat": "Switching/Routing"},
    {"query": "Explain BGP EVPN multi-homing active-active configuration.", "expected": "local_db", "cat": "Switching/Routing"},
    {"query": "What is the buffer size allocation strategy on Broadcom Tomahawk 4 chips?", "expected": "local_db", "cat": "Switching/Routing"},
    {"query": "How does LACP dynamic trunking negotiate link failure in top-of-rack switches?", "expected": "local_db", "cat": "Switching/Routing"},
    {"query": "What are the performance characteristics of Arista 7132LB low-latency switches?", "expected": "local_db", "cat": "Switching/Routing"},

    # ------------------------------------------------------------------
    # 4. Azure & GCP Infrastructure (Expected: local_db)
    # ------------------------------------------------------------------
    {"query": "How does GCP Virtual Private Cloud (VPC) handle global routing across regions?", "expected": "local_db", "cat": "Multi-Cloud"},
    {"query": "What is the difference between Azure ExpressRoute Direct and Circuit peering?", "expected": "local_db", "cat": "Multi-Cloud"},
    {"query": "How do I configure Azure Virtual WAN with secure hub routing intent?", "expected": "local_db", "cat": "Multi-Cloud"},
    {"query": "Explain GCP Cloud Interconnect jumbo frame support configuration.", "expected": "local_db", "cat": "Multi-Cloud"},

    # ------------------------------------------------------------------
    # 5. Out-of-Domain: Current Events, Sports & General Internet (Expected: web_search)
    # ------------------------------------------------------------------
    {"query": "What are the latest trackside server hardware specs used in Formula 1?", "expected": "web_search", "cat": "Out-of-Domain"},
    {"query": "Who won the latest UEFA Champions League final?", "expected": "web_search", "cat": "Out-of-Domain"},
    {"query": "What is the current stock price of NVIDIA?", "expected": "web_search", "cat": "Out-of-Domain"},
    {"query": "What are the breaking news headlines in tech today?", "expected": "web_search", "cat": "Out-of-Domain"},
    {"query": "When is the next SpaceX Starship test launch scheduled?", "expected": "web_search", "cat": "Out-of-Domain"},

    # ------------------------------------------------------------------
    # 6. Out-of-Domain: General Software, Recipes & Everyday Life (Expected: web_search)
    # ------------------------------------------------------------------
    {"query": "How do I make authentic Neapolitan pizza dough at home?", "expected": "web_search", "cat": "General Knowledge"},
    {"query": "What is the weather forecast for London this weekend?", "expected": "web_search", "cat": "General Knowledge"},
    {"query": "Best recommendations for a mechanical keyboard under $100?", "expected": "web_search", "cat": "General Knowledge"},
    {"query": "What are the symptoms of a failed alternator in a car?", "expected": "web_search", "cat": "General Knowledge"},
    {"query": "Who wrote the novel Dune?", "expected": "web_search", "cat": "General Knowledge"},

    # ------------------------------------------------------------------
    # 7. Out-of-Domain: Standard Coding / Non-Infra Dev (Expected: web_search)
    # ------------------------------------------------------------------
    {"query": "How do I center a div using Tailwind CSS flexbox?", "expected": "web_search", "cat": "General Coding"},
    {"query": "What is the difference between useEffect and useLayoutEffect in React?", "expected": "web_search", "cat": "General Coding"},
    {"query": "Write a Python function to reverse a doubly linked list.", "expected": "web_search", "cat": "General Coding"},
    {"query": "How to handle CORS in a Rust Actix-web backend?", "expected": "web_search", "cat": "General Coding"},
    {"query": "How does garbage collection work in Node.js V8 engine?", "expected": "web_search", "cat": "General Coding"},

    # ------------------------------------------------------------------
    # 8. Tricky Edge Cases & Ambiguous Queries (Target Routing)
    # ------------------------------------------------------------------
    {"query": "What is BGP?", "expected": "web_search", "cat": "Edge Case"},
    {"query": "Tell me about Amazon", "expected": "web_search", "cat": "Edge Case"},
    {"query": "How to fix 502 Bad Gateway on NGINX?", "expected": "web_search", "cat": "Edge Case"},
    {"query": "What is the default IP address of a Cisco router?", "expected": "web_search", "cat": "Edge Case"},
    {"query": "How do I update Python on Ubuntu 22.04?", "expected": "web_search", "cat": "Edge Case"},
    {"query": "Explain MTU vs MSS in TCP/IP networking.", "expected": "local_db", "cat": "Edge Case"},
    {"query": "Latest features in Kubernetes 1.30 release notes", "expected": "web_search", "cat": "Edge Case"},
    {"query": "Nutanix vs VMware cost comparison 2026", "expected": "web_search", "cat": "Edge Case"},
    {"query": "AWS Direct Connect pricing breakdown", "expected": "web_search", "cat": "Edge Case"},
    {"query": "How to ping a remote port in Linux using nc or telnet?", "expected": "local_db", "cat": "Edge Case"},
    {"query": "What is the difference between Layer 4 and Layer 7 load balancing?", "expected": "local_db", "cat": "Edge Case"},
    {"query": "Who is the CEO of Nutanix?", "expected": "web_search", "cat": "Edge Case"},
    {"query": "What is RoCEv2?", "expected": "web_search", "cat": "Edge Case"},
]


def run_benchmark():
    print(f"🚀 Initializing Router Benchmark on {len(EVAL_DATASET)} Test Cases...\n")
    
    correct = 0
    total = len(EVAL_DATASET)
    latencies = []
    category_stats = {}

    print(f"{'#':<3} | {'CATEGORY':<18} | {'EXPECTED':<10} | {'ACTUAL':<10} | {'LATENCY':<8} | {'STATUS'}")
    print("-" * 80)

    for idx, test_case in enumerate(EVAL_DATASET, 1):
        query = test_case["query"]
        expected = test_case["expected"]
        cat = test_case["cat"]

        # Track category stats
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "correct": 0}
        category_stats[cat]["total"] += 1

        start_time = time.perf_counter()
        
        # Build standard LangGraph state input
        state = {
            "question": query,
            "context": "",
            "source": "",
            "answer": "",
            "history": []
        }

        try:
            # Execute the router node
            result = route_query(state) 
            actual = result.get("source", "UNKNOWN")
        except Exception as e:
            actual = f"ERROR ({type(e).__name__})"

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        latencies.append(elapsed_ms)

        is_correct = actual == expected
        if is_correct:
            correct += 1
            category_stats[cat]["correct"] += 1

        status_icon = "✅" if is_correct else "❌"
        
        # Display short query string if printing line items
        query_preview = query[:35] + "..." if len(query) > 35 else query
        print(f"{idx:<3} | {cat:<18} | {expected:<10} | {actual:<10} | {elapsed_ms:>6.1f}ms | {status_icon} {query_preview}")

    # Accuracy Metrics
    accuracy = (correct / total) * 100
    avg_latency = sum(latencies) / len(latencies)

    print("\n" + "=" * 80)
    print("📊 CATEGORY ACCURACY BREAKDOWN")
    print("=" * 80)
    for cat, stats in category_stats.items():
        cat_acc = (stats["correct"] / stats["total"]) * 100
        print(f"  • {cat:<20}: {cat_acc:>6.1f}% ({stats['correct']}/{stats['total']})")

    print("\n" + "=" * 80)
    print(f"🎯 FINAL SUMMARY METRICS:")
    print(f"  • Total Test Queries  : {total}")
    print(f"  • Overall Accuracy     : {accuracy:.2f}% ({correct}/{total} Passed)")
    print(f"  • Avg Router Latency   : {avg_latency:.1f} ms")
    print("=" * 80)


if __name__ == "__main__":
    run_benchmark()