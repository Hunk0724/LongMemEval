#!/usr/bin/env python3
"""
分析 CoT 和 CoN 在不同問題類型上的表現
支持兩種模式：
1. 兩組比較：原始 Oracle + CoT vs 原始 Oracle + CoN
2. 三組比較：原始 Oracle + CoT vs 答案專用 Oracle + CoT vs 原始 Oracle + CoN

生成兩個圖表：
1. 正確率（按問題類型）
2. 平均 input tokens（按問題類型）
"""

import json
import sys
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

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
    if len(sys.argv) < 4:
        print("用法（兩組比較）: python3 analyze_cot_con_by_qtype.py <data_file> <cot_eval_file> <con_eval_file>")
        print("用法（三組比較）: python3 analyze_cot_con_by_qtype.py <data_file> <oracle_cot_eval> <answer_only_cot_eval> <oracle_con_eval>")
        sys.exit(1)
    
    data_file = sys.argv[1]
    is_three_way = len(sys.argv) >= 5
    
    # 載入問題類型
    print("載入問題類型...")
    qtype_map = load_question_types(data_file)
    
    if is_three_way:
        # 三組比較模式
        oracle_cot_eval = sys.argv[2]
        answer_only_cot_eval = sys.argv[3]
        oracle_con_eval = sys.argv[4]
        
        print("載入原始 Oracle + CoT 評估結果...")
        oracle_cot_results = load_eval_results(oracle_cot_eval, qtype_map)
        
        print("載入答案專用 Oracle + CoT 評估結果...")
        answer_only_cot_results = load_eval_results(answer_only_cot_eval, qtype_map)
        
        print("載入原始 Oracle + CoN 評估結果...")
        oracle_con_results = load_eval_results(oracle_con_eval, qtype_map)
        
        # 獲取所有問題類型
        all_qtypes = sorted(set(list(oracle_cot_results.keys()) + 
                               list(answer_only_cot_results.keys()) + 
                               list(oracle_con_results.keys())))
        
        # 計算整體準確率
        def calc_overall(results):
            total = sum(results[qtype]['total'] for qtype in results)
            correct = sum(results[qtype]['correct'] for qtype in results)
            acc = (correct / total * 100) if total > 0 else 0
            return acc, correct, total
        
        oracle_cot_acc, oracle_cot_correct, oracle_cot_total = calc_overall(oracle_cot_results)
        answer_only_cot_acc, answer_only_cot_correct, answer_only_cot_total = calc_overall(answer_only_cot_results)
        oracle_con_acc, oracle_con_correct, oracle_con_total = calc_overall(oracle_con_results)
        
        # 準備數據
        oracle_cot_acc_list = []
        oracle_cot_counts = []
        oracle_cot_tokens = []
        
        answer_only_cot_acc_list = []
        answer_only_cot_counts = []
        answer_only_cot_tokens = []
        
        oracle_con_acc_list = []
        oracle_con_counts = []
        oracle_con_tokens = []
        
        for qtype in all_qtypes:
            # 原始 Oracle + CoT
            total = oracle_cot_results[qtype]['total']
            correct = oracle_cot_results[qtype]['correct']
            oracle_cot_acc_list.append((correct / total * 100) if total > 0 else 0)
            oracle_cot_counts.append(f"{correct}/{total}")
            oracle_cot_tokens.append(oracle_cot_results[qtype]['avg_tokens'])
            
            # 答案專用 Oracle + CoT
            total = answer_only_cot_results[qtype]['total']
            correct = answer_only_cot_results[qtype]['correct']
            answer_only_cot_acc_list.append((correct / total * 100) if total > 0 else 0)
            answer_only_cot_counts.append(f"{correct}/{total}")
            answer_only_cot_tokens.append(answer_only_cot_results[qtype]['avg_tokens'])
            
            # 原始 Oracle + CoN
            total = oracle_con_results[qtype]['total']
            correct = oracle_con_results[qtype]['correct']
            oracle_con_acc_list.append((correct / total * 100) if total > 0 else 0)
            oracle_con_counts.append(f"{correct}/{total}")
            oracle_con_tokens.append(oracle_con_results[qtype]['avg_tokens'])
        
        # 創建圖表（三組）
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
        
        x = np.arange(len(all_qtypes))
        width = 0.25
        
        # 圖1: 正確率
        bars1 = ax1.bar(x - width, oracle_cot_acc_list, width, 
                       label=f'Oracle+CoT ({oracle_cot_acc:.1f}%)', 
                       color='#3498db', alpha=0.8)
        bars2 = ax1.bar(x, answer_only_cot_acc_list, width, 
                       label=f'Answer-Only+CoT ({answer_only_cot_acc:.1f}%)', 
                       color='#2ecc71', alpha=0.8)
        bars3 = ax1.bar(x + width, oracle_con_acc_list, width, 
                       label=f'Oracle+CoN ({oracle_con_acc:.1f}%)', 
                       color='#e74c3c', alpha=0.8)
        
        ax1.set_xlabel('Question Type', fontsize=12)
        ax1.set_ylabel('Accuracy (%)', fontsize=12)
        ax1.set_title('Accuracy by Question Type', fontsize=14, fontweight='bold', pad=40)
        ax1.set_xticks(x)
        ax1.set_xticklabels(all_qtypes, rotation=45, ha='right')
        ax1.legend(fontsize=9, loc='upper left')
        ax1.grid(axis='y', alpha=0.3)
        ax1.set_ylim([0, 120])
        
        # 在標題上方添加整體準確率信息
        overall_text = (f'Overall: Oracle+CoT {oracle_cot_acc:.1f}% ({oracle_cot_correct}/{oracle_cot_total}) | '
                       f'Answer-Only+CoT {answer_only_cot_acc:.1f}% ({answer_only_cot_correct}/{answer_only_cot_total}) | '
                       f'Oracle+CoN {oracle_con_acc:.1f}% ({oracle_con_correct}/{oracle_con_total})')
        ax1.text(0.5, 1.02, overall_text, transform=ax1.transAxes, 
                ha='center', va='bottom', fontsize=9, 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.6))
        
        # 在長條圖上添加數字標籤
        for i, (bar1, bar2, bar3) in enumerate(zip(bars1, bars2, bars3)):
            height1 = bar1.get_height()
            height2 = bar2.get_height()
            height3 = bar3.get_height()
            
            if height1 > 0:
                ax1.text(bar1.get_x() + bar1.get_width()/2., height1 + 1,
                        f'{oracle_cot_counts[i]}\n{height1:.1f}%',
                        ha='center', va='bottom', fontsize=7)
            if height2 > 0:
                ax1.text(bar2.get_x() + bar2.get_width()/2., height2 + 1,
                        f'{answer_only_cot_counts[i]}\n{height2:.1f}%',
                        ha='center', va='bottom', fontsize=7)
            if height3 > 0:
                ax1.text(bar3.get_x() + bar3.get_width()/2., height3 + 1,
                        f'{oracle_con_counts[i]}\n{height3:.1f}%',
                        ha='center', va='bottom', fontsize=7)
        
        # 圖2: 平均 tokens
        bars4 = ax2.bar(x - width, oracle_cot_tokens, width, label='Oracle+CoT', color='#3498db', alpha=0.8)
        bars5 = ax2.bar(x, answer_only_cot_tokens, width, label='Answer-Only+CoT', color='#2ecc71', alpha=0.8)
        bars6 = ax2.bar(x + width, oracle_con_tokens, width, label='Oracle+CoN', color='#e74c3c', alpha=0.8)
        
        ax2.set_xlabel('Question Type', fontsize=12)
        ax2.set_ylabel('Average Input Tokens', fontsize=12)
        ax2.set_title('Average Input Tokens by Question Type', fontsize=14, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels(all_qtypes, rotation=45, ha='right')
        ax2.legend(fontsize=9, loc='upper left')
        ax2.grid(axis='y', alpha=0.3)
        
        # 在長條圖上添加數字標籤
        max_token = max(max(oracle_cot_tokens), max(answer_only_cot_tokens), max(oracle_con_tokens))
        for i, (bar4, bar5, bar6) in enumerate(zip(bars4, bars5, bars6)):
            height4 = bar4.get_height()
            height5 = bar5.get_height()
            height6 = bar6.get_height()
            
            if height4 > 0:
                ax2.text(bar4.get_x() + bar4.get_width()/2., height4 + max_token * 0.01,
                        f'{height4:.0f}', ha='center', va='bottom', fontsize=8)
            if height5 > 0:
                ax2.text(bar5.get_x() + bar5.get_width()/2., height5 + max_token * 0.01,
                        f'{height5:.0f}', ha='center', va='bottom', fontsize=8)
            if height6 > 0:
                ax2.text(bar6.get_x() + bar6.get_width()/2., height6 + max_token * 0.01,
                        f'{height6:.0f}', ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        
        # 保存圖表
        output_file = 'analysis_oracle/oracle_variants_by_qtype_comparison.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"\n圖表已保存: {output_file}")
        
        # 打印統計摘要
        print("\n" + "="*100)
        print("統計摘要")
        print("="*100)
        print(f"\n整體準確率:")
        print(f"  Oracle+CoT:        {oracle_cot_acc:.1f}% ({oracle_cot_correct}/{oracle_cot_total})")
        print(f"  Answer-Only+CoT:   {answer_only_cot_acc:.1f}% ({answer_only_cot_correct}/{answer_only_cot_total})")
        print(f"  Oracle+CoN:        {oracle_con_acc:.1f}% ({oracle_con_correct}/{oracle_con_total})")
        print(f"\n準確率差異:")
        print(f"  Answer-Only+CoT vs Oracle+CoT: {answer_only_cot_acc - oracle_cot_acc:+.1f}%")
        print(f"  Oracle+CoN vs Oracle+CoT:       {oracle_con_acc - oracle_cot_acc:+.1f}%")
        print(f"  Oracle+CoN vs Answer-Only+CoT: {oracle_con_acc - answer_only_cot_acc:+.1f}%")
        
        print("\n" + "-"*100)
        print(f"{'Question Type':<25} {'Oracle+CoT':<15} {'Answer-Only+CoT':<18} {'Oracle+CoN':<15}")
        print("-"*100)
        
        for qtype in all_qtypes:
            oracle_cot_total = oracle_cot_results[qtype]['total']
            oracle_cot_correct = oracle_cot_results[qtype]['correct']
            oracle_cot_acc_val = (oracle_cot_correct / oracle_cot_total * 100) if oracle_cot_total > 0 else 0
            
            answer_only_cot_total = answer_only_cot_results[qtype]['total']
            answer_only_cot_correct = answer_only_cot_results[qtype]['correct']
            answer_only_cot_acc_val = (answer_only_cot_correct / answer_only_cot_total * 100) if answer_only_cot_total > 0 else 0
            
            oracle_con_total = oracle_con_results[qtype]['total']
            oracle_con_correct = oracle_con_results[qtype]['correct']
            oracle_con_acc_val = (oracle_con_correct / oracle_con_total * 100) if oracle_con_total > 0 else 0
            
            print(f"{qtype:<25} {oracle_cot_acc_val:>6.1f}% ({oracle_cot_correct:>3}/{oracle_cot_total:<3})  "
                  f"{answer_only_cot_acc_val:>6.1f}% ({answer_only_cot_correct:>3}/{answer_only_cot_total:<3})  "
                  f"{oracle_con_acc_val:>6.1f}% ({oracle_con_correct:>3}/{oracle_con_total:<3})")
        
        return
    
    # 兩組比較模式（原始邏輯）
    cot_eval_file = sys.argv[2]
    con_eval_file = sys.argv[3]
    
    # 載入評估結果
    print("載入 CoT 評估結果...")
    cot_results = load_eval_results(cot_eval_file, qtype_map)
    
    print("載入 CoN 評估結果...")
    con_results = load_eval_results(con_eval_file, qtype_map)
    
    # 獲取所有問題類型（按字母順序排序）
    all_qtypes = sorted(set(list(cot_results.keys()) + list(con_results.keys())))
    
    # 計算整體準確率
    cot_total_all = sum(cot_results[qtype]['total'] for qtype in cot_results)
    cot_correct_all = sum(cot_results[qtype]['correct'] for qtype in cot_results)
    cot_acc_overall = (cot_correct_all / cot_total_all * 100) if cot_total_all > 0 else 0
    
    con_total_all = sum(con_results[qtype]['total'] for qtype in con_results)
    con_correct_all = sum(con_results[qtype]['correct'] for qtype in con_results)
    con_acc_overall = (con_correct_all / con_total_all * 100) if con_total_all > 0 else 0
    
    # 準備數據
    cot_acc = []
    cot_counts = []
    cot_tokens = []
    
    con_acc = []
    con_counts = []
    con_tokens = []
    
    for qtype in all_qtypes:
        # CoT
        cot_total = cot_results[qtype]['total']
        cot_correct = cot_results[qtype]['correct']
        cot_acc.append((cot_correct / cot_total * 100) if cot_total > 0 else 0)
        cot_counts.append(f"{cot_correct}/{cot_total}")
        cot_tokens.append(cot_results[qtype]['avg_tokens'])
        
        # CoN
        con_total = con_results[qtype]['total']
        con_correct = con_results[qtype]['correct']
        con_acc.append((con_correct / con_total * 100) if con_total > 0 else 0)
        con_counts.append(f"{con_correct}/{con_total}")
        con_tokens.append(con_results[qtype]['avg_tokens'])
    
    # 創建圖表 - 增加垂直空間
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    
    x = np.arange(len(all_qtypes))
    width = 0.35
    
    # 圖1: 正確率
    bars1 = ax1.bar(x - width/2, cot_acc, width, label=f'CoT (Overall: {cot_acc_overall:.1f}%)', color='#3498db', alpha=0.8)
    bars2 = ax1.bar(x + width/2, con_acc, width, label=f'CoN (Overall: {con_acc_overall:.1f}%)', color='#e74c3c', alpha=0.8)
    
    ax1.set_xlabel('Question Type', fontsize=12)
    ax1.set_ylabel('Accuracy (%)', fontsize=12)
    ax1.set_title('Accuracy by Question Type', fontsize=14, fontweight='bold', pad=35)  # 增加標題與圖表間距
    ax1.set_xticks(x)
    ax1.set_xticklabels(all_qtypes, rotation=45, ha='right')
    ax1.legend(fontsize=10, loc='upper left')
    ax1.grid(axis='y', alpha=0.3)
    ax1.set_ylim([0, 115])  # 增加上限以容納標籤
    
    # 在標題上方添加整體準確率信息（使用 figure 坐標）
    overall_text = f'Overall Accuracy: CoT {cot_acc_overall:.1f}% ({cot_correct_all}/{cot_total_all}) | CoN {con_acc_overall:.1f}% ({con_correct_all}/{con_total_all})'
    ax1.text(0.5, 1.02, overall_text, transform=ax1.transAxes, 
            ha='center', va='bottom', fontsize=10, 
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # 在長條圖上添加數字標籤
    for i, (bar1, bar2) in enumerate(zip(bars1, bars2)):
        height1 = bar1.get_height()
        height2 = bar2.get_height()
        
        # CoT 標籤
        ax1.text(bar1.get_x() + bar1.get_width()/2., height1 + 1,
                f'{cot_counts[i]}\n{height1:.1f}%',
                ha='center', va='bottom', fontsize=8)
        
        # CoN 標籤
        ax1.text(bar2.get_x() + bar2.get_width()/2., height2 + 1,
                f'{con_counts[i]}\n{height2:.1f}%',
                ha='center', va='bottom', fontsize=8)
    
    # 圖2: 平均 tokens
    bars3 = ax2.bar(x - width/2, cot_tokens, width, label='CoT', color='#3498db', alpha=0.8)
    bars4 = ax2.bar(x + width/2, con_tokens, width, label='CoN', color='#e74c3c', alpha=0.8)
    
    ax2.set_xlabel('Question Type', fontsize=12)
    ax2.set_ylabel('Average Input Tokens', fontsize=12)
    ax2.set_title('Average Input Tokens by Question Type', fontsize=14, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(all_qtypes, rotation=45, ha='right')
    ax2.legend(fontsize=10, loc='upper left')
    ax2.grid(axis='y', alpha=0.3)
    
    # 在長條圖上添加數字標籤
    for i, (bar3, bar4) in enumerate(zip(bars3, bars4)):
        height3 = bar3.get_height()
        height4 = bar4.get_height()
        
        # CoT 標籤
        if height3 > 0:
            ax2.text(bar3.get_x() + bar3.get_width()/2., height3,
                    f'{height3:.0f}',
                    ha='center', va='bottom', fontsize=9)
        
        # CoN 標籤
        if height4 > 0:
            ax2.text(bar4.get_x() + bar4.get_width()/2., height4,
                    f'{height4:.0f}',
                    ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    
    # 保存圖表
    output_file = 'analysis_oracle/cot_con_by_qtype_comparison.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n圖表已保存: {output_file}")
    
    # 打印統計摘要
    print("\n" + "="*80)
    print("統計摘要")
    print("="*80)
    print(f"\n整體準確率:")
    print(f"  CoT: {cot_acc_overall:.1f}% ({cot_correct_all}/{cot_total_all})")
    print(f"  CoN: {con_acc_overall:.1f}% ({con_correct_all}/{con_total_all})")
    print(f"  差異: {con_acc_overall - cot_acc_overall:+.1f}%")
    print("\n" + "-"*80)
    print(f"{'Question Type':<25} {'CoT Acc':<12} {'CoN Acc':<12} {'CoT Tokens':<15} {'CoN Tokens':<15}")
    print("-"*80)
    
    for qtype in all_qtypes:
        cot_total = cot_results[qtype]['total']
        cot_correct = cot_results[qtype]['correct']
        cot_acc_val = (cot_correct / cot_total * 100) if cot_total > 0 else 0
        
        con_total = con_results[qtype]['total']
        con_correct = con_results[qtype]['correct']
        con_acc_val = (con_correct / con_total * 100) if con_total > 0 else 0
        
        cot_tok = cot_results[qtype]['avg_tokens']
        con_tok = con_results[qtype]['avg_tokens']
        
        print(f"{qtype:<25} {cot_acc_val:>6.1f}% ({cot_correct}/{cot_total})  {con_acc_val:>6.1f}% ({con_correct}/{con_total})  {cot_tok:>8.0f}      {con_tok:>8.0f}")

if __name__ == '__main__':
    main()