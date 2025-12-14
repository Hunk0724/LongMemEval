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
    # 準備 Markdown 報告
    report_lines = []
    def print_and_log(text=""):
        """同時輸出到終端和記錄到報告"""
        print(text)
        report_lines.append(text)
    

    os.makedirs(args.output_dir, exist_ok=True)

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
    if full_df.empty:
        print("No valid rows loaded (question_id 未對到 ref？).")
        return

    # 設定繪圖風格
    sns.set_theme(style="whitegrid")

    # 1. 總體準確率比較
    plt.figure(figsize=(8, 5))
    overall_acc = full_df.groupby('Experiment')['is_correct'].mean().reset_index()
    ax = sns.barplot(data=overall_acc, x='Experiment', y='is_correct', palette="viridis")
    plt.title("Overall Accuracy Comparison")
    plt.ylim(0, 1.05)
    # Add value labels on bars
    for container in ax.containers:
        ax.bar_label(container, fmt='%.3f', padding=3)
    plt.savefig(os.path.join(args.output_dir, "cmp_overall_acc.png"))
    print_and_log("\n=== Overall Accuracy ===")
    print_and_log(str(overall_acc))

    # 2. 各任務類型準確率比較 (Grouped Bar Chart)
    plt.figure(figsize=(12, 6))
    task_acc = full_df.groupby(['Experiment', 'question_type'])['is_correct'].mean().reset_index()
    ax = sns.barplot(data=task_acc, x='question_type', y='is_correct', hue='Experiment', palette="viridis")
    plt.title("Accuracy by Task Type")
    plt.xticks(rotation=45)
    plt.ylim(0, 1.05)
    # Add value labels on bars
    for container in ax.containers:
        ax.bar_label(container, fmt='%.3f', padding=3, fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(args.output_dir, "cmp_task_acc.png"))
    
    print_and_log("\n=== [2] Task Type Analysis ===")
    print_and_log("\n[2.1] Sample Count:")
    print_and_log(str(full_df.groupby(['Experiment', 'question_type']).size().unstack(fill_value=0)))
    print_and_log("\n[2.2] Accuracy:")
    print_and_log(str(task_acc.pivot(index='question_type', columns='Experiment', values='is_correct')))

    # 3. Evidence 位置分析 (Line Chart) - 僅看 evidence_count == 1，避免多證據平均值的誤導
    clean_pos_df = full_df[full_df['evidence_count'] == 1].copy()

    if not clean_pos_df.empty:
        clean_pos_df['pos_bin'] = pd.cut(
            clean_pos_df['evidence_pos_norm'],
            bins=5,
            labels=['0-20%', '20-40%', '40-60%', '60-80%', '80-100%']
        )
        pos_acc = clean_pos_df.groupby(['Experiment', 'pos_bin'], observed=False)['is_correct'].mean().reset_index()

        plt.figure(figsize=(10, 6))
        sns.lineplot(data=pos_acc, x='pos_bin', y='is_correct', hue='Experiment', marker='o', linewidth=2.5)
        plt.title("Position Bias Analysis (Strictly Single-Evidence Cases Only)")
        plt.xlabel("Evidence Position in Context (Oldest -> Newest)")
        plt.ylabel("Accuracy")
        plt.ylim(0, 1.05)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig(os.path.join(args.output_dir, "cmp_pos_acc.png"))
        print_and_log("\n=== [3] Position Bias Analysis (Single-Evidence Only) ===")
        print_and_log(f"\nAnalyzed samples: {len(clean_pos_df)} / {len(full_df)}")
        print_and_log("\n[3.1] Question Type Breakdown:")
        print_and_log(str(clean_pos_df.groupby(['Experiment', 'question_type']).size().unstack(fill_value=0)))
        print_and_log("\n[3.2] Accuracy by Position Bin:")
        print_and_log(str(pos_acc.pivot(index='pos_bin', columns='Experiment', values='is_correct')))
    else:
        print_and_log("\n[Warning] No single-evidence data found for position analysis.")

    # 4. Token 消耗比較 (如果有數據)
    if full_df['tokens'].notna().sum() > 0:
        plt.figure(figsize=(8, 5))
        sns.boxplot(data=full_df, x='Experiment', y='tokens', palette="viridis")
        plt.title("Token Usage Distribution")
        plt.savefig(os.path.join(args.output_dir, "cmp_tokens.png"))
        print_and_log("\n=== [4] Token Usage Analysis ===")
        print_and_log(str(full_df.groupby('Experiment')['tokens'].mean()))
    else:
        print_and_log("\n[Info] No token usage data found in logs.")

    print(f"\nPlots saved to {args.output_dir}")

    # 保存 Markdown 報告
    report_file = os.path.join(args.output_dir, "comparison_report.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 實驗比較報告\n\n")
        f.write(f"**參考答案檔案**: `{os.path.basename(args.ref)}`\n\n")
        f.write("**實驗列表**:\n\n")
        for item in args.inputs:
            label, path = item.split(':', 1)
            f.write(f"- **{label}**: `{os.path.basename(path)}`\n")
        f.write("\n---\n\n")
        
        in_code_block = False
        prev_was_header = False
        
        for i, line in enumerate(report_lines):
            line_str = str(line) if not isinstance(line, str) else line
            
            # 檢查是否是標題行
            is_header = line_str.startswith("===") or line_str.startswith("[")
            
            # 檢查是否是 DataFrame 表格
            is_dataframe = (
                ("Experiment" in line_str or "question_type" in line_str or "pos_bin" in line_str) 
                and any(keyword in line_str for keyword in ["is_correct", "mean", "count", "tokens"])
            ) or (in_code_block and line_str.strip() and not is_header and not line_str.startswith("✓") and not line_str.startswith("Analyzed"))
            
            if line_str.startswith("==="):
                if in_code_block:
                    f.write("```\n\n")
                    in_code_block = False
                # 提取標題文字
                title = line_str.replace("===", "").replace("---", "").strip()
                if title:
                    f.write(f"\n## {title}\n\n")
                prev_was_header = True
                
            elif line_str.startswith("["):
                if in_code_block:
                    f.write("```\n\n")
                    in_code_block = False
                f.write(f"### {line_str}\n\n")
                prev_was_header = True
                
            elif is_dataframe:
                # DataFrame 輸出，用代碼塊包裹
                if not in_code_block:
                    f.write("```\n")
                    in_code_block = True
                f.write(line_str + "\n")
                prev_was_header = False
                
            elif line_str.startswith("✓"):
                if in_code_block:
                    f.write("```\n\n")
                    in_code_block = False
                f.write(f"\n{line_str}\n")
                prev_was_header = False
                
            elif line_str.strip():
                if in_code_block:
                    f.write("```\n\n")
                    in_code_block = False
                f.write(line_str + "\n")
                prev_was_header = False
            else:
                if not in_code_block and not prev_was_header:
                    f.write("\n")
        
        if in_code_block:
            f.write("```\n")
    
    print(f"\n✓ 報告已儲存: {report_file}")


if __name__ == '__main__':
    main()

