#!/usr/bin/env python3
"""
分析 RAG 檢索表現，使用多種指標評估檢索品質
比較有 userfact 和沒有 userfact 的檢索表現

使用的指標：
- recall_all@k: 全有或全無指標，= 1 如果所有 evidence sessions 都在 top-k 中
- recall_any@k: 至少一個指標，= 1 如果至少有一個 evidence session 在 top-k 中
- ndcg_any@k: Normalized Discounted Cumulative Gain，考慮排序位置的加權指標
"""

import json
import sys
import os
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

def load_question_types(data_file):
    """從原始數據集載入問題類型和 evidence sessions"""
    qtype_map = {}
    evidence_map = {}
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for entry in data:
            qid = entry['question_id']
            qtype = entry.get('question_type', 'unknown')
            qtype_map[qid] = qtype
            
            # 獲取 evidence session IDs
            evidence_sessions = entry.get('haystack_session_ids', [])
            evidence_map[qid] = set(evidence_sessions)
    
    return qtype_map, evidence_map

def load_retrieval_results(retrieval_file, qtype_map, evidence_map):
    """
    載入檢索結果並提取 recall_all@k 指標
    
    檢索文件格式應包含：
    - question_id
    - retrieval_results.metrics.turn.recall_all@k (已計算好的指標)
    """
    results = defaultdict(lambda: {
        'recall_all@5': [],
        'recall_all@10': [],
        'recall_all@30': [],
        'recall_all@50': [],
        'recall_any@5': [],
        'recall_any@10': [],
        'recall_any@30': [],
        'recall_any@50': [],
        'ndcg_any@5': [],
        'ndcg_any@10': [],
        'ndcg_any@30': [],
        'ndcg_any@50': [],
        'total': 0
    })
    
    has_retrieval_results = False
    missing_metrics_count = 0
    
    with open(retrieval_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                qid = entry['question_id']
                qtype = qtype_map.get(qid, 'unknown')
                
                # 獲取檢索結果
                retrieval_results = entry.get('retrieval_results', {})
                
                if not retrieval_results:
                    continue
                
                has_retrieval_results = True
                
                # 直接使用已計算好的 metrics
                metrics = retrieval_results.get('metrics', {})
                turn_metrics = metrics.get('turn', {})
                
                if not turn_metrics:
                    missing_metrics_count += 1
                    continue
                
                # 提取 recall_all@k、recall_any@k 和 ndcg_any@k 指標
                for k in [5, 10, 30, 50]:
                    metric_name_all = f'recall_all@{k}'
                    metric_name_any = f'recall_any@{k}'
                    metric_name_ndcg = f'ndcg_any@{k}'
                    if metric_name_all in turn_metrics:
                        recall_all = turn_metrics[metric_name_all]
                        results[qtype][metric_name_all].append(recall_all)
                    if metric_name_any in turn_metrics:
                        recall_any = turn_metrics[metric_name_any]
                        results[qtype][metric_name_any].append(recall_any)
                    if metric_name_ndcg in turn_metrics:
                        ndcg_any = turn_metrics[metric_name_ndcg]
                        results[qtype][metric_name_ndcg].append(ndcg_any)
                
                results[qtype]['total'] += 1
                
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Failed to parse line: {e}", file=sys.stderr)
                continue
    
    if not has_retrieval_results:
        print(f"\n錯誤: 文件 {retrieval_file} 不包含 'retrieval_results' 字段")
        return None
    
    if missing_metrics_count > 0:
        print(f"警告: {missing_metrics_count} 個問題缺少 metrics")
    
    # 計算平均 recall_all、recall_any 和 ndcg_any
    for qtype in results:
        for k in [5, 10, 30, 50]:
            for metric_type in ['recall_all', 'recall_any', 'ndcg_any']:
                metric_name = f'{metric_type}@{k}'
                if results[qtype][metric_name]:
                    results[qtype][f'avg_{metric_name}'] = np.mean(results[qtype][metric_name])
                else:
                    results[qtype][f'avg_{metric_name}'] = 0.0
    
    return results

def main():
    if len(sys.argv) < 4:
        print("用法: python3 analyze_retrieval_metrics.py <data_file> <retrieval_file_none> <retrieval_file_userfact>")
        print("  或: python3 analyze_retrieval_metrics.py <data_file> <retrieval_file_none> <retrieval_file_userfact> [output_prefix]")
        sys.exit(1)
    
    data_file = sys.argv[1]
    retrieval_file_none = sys.argv[2]  # 沒有 userfact 的檢索結果
    retrieval_file_userfact = sys.argv[3]  # 有 userfact 的檢索結果
    output_prefix = sys.argv[4] if len(sys.argv) > 4 else 'retrieval_metrics'
    
    # 載入問題類型和 evidence
    print("Loading question types...")
    qtype_map, evidence_map = load_question_types(data_file)
    
    # 載入檢索結果
    print("Loading retrieval results (no userfact)...")
    results_none = load_retrieval_results(retrieval_file_none, qtype_map, evidence_map)
    
    print("Loading retrieval results (with userfact)...")
    results_userfact = load_retrieval_results(retrieval_file_userfact, qtype_map, evidence_map)
    
    # 檢查是否成功載入
    if results_none is None or results_userfact is None:
        print("\n無法繼續分析，請檢查檢索結果文件格式")
        sys.exit(1)
    
    # 獲取所有問題類型
    all_qtypes = sorted(set(list(results_none.keys()) + list(results_userfact.keys())))
    
    # 計算整體 recall_all 和 recall_any
    k_values = [5, 10, 30, 50]
    
    print("\n" + "="*100)
    print("Retrieval Performance Statistics")
    print("="*100)
    
    print("\nOverall Performance - Recall All (All or Nothing):")
    for k in k_values:
        metric_name = f'recall_all@{k}'
        none_all = []
        userfact_all = []
        
        for qtype in all_qtypes:
            if qtype in results_none:
                none_all.extend(results_none[qtype][metric_name])
            if qtype in results_userfact:
                userfact_all.extend(results_userfact[qtype][metric_name])
        
        none_avg = np.mean(none_all) if none_all else 0.0
        userfact_avg = np.mean(userfact_all) if userfact_all else 0.0
        
        print(f"  Recall All@{k}:")
        print(f"    No UserFact: {none_avg:.4f} ({len(none_all)} questions)")
        print(f"    With UserFact: {userfact_avg:.4f} ({len(userfact_all)} questions)")
        print(f"    Difference: {userfact_avg - none_avg:+.4f}")
    
    print("\nOverall Performance - Recall Any (At Least One):")
    print("  Note: Recall Any may be 0.0 when correct_docs is empty (all 'answer' sessions have has_answer=False)")
    for k in k_values:
        metric_name = f'recall_any@{k}'
        none_any = []
        userfact_any = []
        
        for qtype in all_qtypes:
            if qtype in results_none:
                none_any.extend(results_none[qtype][metric_name])
            if qtype in results_userfact:
                userfact_any.extend(results_userfact[qtype][metric_name])
        
        none_avg = np.mean(none_any) if none_any else 0.0
        userfact_avg = np.mean(userfact_any) if userfact_any else 0.0
        
        print(f"  Recall Any@{k}:")
        print(f"    No UserFact: {none_avg:.4f} ({len(none_any)} questions)")
        print(f"    With UserFact: {userfact_avg:.4f} ({len(userfact_any)} questions)")
        print(f"    Difference: {userfact_avg - none_avg:+.4f}")
    
    print("\nOverall Performance - NDCG Any (Normalized Discounted Cumulative Gain):")
    print("  Note: NDCG considers ranking position - higher scores when relevant docs appear earlier")
    for k in k_values:
        metric_name = f'ndcg_any@{k}'
        none_ndcg = []
        userfact_ndcg = []
        
        for qtype in all_qtypes:
            if qtype in results_none:
                none_ndcg.extend(results_none[qtype][metric_name])
            if qtype in results_userfact:
                userfact_ndcg.extend(results_userfact[qtype][metric_name])
        
        none_avg = np.mean(none_ndcg) if none_ndcg else 0.0
        userfact_avg = np.mean(userfact_ndcg) if userfact_ndcg else 0.0
        
        print(f"  NDCG Any@{k}:")
        print(f"    No UserFact: {none_avg:.4f} ({len(none_ndcg)} questions)")
        print(f"    With UserFact: {userfact_avg:.4f} ({len(userfact_ndcg)} questions)")
        print(f"    Difference: {userfact_avg - none_avg:+.4f}")
    
    print("\nBy Question Type - Recall All:")
    print(f"{'Question Type':<25} ", end='')
    for k in k_values:
        print(f"{'NoUF/UF@{k}':<15} ", end='')
    print()
    print("-"*100)
    
    for qtype in all_qtypes:
        print(f"{qtype:<25} ", end='')
        for k in k_values:
            metric_name = f'recall_all@{k}'
            none_val = results_none[qtype].get(f'avg_{metric_name}', 0.0) if qtype in results_none else 0.0
            userfact_val = results_userfact[qtype].get(f'avg_{metric_name}', 0.0) if qtype in results_userfact else 0.0
            print(f"{none_val:.4f}/{userfact_val:.4f}  ", end='')
        print()
    
    print("\nBy Question Type - Recall Any:")
    print(f"{'Question Type':<25} ", end='')
    for k in k_values:
        print(f"{'NoUF/UF@{k}':<15} ", end='')
    print()
    print("-"*100)
    
    for qtype in all_qtypes:
        print(f"{qtype:<25} ", end='')
        for k in k_values:
            metric_name = f'recall_any@{k}'
            none_val = results_none[qtype].get(f'avg_{metric_name}', 0.0) if qtype in results_none else 0.0
            userfact_val = results_userfact[qtype].get(f'avg_{metric_name}', 0.0) if qtype in results_userfact else 0.0
            print(f"{none_val:.4f}/{userfact_val:.4f}  ", end='')
        print()
    
    print("\nBy Question Type - NDCG Any:")
    print(f"{'Question Type':<25} ", end='')
    for k in k_values:
        print(f"{'NoUF/UF@{k}':<15} ", end='')
    print()
    print("-"*100)
    
    for qtype in all_qtypes:
        print(f"{qtype:<25} ", end='')
        for k in k_values:
            metric_name = f'ndcg_any@{k}'
            none_val = results_none[qtype].get(f'avg_{metric_name}', 0.0) if qtype in results_none else 0.0
            userfact_val = results_userfact[qtype].get(f'avg_{metric_name}', 0.0) if qtype in results_userfact else 0.0
            print(f"{none_val:.4f}/{userfact_val:.4f}  ", end='')
        print()
    
    # 創建圖表 - 12個子圖：4個 recall_all，4個 recall_any，4個 ndcg_any
    fig, axes = plt.subplots(3, 4, figsize=(20, 15))
    
    # 計算 overall 平均值（用於標示）
    overall_recall_all = {}
    overall_recall_any = {}
    overall_ndcg_any = {}
    
    for k in k_values:
        # Recall All overall
        metric_name = f'recall_all@{k}'
        none_all = []
        userfact_all = []
        for qtype in all_qtypes:
            if qtype in results_none:
                none_all.extend(results_none[qtype][metric_name])
            if qtype in results_userfact:
                userfact_all.extend(results_userfact[qtype][metric_name])
        overall_recall_all[k] = {
            'none': np.mean(none_all) if none_all else 0.0,
            'userfact': np.mean(userfact_all) if userfact_all else 0.0
        }
        
        # Recall Any overall
        metric_name = f'recall_any@{k}'
        none_any = []
        userfact_any = []
        for qtype in all_qtypes:
            if qtype in results_none:
                none_any.extend(results_none[qtype][metric_name])
            if qtype in results_userfact:
                userfact_any.extend(results_userfact[qtype][metric_name])
        overall_recall_any[k] = {
            'none': np.mean(none_any) if none_any else 0.0,
            'userfact': np.mean(userfact_any) if userfact_any else 0.0
        }
        
        # NDCG Any overall
        metric_name = f'ndcg_any@{k}'
        none_ndcg = []
        userfact_ndcg = []
        for qtype in all_qtypes:
            if qtype in results_none:
                none_ndcg.extend(results_none[qtype][metric_name])
            if qtype in results_userfact:
                userfact_ndcg.extend(results_userfact[qtype][metric_name])
        overall_ndcg_any[k] = {
            'none': np.mean(none_ndcg) if none_ndcg else 0.0,
            'userfact': np.mean(userfact_ndcg) if userfact_ndcg else 0.0
        }
    
    # Recall All 圖表
    for idx, k in enumerate(k_values):
        ax = axes[0, idx]
        metric_name = f'recall_all@{k}'
        
        x = np.arange(len(all_qtypes))
        width = 0.35
        
        none_vals = [results_none[qtype].get(f'avg_{metric_name}', 0.0) if qtype in results_none else 0.0 
                    for qtype in all_qtypes]
        userfact_vals = [results_userfact[qtype].get(f'avg_{metric_name}', 0.0) if qtype in results_userfact else 0.0 
                        for qtype in all_qtypes]
        
        bars1 = ax.bar(x - width/2, none_vals, width, label='No UserFact', color='#3498db', alpha=0.8)
        bars2 = ax.bar(x + width/2, userfact_vals, width, label='With UserFact', color='#e74c3c', alpha=0.8)
        
        ax.set_xlabel('Question Type', fontsize=10)
        ax.set_ylabel(f'Recall All@{k}', fontsize=10)
        ax.set_title(f'Recall All@{k} by Question Type', fontsize=11, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(all_qtypes, rotation=45, ha='right', fontsize=8)
        ax.legend(fontsize=8)
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim([0, 1.1])
        
        # 添加 overall 平均值標示
        overall_text = (f'Overall: NoUF {overall_recall_all[k]["none"]:.4f} | '
                       f'UF {overall_recall_all[k]["userfact"]:.4f}')
        ax.text(0.5, 1.02, overall_text, transform=ax.transAxes, 
                ha='center', va='bottom', fontsize=9, 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.6))
        
        # 添加數值標籤
        for i, (bar1, bar2) in enumerate(zip(bars1, bars2)):
            height1 = bar1.get_height()
            height2 = bar2.get_height()
            if height1 > 0:
                ax.text(bar1.get_x() + bar1.get_width()/2., height1 + 0.02,
                       f'{height1:.3f}', ha='center', va='bottom', fontsize=7)
            if height2 > 0:
                ax.text(bar2.get_x() + bar2.get_width()/2., height2 + 0.02,
                       f'{height2:.3f}', ha='center', va='bottom', fontsize=7)
    
    # Recall Any 圖表
    for idx, k in enumerate(k_values):
        ax = axes[1, idx]
        metric_name = f'recall_any@{k}'
        
        x = np.arange(len(all_qtypes))
        width = 0.35
        
        none_vals = [results_none[qtype].get(f'avg_{metric_name}', 0.0) if qtype in results_none else 0.0 
                    for qtype in all_qtypes]
        userfact_vals = [results_userfact[qtype].get(f'avg_{metric_name}', 0.0) if qtype in results_userfact else 0.0 
                        for qtype in all_qtypes]
        
        bars1 = ax.bar(x - width/2, none_vals, width, label='No UserFact', color='#3498db', alpha=0.8)
        bars2 = ax.bar(x + width/2, userfact_vals, width, label='With UserFact', color='#e74c3c', alpha=0.8)
        
        ax.set_xlabel('Question Type', fontsize=10)
        ax.set_ylabel(f'Recall Any@{k}', fontsize=10)
        ax.set_title(f'Recall Any@{k} by Question Type', fontsize=11, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(all_qtypes, rotation=45, ha='right', fontsize=8)
        ax.legend(fontsize=8)
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim([0, 1.1])
        
        # 添加 overall 平均值標示
        overall_text = (f'Overall: NoUF {overall_recall_any[k]["none"]:.4f} | '
                       f'UF {overall_recall_any[k]["userfact"]:.4f}')
        ax.text(0.5, 1.02, overall_text, transform=ax.transAxes, 
                ha='center', va='bottom', fontsize=9, 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.6))
        
        # 添加數值標籤
        for i, (bar1, bar2) in enumerate(zip(bars1, bars2)):
            height1 = bar1.get_height()
            height2 = bar2.get_height()
            if height1 > 0:
                ax.text(bar1.get_x() + bar1.get_width()/2., height1 + 0.02,
                       f'{height1:.3f}', ha='center', va='bottom', fontsize=7)
            if height2 > 0:
                ax.text(bar2.get_x() + bar2.get_width()/2., height2 + 0.02,
                       f'{height2:.3f}', ha='center', va='bottom', fontsize=7)
    
    # NDCG Any 圖表
    for idx, k in enumerate(k_values):
        ax = axes[2, idx]
        metric_name = f'ndcg_any@{k}'
        
        x = np.arange(len(all_qtypes))
        width = 0.35
        
        none_vals = [results_none[qtype].get(f'avg_{metric_name}', 0.0) if qtype in results_none else 0.0 
                    for qtype in all_qtypes]
        userfact_vals = [results_userfact[qtype].get(f'avg_{metric_name}', 0.0) if qtype in results_userfact else 0.0 
                        for qtype in all_qtypes]
        
        bars1 = ax.bar(x - width/2, none_vals, width, label='No UserFact', color='#3498db', alpha=0.8)
        bars2 = ax.bar(x + width/2, userfact_vals, width, label='With UserFact', color='#e74c3c', alpha=0.8)
        
        ax.set_xlabel('Question Type', fontsize=10)
        ax.set_ylabel(f'NDCG Any@{k}', fontsize=10)
        ax.set_title(f'NDCG Any@{k} by Question Type', fontsize=11, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(all_qtypes, rotation=45, ha='right', fontsize=8)
        ax.legend(fontsize=8)
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim([0, 1.1])
        
        # 添加 overall 平均值標示
        overall_text = (f'Overall: NoUF {overall_ndcg_any[k]["none"]:.4f} | '
                       f'UF {overall_ndcg_any[k]["userfact"]:.4f}')
        ax.text(0.5, 1.02, overall_text, transform=ax.transAxes, 
                ha='center', va='bottom', fontsize=9, 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.6))
        
        # 添加數值標籤
        for i, (bar1, bar2) in enumerate(zip(bars1, bars2)):
            height1 = bar1.get_height()
            height2 = bar2.get_height()
            if height1 > 0:
                ax.text(bar1.get_x() + bar1.get_width()/2., height1 + 0.02,
                       f'{height1:.3f}', ha='center', va='bottom', fontsize=7)
            if height2 > 0:
                ax.text(bar2.get_x() + bar2.get_width()/2., height2 + 0.02,
                       f'{height2:.3f}', ha='center', va='bottom', fontsize=7)
    
    plt.tight_layout()
    
    # 保存圖表
    output_file = f'analysis_RAG/{output_prefix}_recall_all.png'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\nChart saved: {output_file}")

if __name__ == '__main__':
    main()

