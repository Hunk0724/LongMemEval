import sys
import json
import argparse
import os


def export_error_cases(eval_file, generation_file, ref_file, retrieval_file=None, output_file=None):
    """
    匯出答錯的題目詳細資訊，方便後續分析
    
    Args:
        eval_file: 評估結果檔案 (.eval-results)
        generation_file: 生成檔案 (包含 hypothesis 和 tokens)
        ref_file: 參考答案檔案
        retrieval_file: 檢索結果檔案（可選）
        output_file: 輸出檔案路徑
    """
    # 載入資料
    print(f"載入評估結果: {eval_file}")
    eval_data = [json.loads(line) for line in open(eval_file)]
    eval_map = {x['question_id']: x for x in eval_data}
    
    print(f"載入生成結果: {generation_file}")
    gen_data = [json.loads(line) for line in open(generation_file)]
    gen_map = {x['question_id']: x for x in gen_data}
    
    print(f"載入參考答案: {ref_file}")
    ref_data = json.load(open(ref_file))
    ref_map = {x['question_id']: x for x in ref_data}
    
    # 載入檢索結果（如果有）
    retrieval_map = {}
    if retrieval_file:
        print(f"載入檢索結果: {retrieval_file}")
        try:
            retrieval_data = [json.loads(line) for line in open(retrieval_file)]
            retrieval_map = {x['question_id']: x for x in retrieval_data}
        except:
            print(f"Warning: 無法載入檢索結果檔案")
    
    # 收集錯誤案例
    error_cases = []
    correct_cases = []
    
    for qid, eval_entry in eval_map.items():
        if qid not in ref_map or qid not in gen_map:
            continue
        
        ref = ref_map[qid]
        gen = gen_map[qid]
        
        is_correct = eval_entry.get('autoeval_label', {}).get('label', False)
        
        # 構建詳細資訊
        case_info = {
            'question_id': qid,
            'question_type': ref['question_type'],
            'is_correct': is_correct,
            
            # 問題資訊
            'question': ref['question'],
            'question_date': ref.get('question_date', 'N/A'),
            'correct_answer': ref['answer'],
            
            # 生成資訊
            'llm_output': gen['hypothesis'],
            'prompt': gen.get('prompt', None),  # 完整的 prompt（如果有）
            
            # Tokens 資訊
            'prompt_tokens': None,
            'completion_tokens': None,
            'total_tokens': None,
            
            # 證據資訊
            'answer_session_ids': ref['answer_session_ids'],
            'haystack_session_ids': ref.get('haystack_session_ids', []),
            'evidence_count': len(ref['answer_session_ids']),
            
            # 評估資訊
            'eval_model': eval_entry.get('autoeval_label', {}).get('model', 'N/A'),
            'eval_reasoning': eval_entry.get('autoeval_label', {}).get('reason', 'N/A')
        }
        
        # 提取 tokens 資訊
        if 'tokens' in gen:
            case_info['prompt_tokens'] = gen['tokens'].get('prompt_token_count', 
                                         gen['tokens'].get('prompt_tokens'))
            case_info['completion_tokens'] = gen['tokens'].get('completion_tokens')
            case_info['total_tokens'] = gen['tokens'].get('total_tokens')
        elif 'usage' in gen:
            case_info['prompt_tokens'] = gen['usage'].get('prompt_tokens')
            case_info['completion_tokens'] = gen['usage'].get('completion_tokens')
            case_info['total_tokens'] = gen['usage'].get('total_tokens')
        
        # 檢索資訊（如果有）
        if qid in retrieval_map:
            ret = retrieval_map[qid]
            retrieval_results = ret.get('retrieval_results', {})
            ranked_items = retrieval_results.get('ranked_items', [])
            
            # 提取 session_id 的函數
            def get_session_id(corpus_id):
                # 處理 turn-level corpus_id (例如: answer_xxx_1 -> answer_xxx)
                parts = corpus_id.replace('noans_', 'answer_').rsplit('_', 1)
                return parts[0] if len(parts) > 1 else corpus_id
            
            # 分析檢索結果
            answer_session_ids = set(ref['answer_session_ids'])
            top50_items = ranked_items[:50]
            
            # 找出哪些 evidence 被檢索到
            retrieved_evidence = set()
            evidence_positions = {}  # evidence -> 第一次出現的位置
            
            for i, item in enumerate(top50_items, 1):
                corpus_id = item['corpus_id']
                session_id = get_session_id(corpus_id)
                
                if session_id in answer_session_ids:
                    retrieved_evidence.add(session_id)
                    if session_id not in evidence_positions:
                        evidence_positions[session_id] = i
            
            # 找出哪些 evidence 沒被檢索到
            missing_evidence = answer_session_ids - retrieved_evidence
            
            case_info['retrieval_analysis'] = {
                'query': retrieval_results.get('query', 'N/A'),
                'total_evidence_count': len(answer_session_ids),
                'retrieved_evidence_count': len(retrieved_evidence),
                'missing_evidence_count': len(missing_evidence),
                'recall@50': len(retrieved_evidence) / len(answer_session_ids) if answer_session_ids else 0,
                
                # 詳細的 evidence 資訊
                'all_evidence_ids': list(answer_session_ids),
                'retrieved_evidence_ids': list(retrieved_evidence),
                'missing_evidence_ids': list(missing_evidence),
                'evidence_positions': evidence_positions,  # 每個 evidence 在 Top-50 中的位置
                
                # Top-10 檢索結果（標註是否為 evidence）
                'top10_results': [
                    {
                        'rank': i,
                        'corpus_id': item['corpus_id'],
                        'session_id': get_session_id(item['corpus_id']),
                        'is_evidence': get_session_id(item['corpus_id']) in answer_session_ids,
                        'text_preview': item['text'][:200] + '...' if len(item['text']) > 200 else item['text']
                    }
                    for i, item in enumerate(ranked_items[:10], 1)
                ]
            }
        
        # 分類
        if is_correct:
            correct_cases.append(case_info)
        else:
            error_cases.append(case_info)
    
    # 按問題類型分組錯誤案例
    error_by_type = {}
    for case in error_cases:
        qtype = case['question_type']
        if qtype not in error_by_type:
            error_by_type[qtype] = []
        error_by_type[qtype].append(case)
    
    # 生成輸出檔案名稱
    if output_file is None:
        base_name = os.path.splitext(eval_file)[0]
        output_file = base_name + '.error_analysis.jsonl'
    
    # 寫入錯誤案例
    print(f"\n寫入錯誤案例到: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        for case in error_cases:
            f.write(json.dumps(case, ensure_ascii=False) + '\n')
    
    # 生成摘要報告
    summary_file = output_file.replace('.jsonl', '_summary.md')
    print(f"寫入摘要報告到: {summary_file}")
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("# 錯誤案例分析摘要\n\n")
        
        f.write("## 整體統計\n\n")
        f.write(f"- **總題數**: {len(error_cases) + len(correct_cases)}\n")
        f.write(f"- **答對**: {len(correct_cases)} ({len(correct_cases)/(len(error_cases)+len(correct_cases))*100:.1f}%)\n")
        f.write(f"- **答錯**: {len(error_cases)} ({len(error_cases)/(len(error_cases)+len(correct_cases))*100:.1f}%)\n\n")
        
        f.write("## 按問題類型的錯誤數量\n\n")
        f.write("| 問題類型 | 錯誤數量 |\n")
        f.write("|---------|----------|\n")
        for qtype in sorted(error_by_type.keys()):
            f.write(f"| {qtype} | {len(error_by_type[qtype])} |\n")
        f.write("\n")
        
        f.write("---\n\n")
        f.write("## 按問題類型分組的錯誤案例詳細資訊\n\n")
        
        for qtype in sorted(error_by_type.keys()):
            cases = error_by_type[qtype]
            f.write(f"\n### {qtype}\n\n")
            f.write(f"**錯誤數量**: {len(cases)}\n\n")
            
            # 計算平均 tokens
            tokens_list = [c['prompt_tokens'] for c in cases if c['prompt_tokens'] is not None]
            if tokens_list:
                avg_tokens = sum(tokens_list) / len(tokens_list)
                f.write(f"**平均 Prompt Tokens**: {avg_tokens:.0f}\n\n")
            
            f.write("#### 錯誤案例 Question IDs\n\n")
            for i, case in enumerate(cases, 1):
                tokens_info = f" `({case['prompt_tokens']} tokens)`" if case['prompt_tokens'] else ""
                f.write(f"{i}. `{case['question_id']}`{tokens_info}\n")
            
            # 列出前 3 個案例的詳細資訊
            f.write(f"\n#### 前 3 個案例詳細資訊\n\n")
            for i, case in enumerate(cases[:3], 1):
                f.write(f"**案例 {i}: `{case['question_id']}`**\n\n")
                f.write(f"- **問題**: {case['question']}\n")
                f.write(f"- **正確答案**: {case['correct_answer']}\n")
                f.write(f"- **證據數量**: {case['evidence_count']}\n")
                
                # 檢索分析（如果有）
                if 'retrieval_analysis' in case:
                    ret_analysis = case['retrieval_analysis']
                    f.write(f"- **檢索 Recall@50**: {ret_analysis['recall@50']:.2%} ({ret_analysis['retrieved_evidence_count']}/{ret_analysis['total_evidence_count']})\n")
                    
                    if ret_analysis['retrieved_evidence_ids']:
                        f.write(f"- **已檢索到的證據**: ")
                        for eid in ret_analysis['retrieved_evidence_ids']:
                            pos = ret_analysis['evidence_positions'].get(eid, '?')
                            f.write(f"`{eid}` (rank {pos}), ")
                        f.write("\n")
                    
                    if ret_analysis['missing_evidence_ids']:
                        f.write(f"- **未檢索到的證據**: ")
                        for eid in ret_analysis['missing_evidence_ids']:
                            f.write(f"`{eid}`, ")
                        f.write("\n")
                
                llm_output = case['llm_output'][:200] + '...' if len(case['llm_output']) > 200 else case['llm_output']
                f.write(f"- **LLM 輸出**: {llm_output}\n")
                
                if case['prompt_tokens']:
                    f.write(f"- **Prompt Tokens**: {case['prompt_tokens']}\n")
                
                # 顯示 prompt 的前 500 字元（如果有）
                if case.get('prompt'):
                    prompt_preview = case['prompt'][:500] + '...' if len(case['prompt']) > 500 else case['prompt']
                    f.write(f"- **Prompt 預覽**:\n```\n{prompt_preview}\n```\n")
                
                eval_reasoning = case['eval_reasoning'][:200] + '...' if len(case['eval_reasoning']) > 200 else case['eval_reasoning']
                f.write(f"- **評估理由**: {eval_reasoning}\n")
                f.write("\n---\n")
    
    print(f"\n✓ 完成！")
    print(f"  - 錯誤案例詳細資訊: {output_file}")
    print(f"  - 摘要報告: {summary_file}")
    print(f"\n統計:")
    print(f"  總題數: {len(error_cases) + len(correct_cases)}")
    print(f"  答對: {len(correct_cases)}")
    print(f"  答錯: {len(error_cases)}")
    print(f"\n按問題類型的錯誤數量:")
    for qtype in sorted(error_by_type.keys()):
        print(f"  {qtype:30s}: {len(error_by_type[qtype]):3d} 錯誤")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="匯出答錯的題目詳細資訊")
    parser.add_argument('eval_file', type=str, help="評估結果檔案 (.eval-results)")
    parser.add_argument('generation_file', type=str, help="生成檔案 (包含 hypothesis 和 tokens)")
    parser.add_argument('ref_file', type=str, help="參考答案檔案 (.json)")
    parser.add_argument('--retrieval', type=str, help="檢索結果檔案（可選）")
    parser.add_argument('--output', type=str, help="輸出檔案路徑（預設為 eval_file.error_analysis.jsonl）")
    
    args = parser.parse_args()
    
    export_error_cases(args.eval_file, args.generation_file, args.ref_file, 
                      args.retrieval, args.output)

