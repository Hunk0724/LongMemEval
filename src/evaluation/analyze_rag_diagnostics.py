import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import os


def load_retrieval_log(file_path):
    """讀取檢索 Log，計算 Recall。"""
    retrieval_data = {}
    with open(file_path, 'r') as f:
        for line in f:
            entry = json.loads(line)
            qid = entry['question_id']

            # 取得正確答案的 session ids（若 retrieval log 內無此欄，需改為從 ref 讀）
            target_ids = set(entry['answer_session_ids'])

            # 取得檢索到的 ids
            ranked_items = entry['retrieval_results']['ranked_items']
            retrieved_ids = [x['corpus_id'] for x in ranked_items]

            # turn 粒度時，移除 _<turnid> 後綴回到 session 粒度
            retrieved_sessions = set()
            for rid in retrieved_ids:
                if '_answer_' in rid:
                    base_id = rid
                else:
                    base_id = rid.rsplit('_', 1)[0] if rid[-1].isdigit() else rid
                retrieved_sessions.add(base_id)

            # 計算 Recall（模糊比對：target 字串有被任一 retrieved 覆蓋即可）
            hits = 0
            for tid in target_ids:
                if any(tid in r for r in retrieved_ids):
                    hits += 1

            recall = hits / len(target_ids) if target_ids else 0

            retrieval_data[qid] = {
                'recall': recall,
                'retrieved_count': len(retrieved_ids),
                'target_count': len(target_ids)
            }
    return retrieval_data


def load_generation_log(file_path):
    """讀取生成 Log，取得評分結果。"""
    gen_data = {}
    with open(file_path, 'r') as f:
        for line in f:
            entry = json.loads(line)
            qid = entry['question_id']
            is_correct = 1 if entry.get('autoeval_label', {}).get('label', False) else 0
            gen_data[qid] = {'is_correct': is_correct}
    return gen_data


def analyze(retrieval_file, generation_file, ref_file, output_dir):
    print("Loading data...")
    ref_data = json.load(open(ref_file))
    ref_map = {x['question_id']: x for x in ref_data}

    ret_data = load_retrieval_log(retrieval_file)
    gen_data = load_generation_log(generation_file)

    combined = []
    for qid, ref in ref_map.items():
        if qid not in ret_data or qid not in gen_data:
            continue

        r_info = ret_data[qid]
        g_info = gen_data[qid]

        # 計算 Evidence 位置（後續只針對 Single-Session 使用）
        haystack = ref['haystack_session_ids']
        evidence = ref['answer_session_ids']
        indices = [i for i, h in enumerate(haystack) if h in evidence]

        if not indices:
            pos = -1
        else:
            pos = np.mean(indices) / len(haystack)

        combined.append({
            'question_id': qid,
            'type': ref['question_type'],
            'recall': r_info['recall'],
            'is_correct': g_info['is_correct'],
            'pos': pos,
            'evidence_count': len(evidence)
        })

    df = pd.DataFrame(combined)
    os.makedirs(output_dir, exist_ok=True)

    # === 分析 1: Retrieval Recall 表現 ===
    print("\n[1] Average Recall by Task Type:")
    print(df.groupby('type')['recall'].mean())

    # === 分析 2: 錯誤歸因 (Retrieval vs Reasoning) ===
    def classify_error(row):
        if row['is_correct'] == 1:
            return 'Correct'
        if row['recall'] < 1.0:
            return 'Retrieval Fail'
        return 'Reasoning Fail'

    df['error_type'] = df.apply(classify_error, axis=1)

    plt.figure(figsize=(10, 6))
    sns.countplot(data=df, y='type', hue='error_type')
    plt.title("Error Analysis: Retrieval vs. Reasoning")
    plt.tight_layout()
    plt.savefig(f"{output_dir}/error_analysis.png")

    print("\n[2] Error Distribution (Count):")
    print(df.groupby(['type', 'error_type']).size().unstack(fill_value=0))

    # === 分析 3: 修正後的位置分析 (僅 Single Session) ===
    single_session_df = df[df['type'].str.contains('single-session')]
    if not single_session_df.empty:
        single_session_df['pos_bin'] = pd.cut(single_session_df['pos'], bins=5, labels=['0-20%', '20-40%', '40-60%', '60-80%', '80-100%'])

        plt.figure(figsize=(8, 5))
        # 只看 Recall=1.0 的案例，避免檢索缺失干擾位置分析
        perfect_retrieval_df = single_session_df[single_session_df['recall'] == 1.0]

        if not perfect_retrieval_df.empty:
            sns.barplot(data=perfect_retrieval_df, x='pos_bin', y='is_correct', palette="viridis")
            plt.title("Position Bias (Only Perfect Retrieval Cases in Single-Session)")
            plt.ylim(0, 1)
            plt.savefig(f"{output_dir}/position_bias_clean.png")
            print("\n[3] Clean Position Bias (Accuracy when Recall=1.0):")
            print(perfect_retrieval_df.groupby('pos_bin', observed=False)['is_correct'].mean())
        else:
            print("\n[Info] Not enough perfect retrieval cases for position analysis.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--retrieval_log', required=True, help="Path to retrieval output jsonl")
    parser.add_argument('--generation_log', required=True, help="Path to generation output jsonl")
    parser.add_argument('--ref_file', required=True, help="Original dataset file")
    parser.add_argument('--output_dir', default="analysis_results")
    args = parser.parse_args()

    analyze(args.retrieval_log, args.generation_log, args.ref_file, args.output_dir)

