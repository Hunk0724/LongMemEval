import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import os


def calculate_recall(retrieval_results, answer_session_ids, k=10):
    """計算 Recall@K（Session 級別）"""
    if not retrieval_results or 'ranked_items' not in retrieval_results:
        return 0.0
    
    # 從 corpus_id 提取 session_id
    def get_session_id(corpus_id):
        parts = corpus_id.rsplit('_', 1)
        return parts[0] if len(parts) > 1 else corpus_id
    
    retrieved_items = retrieval_results['ranked_items'][:k]
    retrieved_sids = set([get_session_id(item['corpus_id']) for item in retrieved_items])
    
    # 計算 recall
    answer_sids_set = set(answer_session_ids)
    recall = len(retrieved_sids & answer_sids_set) / len(answer_sids_set) if answer_sids_set else 0.0
    
    return recall


def analyze(hypo_file, ref_file, retrieval_file=None, output_dir="."):
    """
    分析實驗結果，包含 Recall、位置偏差、證據數量等
    
    Args:
        hypo_file: 生成結果檔案 (eval-results)
        ref_file: 參考答案檔案
        retrieval_file: 檢索結果檔案（可選，用於計算 Recall）
        output_dir: 圖表輸出目錄
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 準備 Markdown 報告
    report_lines = []
    def print_and_log(text=""):
        """同時輸出到終端和記錄到報告"""
        print(text)
        report_lines.append(text)
    
    # 載入預測結果與原始資料
    try:
        preds = [json.loads(line) for line in open(hypo_file)]
    except:
        print_and_log(f"Error loading {hypo_file}")
        return
    
    ref_data = json.load(open(ref_file))
    ref_map = {x['question_id']: x for x in ref_data}
    
    # 載入檢索結果（如果提供）
    retrieval_map = {}
    if retrieval_file:
        try:
            retrieval_data = [json.loads(line) for line in open(retrieval_file)]
            retrieval_map = {x['question_id']: x for x in retrieval_data}
            print_and_log(f"✓ 載入檢索結果: {len(retrieval_map)} 個問題")
        except:
            print_and_log(f"Warning: 無法載入檢索結果檔案 {retrieval_file}")
    
    # 收集統計資料
    stats = []
    for p in preds:
        qid = p['question_id']
        if qid not in ref_map:
            continue
        
        ref = ref_map[qid]
        
        # 1. 取得評分結果
        is_correct = 1 if p.get('autoeval_label', {}).get('label', False) else 0
        
        # 2. 計算 Evidence 的位置
        haystack_ids = ref['haystack_session_ids']
        evidence_ids = ref['answer_session_ids']
        evidence_indices = [i for i, sess_id in enumerate(haystack_ids) if sess_id in evidence_ids]
        
        if not evidence_indices:
            avg_pos = -1
            min_pos = -1
            max_pos = -1
        else:
            avg_pos = np.mean(evidence_indices) / len(haystack_ids)
            min_pos = min(evidence_indices) / len(haystack_ids)
            max_pos = max(evidence_indices) / len(haystack_ids)
        
        # 3. 計算歷史長度
        history_len = len(haystack_ids)
        
        # 4. 計算 Evidence 數量
        evidence_count = len(evidence_indices)
        
        # 5. 計算 Recall（如果有檢索結果）
        recall_5 = 0.0
        recall_10 = 0.0
        recall_50 = 0.0
        if qid in retrieval_map:
            retrieval_results = retrieval_map[qid].get('retrieval_results', {})
            recall_5 = calculate_recall(retrieval_results, evidence_ids, k=5)
            recall_10 = calculate_recall(retrieval_results, evidence_ids, k=10)
            recall_50 = calculate_recall(retrieval_results, evidence_ids, k=50)
        
        stats.append({
            'question_id': qid,
            'question_type': ref['question_type'],
            'is_correct': is_correct,
            'evidence_pos_avg': avg_pos,
            'evidence_pos_min': min_pos,  # 最早的證據位置
            'evidence_pos_max': max_pos,  # 最晚的證據位置
            'evidence_count': evidence_count,
            'history_len': history_len,
            'recall@5': recall_5,
            'recall@10': recall_10,
            'recall@50': recall_50
        })
    
    df = pd.DataFrame(stats)
    
    # ===== 論文格式的快速摘要 =====
    print_and_log("\n" + "="*80)
    print_and_log("=== 快速摘要（論文格式）===")
    print_and_log("="*80)
    
    # 檢測評估模型
    eval_model = None
    for p in preds:
        if 'autoeval_label' in p and 'model' in p['autoeval_label']:
            eval_model = p['autoeval_label']['model']
            break
    
    if eval_model:
        print_and_log(f"\n評估模型: {eval_model}")
    
    print_and_log("\n按任務類型的準確率:")
    task_accs = []
    for qtype in sorted(df['question_type'].unique()):
        type_df = df[df['question_type'] == qtype]
        acc = type_df['is_correct'].mean()
        count = len(type_df)
        task_accs.append(acc)
        print_and_log(f"  {qtype:30s}: {acc:.4f} ({count})")
    
    if task_accs:
        print_and_log(f"\nTask-averaged Accuracy: {np.mean(task_accs):.4f}")
    print_and_log(f"Overall Accuracy:       {df['is_correct'].mean():.4f}")
    
    # 檢查是否有 abstention 問題
    abstention_count = sum(1 for p in preds if '_abs' in p['question_id'])
    if abstention_count > 0:
        abstention_correct = sum(1 for p in preds if '_abs' in p['question_id'] and p.get('autoeval_label', {}).get('label', False))
        print_and_log(f"Abstention Accuracy:    {abstention_correct/abstention_count:.4f} ({abstention_count})")
    
    # ===== 詳細統計 =====
    print_and_log("\n" + "="*80)
    print_and_log("=== 詳細分析報告 ===")
    print_and_log("="*80)
    print_and_log(f"總樣本數: {len(df)}")
    print_and_log(f"平均準確率: {df['is_correct'].mean():.4f}")
    
    # ===== Recall 分析（如果有檢索結果）=====
    if retrieval_file and df['recall@10'].sum() > 0:
        print_and_log("\n" + "="*80)
        print_and_log("=== [1] Retrieval Recall 分析 ===")
        print_and_log("="*80)
        print_and_log(f"平均 Recall@5:  {df['recall@5'].mean():.4f}")
        print_and_log(f"平均 Recall@10: {df['recall@10'].mean():.4f}")
        print_and_log(f"平均 Recall@50: {df['recall@50'].mean():.4f}")
        
        # Recall 與準確率的關係
        print_and_log("\n[1.1] Recall@10 vs. 準確率")
        df['recall_bin'] = pd.cut(df['recall@10'], bins=[0, 0.5, 0.99, 1.0], 
                                   labels=['Low (<0.5)', 'Medium (0.5-0.99)', 'Perfect (1.0)'])
        recall_acc = df.groupby('recall_bin', observed=False)['is_correct'].agg(['mean', 'count'])
        print_and_log(recall_acc)
        
        # 錯誤歸因分析
        print_and_log("\n[1.2] 錯誤歸因分析（整體）")
        incorrect_df = df[df['is_correct'] == 0]
        retrieval_fail = len(incorrect_df[incorrect_df['recall@10'] < 1.0])
        reasoning_fail = len(incorrect_df[incorrect_df['recall@10'] == 1.0])
        print_and_log(f"檢索失敗 (Recall < 1.0): {retrieval_fail} / {len(incorrect_df)} ({retrieval_fail/len(incorrect_df)*100:.1f}%)")
        print_and_log(f"推理失敗 (Recall = 1.0): {reasoning_fail} / {len(incorrect_df)} ({reasoning_fail/len(incorrect_df)*100:.1f}%)")
        
        # 按問題類型分解的 Recall 和錯誤歸因
        print_and_log("\n[1.3] 按問題類型分解的 Recall 和錯誤歸因")
        type_recall_stats = []
        for qtype in sorted(df['question_type'].unique()):
            type_df = df[df['question_type'] == qtype]
            type_incorrect = type_df[type_df['is_correct'] == 0]
            
            avg_recall = type_df['recall@10'].mean()
            accuracy = type_df['is_correct'].mean()
            total_count = len(type_df)
            incorrect_count = len(type_incorrect)
            
            if incorrect_count > 0:
                retrieval_fail_count = len(type_incorrect[type_incorrect['recall@10'] < 1.0])
                reasoning_fail_count = len(type_incorrect[type_incorrect['recall@10'] == 1.0])
                retrieval_fail_pct = retrieval_fail_count / incorrect_count * 100
                reasoning_fail_pct = reasoning_fail_count / incorrect_count * 100
            else:
                retrieval_fail_count = 0
                reasoning_fail_count = 0
                retrieval_fail_pct = 0
                reasoning_fail_pct = 0
            
            type_recall_stats.append({
                'question_type': qtype,
                'count': total_count,
                'accuracy': accuracy,
                'avg_recall@10': avg_recall,
                'incorrect': incorrect_count,
                'retrieval_fail': retrieval_fail_count,
                'retrieval_fail_%': retrieval_fail_pct,
                'reasoning_fail': reasoning_fail_count,
                'reasoning_fail_%': reasoning_fail_pct
            })
        
        type_recall_df = pd.DataFrame(type_recall_stats)
        print_and_log("\n完整統計表：")
        print_and_log(str(type_recall_df.to_string(index=False)))
    
    # ===== 問題類型分析 =====
    print_and_log("\n" + "="*80)
    print_and_log("=== [2] 準確率 vs. 問題類型 ===")
    print_and_log("="*80)
    type_stats = df.groupby('question_type').agg({
        'is_correct': ['mean', 'count'],
        'recall@10': 'mean' if retrieval_file else lambda x: 0
    })
    print_and_log(type_stats)
    
    # ===== 位置分析（僅 Single-Evidence）=====
    print_and_log("\n" + "="*80)
    print_and_log("=== [3] 位置偏差分析（僅 Single-Evidence 樣本）===")
    print_and_log("="*80)
    
    single_evidence_df = df[df['evidence_count'] == 1].copy()
    print_and_log(f"Single-Evidence 樣本數: {len(single_evidence_df)} / {len(df)}")
    
    if len(single_evidence_df) > 0:
        # 使用 min_pos（對於單證據，min_pos = max_pos = avg_pos）
        single_evidence_df['pos_bin'] = pd.cut(
            single_evidence_df['evidence_pos_min'], 
            bins=5, 
            labels=['0-20% (Oldest)', '20-40%', '40-60%', '60-80%', '80-100% (Newest)']
        )
        
        pos_stats = single_evidence_df.groupby('pos_bin', observed=False).agg({
            'is_correct': ['mean', 'count'],
            'recall@10': 'mean' if retrieval_file else lambda x: 0
        })
        print_and_log("\n[3.1] 準確率 vs. Evidence 位置")
        print_and_log(pos_stats)
        
        # 繪製位置偏差圖
        plt.figure(figsize=(10, 6))
        pos_acc = single_evidence_df.groupby('pos_bin', observed=False)['is_correct'].mean()
        pos_acc.plot(kind='bar', color='steelblue')
        plt.title("Position Bias Analysis (Single-Evidence Only)")
        plt.xlabel("Evidence Position in Context")
        plt.ylabel("Accuracy")
        plt.ylim(0, 1.05)
        plt.xticks(rotation=45)
        plt.grid(True, axis='y', alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "position_bias_single_evidence.png"))
        print_and_log(f"\n✓ 圖表已儲存: {output_dir}/position_bias_single_evidence.png")
    
    # ===== Multi-Evidence 分析 =====
    print_and_log("\n" + "="*80)
    print_and_log("=== [4] Multi-Evidence 分析 ===")
    print_and_log("="*80)
    
    multi_evidence_df = df[df['evidence_count'] > 1].copy()
    print_and_log(f"Multi-Evidence 樣本數: {len(multi_evidence_df)} / {len(df)}")
    
    if len(multi_evidence_df) > 0:
        # 計算證據跨度
        multi_evidence_df['evidence_span'] = multi_evidence_df['evidence_pos_max'] - multi_evidence_df['evidence_pos_min']
        
        print_and_log("\n[4.1] 準確率 vs. Evidence 數量")
        count_stats = multi_evidence_df.groupby('evidence_count').agg({
            'is_correct': ['mean', 'count'],
            'evidence_span': 'mean'
        })
        print_and_log(count_stats)
        
        print_and_log("\n[4.2] 準確率 vs. Evidence 跨度")
        multi_evidence_df['span_bin'] = pd.cut(
            multi_evidence_df['evidence_span'],
            bins=3,
            labels=['Small (<0.33)', 'Medium (0.33-0.67)', 'Large (>0.67)']
        )
        span_stats = multi_evidence_df.groupby('span_bin', observed=False)['is_correct'].agg(['mean', 'count'])
        print_and_log(span_stats)
    
    # ===== Context Length 分析 =====
    print_and_log("\n" + "="*80)
    print_and_log("=== [5] Context Length 分析 ===")
    print_and_log("="*80)
    
    df['history_bin'] = pd.cut(
        df['history_len'],
        bins=[0, 50, 100, 150, 200],
        labels=['0-50', '50-100', '100-150', '150-200']
    )
    
    history_stats = df.groupby('history_bin', observed=False).agg({
        'is_correct': ['mean', 'count'],
        'recall@10': 'mean' if retrieval_file else lambda x: 0
    })
    print_and_log(history_stats)
    
    print_and_log("\n" + "="*80)
    print_and_log("分析完成！")
    print_and_log("="*80)
    
    # 保存 Markdown 報告
    report_file = os.path.join(output_dir, "analysis_report.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 實驗分析報告\n\n")
        f.write(f"**生成結果檔案**: `{os.path.basename(hypo_file)}`\n\n")
        f.write(f"**參考答案檔案**: `{os.path.basename(ref_file)}`\n\n")
        if retrieval_file:
            f.write(f"**檢索結果檔案**: `{os.path.basename(retrieval_file)}`\n\n")
        f.write("---\n\n")
        
        in_code_block = False
        for line in report_lines:
            # 將 DataFrame 等對象轉換為字符串
            line_str = str(line) if not isinstance(line, str) else line
            
            # 轉換為 Markdown 格式
            if line_str.startswith("==="):
                if in_code_block:
                    f.write("```\n\n")
                    in_code_block = False
                f.write("\n" + line_str.replace("=", "-") + "\n")
            elif line_str.startswith("["):
                if in_code_block:
                    f.write("```\n\n")
                    in_code_block = False
                f.write("\n### " + line_str + "\n\n")
            elif ("mean" in line_str and "count" in line_str) or ("question_type" in line_str and "is_correct" in line_str):
                # DataFrame 輸出，用代碼塊包裹
                if not in_code_block:
                    f.write("```\n")
                    in_code_block = True
                f.write(line_str + "\n")
            elif line_str.strip():
                if in_code_block and not any(keyword in line_str for keyword in ["===", "[", "✓", "Warning"]):
                    # DataFrame 的延續行
                    f.write(line_str + "\n")
                else:
                    if in_code_block:
                        f.write("```\n\n")
                        in_code_block = False
                    f.write(line_str + "\n")
            else:
                f.write("\n")
        
        if in_code_block:
            f.write("```\n")
    
    print(f"\n✓ 報告已儲存: {report_file}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="詳細分析實驗結果，包含 Recall、位置偏差、證據數量等")
    parser.add_argument('hypo_file', type=str, help="生成結果檔案 (.jsonl with autoeval_label)")
    parser.add_argument('ref_file', type=str, help="參考答案檔案 (.json)")
    parser.add_argument('--retrieval', type=str, help="檢索結果檔案（可選，用於計算 Recall）")
    parser.add_argument('--output-dir', type=str, default="analysis_results", help="圖表輸出目錄")
    
    args = parser.parse_args()
    
    analyze(args.hypo_file, args.ref_file, args.retrieval, args.output_dir)
