import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import os


def load_data(file_path, ref_map):
    data = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                entry = json.loads(line)
                qid = entry['question_id']
                if qid not in ref_map:
                    continue

                ref = ref_map[qid]

                # 判斷是否正確
                is_correct = 1 if entry.get('autoeval_label', {}).get('label', False) else 0

                # 取得 Token 消耗 (如果有)
                tokens = entry.get('usage', {}).get('total_tokens', np.nan)

                # 計算 Evidence 位置
                haystack_ids = ref['haystack_session_ids']
                evidence_ids = ref['answer_session_ids']
                evidence_indices = [i for i, sess_id in enumerate(haystack_ids) if sess_id in evidence_ids]

                if not evidence_indices:
                    avg_pos = -1
                else:
                    avg_pos = np.mean(evidence_indices) / len(haystack_ids) if len(haystack_ids) > 0 else 0

                data.append({
                    'question_id': qid,
                    'question_type': ref['question_type'],
                    'is_correct': is_correct,
                    'tokens': tokens,
                    'evidence_pos_norm': avg_pos,
                    'evidence_count': len(evidence_indices)
                })
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
    return pd.DataFrame(data)


def main():
    parser = argparse.ArgumentParser(description="比較多個實驗結果並繪製圖表")
    parser.add_argument('--ref', type=str, required=True, help="參考答案檔 (如 longmemeval_s_cleaned.json)")
    parser.add_argument('--inputs', nargs='+', required=True, help='輸入檔案，格式為 Label:FilePath (例如 Oracle:log1.jsonl RAG:log2.jsonl)')
    parser.add_argument('--output_dir', type=str, default=".", help="圖表輸出目錄")
    args = parser.parse_args()

    # 載入 Reference
    print(f"Loading reference from {args.ref}...")
    ref_data = json.load(open(args.ref))
    ref_map = {x['question_id']: x for x in ref_data}

    all_dfs = []

    for item in args.inputs:
        label, path = item.split(':', 1)
        print(f"Processing {label} from {path}...")
        df = load_data(path, ref_map)
        df['Experiment'] = label
        all_dfs.append(df)

    if not all_dfs:
        print("No data loaded.")
        return

    full_df = pd.concat(all_dfs)

    # 設定繪圖風格
    sns.set_theme(style="whitegrid")

    # 1. 總體準確率比較
    plt.figure(figsize=(8, 5))
    overall_acc = full_df.groupby('Experiment')['is_correct'].mean().reset_index()
    sns.barplot(data=overall_acc, x='Experiment', y='is_correct', palette="viridis")
    plt.title("Overall Accuracy Comparison")
    plt.ylim(0, 1)
    plt.savefig(os.path.join(args.output_dir, "cmp_overall_acc.png"))
    print("\n=== Overall Accuracy ===")
    print(overall_acc)

    # 2. 各任務類型準確率比較 (Grouped Bar Chart)
    plt.figure(figsize=(12, 6))
    task_acc = full_df.groupby(['Experiment', 'question_type'])['is_correct'].mean().reset_index()
    sns.barplot(data=task_acc, x='question_type', y='is_correct', hue='Experiment', palette="viridis")
    plt.title("Accuracy by Task Type")
    plt.xticks(rotation=45)
    plt.ylim(0, 1)
    plt.tight_layout()
    plt.savefig(os.path.join(args.output_dir, "cmp_task_acc.png"))

    # 3. Evidence 位置分析 (Line Chart)
    full_df['pos_bin'] = pd.cut(full_df['evidence_pos_norm'], bins=5, labels=['0-20%', '20-40%', '40-60%', '60-80%', '80-100%'])
    pos_acc = full_df.groupby(['Experiment', 'pos_bin'], observed=False)['is_correct'].mean().reset_index()

    plt.figure(figsize=(10, 6))
    sns.lineplot(data=pos_acc, x='pos_bin', y='is_correct', hue='Experiment', marker='o')
    plt.title("Accuracy vs. Evidence Position (Oldest -> Newest)")
    plt.ylim(0, 1)
    plt.savefig(os.path.join(args.output_dir, "cmp_pos_acc.png"))

    # 4. Token 消耗比較 (如果有數據)
    if full_df['tokens'].notna().sum() > 0:
        plt.figure(figsize=(8, 5))
        sns.boxplot(data=full_df, x='Experiment', y='tokens', palette="viridis")
        plt.title("Token Usage Distribution")
        plt.savefig(os.path.join(args.output_dir, "cmp_tokens.png"))
        print("\n=== Avg Token Usage ===")
        print(full_df.groupby('Experiment')['tokens'].mean())
    else:
        print("\n[Info] No token usage data found in logs.")

    print(f"\nPlots saved to {args.output_dir}")


if __name__ == '__main__':
    main()

