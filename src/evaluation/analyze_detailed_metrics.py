import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def analyze(hypo_file, ref_file):
    # 載入預測結果與原始資料
    try:
        preds = [json.loads(line) for line in open(hypo_file)]
    except:
        print(f"Error loading {hypo_file}")
        return
    ref_data = json.load(open(ref_file))
    ref_map = {x['question_id']: x for x in ref_data}
    stats = []
    for p in preds:
        qid = p['question_id']
        if qid not in ref_map: continue
        
        ref = ref_map[qid]
        
        # 1. 取得評分結果 (Yes/No)
        is_correct = 1 if p.get('autoeval_label', {}).get('label', False) else 0
        
        # 2. 計算 Evidence 的位置 (Position)
        # 我們將位置正規化為 0.0 (最舊) ~ 1.0 (最新)
        haystack_ids = ref['haystack_session_ids']
        evidence_ids = ref['answer_session_ids']
        
        evidence_indices = [i for i, sess_id in enumerate(haystack_ids) if sess_id in evidence_ids]
        
        if not evidence_indices:
            avg_pos = -1 # 異常
        else:
            avg_pos = np.mean(evidence_indices) / len(haystack_ids)
        # 3. 計算歷史長度 (Session Count)
        history_len = len(haystack_ids)
        
        # 4. 計算 Evidence 數量 (跨多少 Session)
        evidence_count = len(evidence_indices)
        stats.append({
            'question_type': ref['question_type'],
            'is_correct': is_correct,
            'evidence_pos_norm': avg_pos, # 0~1, 1代表最近
            'evidence_count': evidence_count,
            'history_len': history_len
        })
    df = pd.DataFrame(stats)
    
    print("=== 整體分析報告 ===")
    print(f"總樣本數: {len(df)}")
    print(f"平均準確率: {df['is_correct'].mean():.4f}")
    
    print("\n[1] 準確率 vs. 問題類型")
    print(df.groupby('question_type')['is_correct'].mean())
    print("\n[2] 準確率 vs. Evidence 位置 (分位數)")
    # 將位置分為 5 等份 (0-0.2, 0.2-0.4...)
    df['pos_bin'] = pd.cut(df['evidence_pos_norm'], bins=5, labels=['0-20% (Oldest)', '20-40%', '40-60%', '60-80%', '80-100% (Newest)'])
    print(df.groupby('pos_bin')['is_correct'].mean())
    print("\n[3] 準確率 vs. Evidence 數量 (跨 Session 數)")
    print(df.groupby('evidence_count')['is_correct'].mean())
    # 如果需要畫圖，可以在這裡呼叫 matplotlib
    # sns.barplot(data=df, x='pos_bin', y='is_correct')
    # plt.title("Accuracy by Evidence Position")
    # plt.savefig("pos_analysis.png")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python analyze_detailed_metrics.py <hypo_file.jsonl> <ref_file.json>")
        exit(1)
    analyze(sys.argv[1], sys.argv[2])

