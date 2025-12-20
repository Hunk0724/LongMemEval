#!/usr/bin/env python3
"""
分析三種 RAG 設定在不同問題類型上的表現
生成兩個圖表：
1. 正確率（按問題類型）
2. 平均 input tokens（按問題類型）

三種設定：
1. RAG baseline (CoT): rag_stella_none
2. RAG + UserFact (CoT): rag_stella_userfact_turn
3. RAG + UserFact (CoN): rag_stella_userfact_turn
"""

import json
import sys
import os
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def load_question_types(data_file):
    """從原始數據集載入問題類型"""
    qtype_map = {}
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for entry in data:
            qid = entry['question_id']
            qtype = entry.get('question_type', 'unknown')
            qtype_map[qid] = qtype
    return qtype_map

def load_eval_results(eval_file, qtype_map):
    """載入評估結果"""
    results = defaultdict(lambda: {'correct': 0, 'total': 0, 'tokens': []})
    
    with open(eval_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                qid = entry['question_id']
                qtype = qtype_map.get(qid, 'unknown')
                
                # 正確率
                is_correct = entry.get('autoeval_label', {}).get('label', False)
                if is_correct:
                    results[qtype]['correct'] += 1
                results[qtype]['total'] += 1
                
                # Tokens
                prompt_tokens = entry.get('tokens', {}).get('prompt_token_count', 0)
                if prompt_tokens > 0:
                    results[qtype]['tokens'].append(prompt_tokens)
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse line: {e}", file=sys.stderr)
                continue
    
    # 計算平均 tokens
    for qtype in results:
        tokens_list = results[qtype]['tokens']
        if tokens_list:
            results[qtype]['avg_tokens'] = np.mean(tokens_list)
            results[qtype]['median_tokens'] = np.median(tokens_list)
        else:
            results[qtype]['avg_tokens'] = 0
            results[qtype]['median_tokens'] = 0
    
    return results

def main():
    if len(sys.argv) < 6:
        print("用法: python3 analyze_rag_by_qtype.py <data_file> <rag_baseline_eval_file> <rag_userfact_cot_eval_file> <rag_userfact_con_eval_file> <oracle_cot_eval_file> <oracle_con_eval_file>")
        sys.exit(1)
    
    data_file = sys.argv[1]
    rag_baseline_eval_file = sys.argv[2]  # RAG baseline (CoT)
    rag_userfact_cot_eval_file = sys.argv[3]  # RAG + UserFact (CoT)
    rag_userfact_con_eval_file = sys.argv[4]  # RAG + UserFact (CoN)
    oracle_cot_eval_file = sys.argv[5]  # Oracle (CoT)
    oracle_con_eval_file = sys.argv[6]  # Oracle (CoN)
    
    # 載入問題類型
    print("載入問題類型...")
    qtype_map = load_question_types(data_file)
    
    # 載入評估結果
    print("載入 RAG baseline (CoT) 評估結果...")
    rag_baseline_results = load_eval_results(rag_baseline_eval_file, qtype_map)
    
    print("載入 RAG + UserFact (CoT) 評估結果...")
    rag_userfact_cot_results = load_eval_results(rag_userfact_cot_eval_file, qtype_map)
    
    print("載入 RAG + UserFact (CoN) 評估結果...")
    rag_userfact_con_results = load_eval_results(rag_userfact_con_eval_file, qtype_map)
    
    print("載入 Oracle (CoT) 評估結果...")
    oracle_cot_results = load_eval_results(oracle_cot_eval_file, qtype_map)
    
    print("載入 Oracle (CoN) 評估結果...")
    oracle_con_results = load_eval_results(oracle_con_eval_file, qtype_map)
    
    # 獲取所有問題類型（按字母順序排序）
    all_qtypes = sorted(set(
        list(rag_baseline_results.keys()) + 
        list(rag_userfact_cot_results.keys()) + 
        list(rag_userfact_con_results.keys()) +
        list(oracle_cot_results.keys()) +
        list(oracle_con_results.keys())
    ))
    
    # 計算整體準確率
    rag_baseline_total_all = sum(rag_baseline_results[qtype]['total'] for qtype in rag_baseline_results)
    rag_baseline_correct_all = sum(rag_baseline_results[qtype]['correct'] for qtype in rag_baseline_results)
    rag_baseline_acc_overall = (rag_baseline_correct_all / rag_baseline_total_all * 100) if rag_baseline_total_all > 0 else 0
    
    rag_userfact_cot_total_all = sum(rag_userfact_cot_results[qtype]['total'] for qtype in rag_userfact_cot_results)
    rag_userfact_cot_correct_all = sum(rag_userfact_cot_results[qtype]['correct'] for qtype in rag_userfact_cot_results)
    rag_userfact_cot_acc_overall = (rag_userfact_cot_correct_all / rag_userfact_cot_total_all * 100) if rag_userfact_cot_total_all > 0 else 0
    
    rag_userfact_con_total_all = sum(rag_userfact_con_results[qtype]['total'] for qtype in rag_userfact_con_results)
    rag_userfact_con_correct_all = sum(rag_userfact_con_results[qtype]['correct'] for qtype in rag_userfact_con_results)
    rag_userfact_con_acc_overall = (rag_userfact_con_correct_all / rag_userfact_con_total_all * 100) if rag_userfact_con_total_all > 0 else 0
    
    oracle_cot_total_all = sum(oracle_cot_results[qtype]['total'] for qtype in oracle_cot_results)
    oracle_cot_correct_all = sum(oracle_cot_results[qtype]['correct'] for qtype in oracle_cot_results)
    oracle_cot_acc_overall = (oracle_cot_correct_all / oracle_cot_total_all * 100) if oracle_cot_total_all > 0 else 0
    
    oracle_con_total_all = sum(oracle_con_results[qtype]['total'] for qtype in oracle_con_results)
    oracle_con_correct_all = sum(oracle_con_results[qtype]['correct'] for qtype in oracle_con_results)
    oracle_con_acc_overall = (oracle_con_correct_all / oracle_con_total_all * 100) if oracle_con_total_all > 0 else 0
    
    # 準備數據
    rag_baseline_acc = []
    rag_baseline_counts = []
    rag_baseline_tokens = []
    
    rag_userfact_cot_acc = []
    rag_userfact_cot_counts = []
    rag_userfact_cot_tokens = []
    
    rag_userfact_con_acc = []
    rag_userfact_con_counts = []
    rag_userfact_con_tokens = []
    
    oracle_cot_acc = []
    oracle_cot_counts = []
    oracle_cot_tokens = []
    
    oracle_con_acc = []
    oracle_con_counts = []
    oracle_con_tokens = []
    
    for qtype in all_qtypes:
        # RAG baseline
        baseline_total = rag_baseline_results[qtype]['total']
        baseline_correct = rag_baseline_results[qtype]['correct']
        rag_baseline_acc.append((baseline_correct / baseline_total * 100) if baseline_total > 0 else 0)
        rag_baseline_counts.append(f"{baseline_correct}/{baseline_total}")
        rag_baseline_tokens.append(rag_baseline_results[qtype]['avg_tokens'])
        
        # RAG + UserFact (CoT)
        userfact_cot_total = rag_userfact_cot_results[qtype]['total']
        userfact_cot_correct = rag_userfact_cot_results[qtype]['correct']
        rag_userfact_cot_acc.append((userfact_cot_correct / userfact_cot_total * 100) if userfact_cot_total > 0 else 0)
        rag_userfact_cot_counts.append(f"{userfact_cot_correct}/{userfact_cot_total}")
        rag_userfact_cot_tokens.append(rag_userfact_cot_results[qtype]['avg_tokens'])
        
        # RAG + UserFact (CoN)
        userfact_con_total = rag_userfact_con_results[qtype]['total']
        userfact_con_correct = rag_userfact_con_results[qtype]['correct']
        rag_userfact_con_acc.append((userfact_con_correct / userfact_con_total * 100) if userfact_con_total > 0 else 0)
        rag_userfact_con_counts.append(f"{userfact_con_correct}/{userfact_con_total}")
        rag_userfact_con_tokens.append(rag_userfact_con_results[qtype]['avg_tokens'])
        
        # Oracle (CoT)
        oracle_cot_total = oracle_cot_results[qtype]['total']
        oracle_cot_correct = oracle_cot_results[qtype]['correct']
        oracle_cot_acc.append((oracle_cot_correct / oracle_cot_total * 100) if oracle_cot_total > 0 else 0)
        oracle_cot_counts.append(f"{oracle_cot_correct}/{oracle_cot_total}")
        oracle_cot_tokens.append(oracle_cot_results[qtype]['avg_tokens'])
        
        # Oracle (CoN)
        oracle_con_total = oracle_con_results[qtype]['total']
        oracle_con_correct = oracle_con_results[qtype]['correct']
        oracle_con_acc.append((oracle_con_correct / oracle_con_total * 100) if oracle_con_total > 0 else 0)
        oracle_con_counts.append(f"{oracle_con_correct}/{oracle_con_total}")
        oracle_con_tokens.append(oracle_con_results[qtype]['avg_tokens'])
    
    # 創建圖表 - 增加垂直和水平空間
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
    
    x = np.arange(len(all_qtypes))
    width = 0.16  # 稍微增加寬度
    
    # 圖1: 正確率
    bars1 = ax1.bar(x - 2*width, rag_baseline_acc, width, label=f'RAG Baseline ({rag_baseline_acc_overall:.1f}%)', color='#3498db', alpha=0.8)
    bars2 = ax1.bar(x - width, rag_userfact_cot_acc, width, label=f'RAG+UF+CoT ({rag_userfact_cot_acc_overall:.1f}%)', color='#2ecc71', alpha=0.8)
    bars3 = ax1.bar(x, rag_userfact_con_acc, width, label=f'RAG+UF+CoN ({rag_userfact_con_acc_overall:.1f}%)', color='#e74c3c', alpha=0.8)
    bars4 = ax1.bar(x + width, oracle_cot_acc, width, label=f'Oracle CoT ({oracle_cot_acc_overall:.1f}%)', color='#9b59b6', alpha=0.8, edgecolor='black', linewidth=1.5, hatch='///')
    bars5 = ax1.bar(x + 2*width, oracle_con_acc, width, label=f'Oracle CoN ({oracle_con_acc_overall:.1f}%)', color='#f39c12', alpha=0.8, edgecolor='black', linewidth=1.5, hatch='///')
    
    ax1.set_xlabel('Question Type', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Accuracy (%)', fontsize=13, fontweight='bold')
    ax1.set_title('Accuracy by Question Type', fontsize=15, fontweight='bold', pad=40)
    ax1.set_xticks(x)
    ax1.set_xticklabels(all_qtypes, rotation=45, ha='right', fontsize=11)
    ax1.legend(fontsize=9, loc='upper left', ncol=2, framealpha=0.9)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    ax1.set_ylim([0, 120])  # 增加上限以容納標籤
    
    # 在標題上方添加整體準確率信息
    overall_text = (f'Overall: Baseline {rag_baseline_acc_overall:.1f}% | RAG+UF+CoT {rag_userfact_cot_acc_overall:.1f}% | '
                   f'RAG+UF+CoN {rag_userfact_con_acc_overall:.1f}% | Oracle CoT {oracle_cot_acc_overall:.1f}% | Oracle CoN {oracle_con_acc_overall:.1f}%')
    ax1.text(0.5, 1.03, overall_text, transform=ax1.transAxes, 
            ha='center', va='bottom', fontsize=9, 
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.6))
    
    # 在長條圖上添加數字標籤 - 使用旋轉和更小的字體
    for i, (bar1, bar2, bar3, bar4, bar5) in enumerate(zip(bars1, bars2, bars3, bars4, bars5)):
        heights = [bar1.get_height(), bar2.get_height(), bar3.get_height(), 
                  bar4.get_height(), bar5.get_height()]
        bars = [bar1, bar2, bar3, bar4, bar5]
        
        for j, (bar, height) in enumerate(zip(bars, heights)):
            if height > 0:
                # 對於較高的柱子使用不同的標籤位置
                if height > 10:
                    label_y = height + 1.5
                    va_pos = 'bottom'
                else:
                    label_y = height + 2
                    va_pos = 'bottom'
                
                # Oracle 使用粗體
                is_oracle = (j >= 3)
                ax1.text(bar.get_x() + bar.get_width()/2., label_y,
                        f'{height:.1f}',
                        ha='center', va=va_pos, fontsize=7,
                        rotation=0, weight='bold' if is_oracle else 'normal')
    
    # 圖2: 平均 tokens
    bars6 = ax2.bar(x - 2*width, rag_baseline_tokens, width, label='RAG Baseline', color='#3498db', alpha=0.8)
    bars7 = ax2.bar(x - width, rag_userfact_cot_tokens, width, label='RAG+UF+CoT', color='#2ecc71', alpha=0.8)
    bars8 = ax2.bar(x, rag_userfact_con_tokens, width, label='RAG+UF+CoN', color='#e74c3c', alpha=0.8)
    bars9 = ax2.bar(x + width, oracle_cot_tokens, width, label='Oracle CoT', color='#9b59b6', alpha=0.8, edgecolor='black', linewidth=1.5, hatch='///')
    bars10 = ax2.bar(x + 2*width, oracle_con_tokens, width, label='Oracle CoN', color='#f39c12', alpha=0.8, edgecolor='black', linewidth=1.5, hatch='///')
    
    ax2.set_xlabel('Question Type', fontsize=13, fontweight='bold')
    ax2.set_ylabel('Average Input Tokens', fontsize=13, fontweight='bold')
    ax2.set_title('Average Input Tokens by Question Type', fontsize=15, fontweight='bold', pad=20)
    ax2.set_xticks(x)
    ax2.set_xticklabels(all_qtypes, rotation=45, ha='right', fontsize=11)
    ax2.legend(fontsize=9, loc='upper left', ncol=2, framealpha=0.9)
    ax2.grid(axis='y', alpha=0.3, linestyle='--')
    
    # 為 tokens 圖表設置更高的上限
    max_token = max(max(rag_baseline_tokens), max(rag_userfact_cot_tokens), max(rag_userfact_con_tokens),
                   max(oracle_cot_tokens), max(oracle_con_tokens))
    ax2.set_ylim([0, max_token * 1.15])
    
    # 在長條圖上添加數字標籤
    for i, (bar6, bar7, bar8, bar9, bar10) in enumerate(zip(bars6, bars7, bars8, bars9, bars10)):
        heights = [bar6.get_height(), bar7.get_height(), bar8.get_height(), 
                  bar9.get_height(), bar10.get_height()]
        bars = [bar6, bar7, bar8, bar9, bar10]
        
        for j, (bar, height) in enumerate(zip(bars, heights)):
            if height > 0:
                is_oracle = (j >= 3)
                ax2.text(bar.get_x() + bar.get_width()/2., height + max_token * 0.01,
                        f'{height:.0f}',
                        ha='center', va='bottom', fontsize=7,
                        weight='bold' if is_oracle else 'normal')
    
    plt.tight_layout()
    
    # 保存圖表
    output_file = 'analysis_RAG/rag_by_qtype_comparison.png'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n圖表已保存: {output_file}")
    
    # 打印統計摘要
    print("\n" + "="*100)
    print("統計摘要")
    print("="*100)
    print(f"\n整體準確率:")
    print(f"  RAG Baseline: {rag_baseline_acc_overall:.1f}% ({rag_baseline_correct_all}/{rag_baseline_total_all})")
    print(f"  RAG + UserFact + CoT: {rag_userfact_cot_acc_overall:.1f}% ({rag_userfact_cot_correct_all}/{rag_userfact_cot_total_all})")
    print(f"  RAG + UserFact + CoN: {rag_userfact_con_acc_overall:.1f}% ({rag_userfact_con_correct_all}/{rag_userfact_con_total_all})")
    print(f"  Oracle CoT: {oracle_cot_acc_overall:.1f}% ({oracle_cot_correct_all}/{oracle_cot_total_all})")
    print(f"  Oracle CoN: {oracle_con_acc_overall:.1f}% ({oracle_con_correct_all}/{oracle_con_total_all})")
    print(f"\n  差異 (相對於 Baseline):")
    print(f"    RAG+UserFact+CoT: {rag_userfact_cot_acc_overall - rag_baseline_acc_overall:+.1f}%")
    print(f"    RAG+UserFact+CoN: {rag_userfact_con_acc_overall - rag_baseline_acc_overall:+.1f}%")
    print(f"    Oracle CoT: {oracle_cot_acc_overall - rag_baseline_acc_overall:+.1f}%")
    print(f"    Oracle CoN: {oracle_con_acc_overall - rag_baseline_acc_overall:+.1f}%")
    print("\n" + "-"*100)
    print(f"{'Question Type':<25} {'Baseline':<12} {'+UF+CoT':<12} {'+UF+CoN':<12} {'Oracle CoT':<12} {'Oracle CoN':<12}")
    print("-"*100)
    
    for qtype in all_qtypes:
        baseline_total = rag_baseline_results[qtype]['total']
        baseline_correct = rag_baseline_results[qtype]['correct']
        baseline_acc_val = (baseline_correct / baseline_total * 100) if baseline_total > 0 else 0
        
        userfact_cot_total = rag_userfact_cot_results[qtype]['total']
        userfact_cot_correct = rag_userfact_cot_results[qtype]['correct']
        userfact_cot_acc_val = (userfact_cot_correct / userfact_cot_total * 100) if userfact_cot_total > 0 else 0
        
        userfact_con_total = rag_userfact_con_results[qtype]['total']
        userfact_con_correct = rag_userfact_con_results[qtype]['correct']
        userfact_con_acc_val = (userfact_con_correct / userfact_con_total * 100) if userfact_con_total > 0 else 0
        
        oracle_cot_total = oracle_cot_results[qtype]['total']
        oracle_cot_correct = oracle_cot_results[qtype]['correct']
        oracle_cot_acc_val = (oracle_cot_correct / oracle_cot_total * 100) if oracle_cot_total > 0 else 0
        
        oracle_con_total = oracle_con_results[qtype]['total']
        oracle_con_correct = oracle_con_results[qtype]['correct']
        oracle_con_acc_val = (oracle_con_correct / oracle_con_total * 100) if oracle_con_total > 0 else 0
        
        print(f"{qtype:<25} {baseline_acc_val:>6.1f}%  {userfact_cot_acc_val:>6.1f}%  {userfact_con_acc_val:>6.1f}%  {oracle_cot_acc_val:>6.1f}%  {oracle_con_acc_val:>6.1f}%")

if __name__ == '__main__':
    main()