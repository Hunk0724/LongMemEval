import os
import sys
import json
from tqdm import tqdm
import backoff
import openai
import numpy as np


model_zoo = {
    'llama-3.1-70b-instruct': ('meta-llama/Meta-Llama-3.1-70B-Instruct', 'local'),
    'gpt-4o-mini': ('gpt-4o-mini-2024-07-18', 'openai'),
    'gpt-4o': ('gpt-4o-2024-08-06', 'openai'),
}


@backoff.on_exception(backoff.expo, (openai.error.RateLimitError,
                                    openai.error.APIError))
def chat_completions_with_backoff(**kwargs):
    return openai.ChatCompletion.create(**kwargs)


def get_anscheck_prompt(task, question, answer, response, abstention=False):
    if not abstention:
        if task in ['single-session-user', 'single-session-assistant', 'multi-session']:
            template = "I will give you a question, a correct answer, and a response from a model. Please answer yes if the response contains the correct answer. Otherwise, answer no. If the response is equivalent to the correct answer or contains all the intermediate steps to get the correct answer, you should also answer yes. If the response only contains a subset of the information required by the answer, answer no. \n\nQuestion: {}\n\nCorrect Answer: {}\n\nModel Response: {}\n\nIs the model response correct? Answer yes or no only."
            prompt = template.format(question, answer, response)
        elif task == 'temporal-reasoning':
            template = "I will give you a question, a correct answer, and a response from a model. Please answer yes if the response contains the correct answer. Otherwise, answer no. If the response is equivalent to the correct answer or contains all the intermediate steps to get the correct answer, you should also answer yes. If the response only contains a subset of the information required by the answer, answer no. In addition, do not penalize off-by-one errors for the number of days. If the question asks for the number of days/weeks/months, etc., and the model makes off-by-one errors (e.g., predicting 19 days when the answer is 18), the model's response is still correct. \n\nQuestion: {}\n\nCorrect Answer: {}\n\nModel Response: {}\n\nIs the model response correct? Answer yes or no only."
            prompt = template.format(question, answer, response)
        elif task == 'knowledge-update':
            template = "I will give you a question, a correct answer, and a response from a model. Please answer yes if the response contains the correct answer. Otherwise, answer no. If the response contains some previous information along with an updated answer, the response should be considered as correct as long as the updated answer is the required answer.\n\nQuestion: {}\n\nCorrect Answer: {}\n\nModel Response: {}\n\nIs the model response correct? Answer yes or no only."
            prompt = template.format(question, answer, response)
        elif task == 'single-session-preference':
            template = "I will give you a question, a rubric for desired personalized response, and a response from a model. Please answer yes if the response satisfies the desired response. Otherwise, answer no. The model does not need to reflect all the points in the rubric. The response is correct as long as it recalls and utilizes the user's personal information correctly.\n\nQuestion: {}\n\nRubric: {}\n\nModel Response: {}\n\nIs the model response correct? Answer yes or no only."
            prompt = template.format(question, answer, response)
        else:
            raise NotImplementedError
    else:
        template = "I will give you an unanswerable question, an explanation, and a response from a model. Please answer yes if the model correctly identifies the question as unanswerable. The model could say that the information is incomplete, or some other information is given but the asked information is not.\n\nQuestion: {}\n\nExplanation: {}\n\nModel Response: {}\n\nDoes the model correctly identify the question as unanswerable? Answer yes or no only."
        prompt = template.format(question, answer, response) 
    return prompt


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('Usage: python evaluate_qa.py metric_model hyp_file ref_file')
        exit()

    metric_model_short = sys.argv[1]
    hyp_file = sys.argv[2]
    ref_file = sys.argv[3]
    verbose = True
    
    result_file = hyp_file + '.eval-results-{}'.format(metric_model_short)

    if metric_model_short not in model_zoo:
        print('Requested metric model is not supported:', metric_model_short)
        exit()
    metric_model, metric_model_source = model_zoo[metric_model_short]
    if metric_model_source == 'openai':
        openai.organization = os.getenv('OPENAI_ORGANIZATION')
        openai.api_key = os.getenv('OPENAI_API_KEY')
    else:
        openai.api_key = "EMPTY"
        openai.api_base = "http://localhost:8001/v1"

    try:
        hypotheses = [json.loads(line) for line in open(hyp_file).readlines()]
    except:
        hypotheses = json.load(open(hyp_file))
    try:
        references = json.load(open(ref_file))
    except:
        references = [json.loads(line) for line in open(ref_file).readlines()]
    qid2qdata = {entry['question_id']: entry for entry in references}
    qid2qtype = {entry['question_id']: entry['question_type'] for entry in references}
    qtypes = set(list(qid2qtype.values()))
    qtype2acc = {t: [] for t in qtypes}

    # 斷點續傳：檢查已處理的問題
    processed_question_ids = set()
    if os.path.exists(result_file):
        print(f"發現已存在的評估結果檔案: {result_file}")
        print("正在讀取已處理的問題...")
        try:
            with open(result_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if 'question_id' in entry:
                            processed_question_ids.add(entry['question_id'])
                            # 如果已有評估結果，也記錄到 qtype2acc
                            if entry.get('autoeval_label', {}).get('label'):
                                qtype = qid2qtype.get(entry['question_id'])
                                if qtype:
                                    qtype2acc[qtype].append(1)
                            else:
                                qtype = qid2qtype.get(entry['question_id'])
                                if qtype:
                                    qtype2acc[qtype].append(0)
                    except:
                        continue
            print(f"已找到 {len(processed_question_ids)} 個已處理的問題，將跳過這些問題")
        except Exception as e:
            print(f"讀取已處理問題時發生錯誤: {e}，將重新開始")
            processed_question_ids = set()
            qtype2acc = {t: [] for t in qtypes}

    # 以追加模式開啟檔案（如果已存在且有已處理的問題）或寫入模式（如果不存在）
    if len(processed_question_ids) > 0:
        out_f = open(result_file, 'a')
        print(f"以追加模式開啟檔案，將從問題 {len(processed_question_ids) + 1} 開始")
    else:
        out_f = open(result_file, 'w')
    
    total_eval_prompt_tokens = 0
    total_eval_completion_tokens = 0
    skipped_count = 0

    with out_f:
        logs = []
        for entry in tqdm(hypotheses, desc="評估答案"):

            if entry['question_id'] not in qid2qtype:
                print('Warning: skipping {} as it is not in reference data.'.format(entry['question_id']))
                continue
            
            # 跳過已處理的問題
            if entry['question_id'] in processed_question_ids:
                skipped_count += 1
                continue
            
            qtype = qid2qtype[entry['question_id']]
            q = qid2qdata[entry['question_id']]['question']
            ans = qid2qdata[entry['question_id']]['answer']
            hyp = entry['hypothesis']
            
            prompt = get_anscheck_prompt(qtype, q, ans, hyp, abstention='_abs' in entry['question_id'])
            kwargs = {
                'model': metric_model,
                'messages':[
                    {"role": "user", "content": prompt}
                ],
                'n': 1,
                'temperature': 0,
                'max_tokens': 10
            }
            completion = chat_completions_with_backoff(**kwargs)
            eval_response = completion.choices[0].message['content'].strip()
            label = 'yes' in eval_response.lower()
            
            # 提取 token 資訊
            eval_prompt_tokens = completion.usage.get('prompt_tokens', 0)
            eval_completion_tokens = completion.usage.get('completion_tokens', 0)
            eval_total_tokens = completion.usage.get('total_tokens', eval_prompt_tokens + eval_completion_tokens)
            
            total_eval_prompt_tokens += eval_prompt_tokens
            total_eval_completion_tokens += eval_completion_tokens
            
            entry['autoeval_label'] = {
                'model': metric_model,
                'label': label
            }
            # 記錄評估階段的 token 資訊
            if 'tokens' not in entry:
                entry['tokens'] = {}
            entry['tokens']['eval_prompt_tokens'] = eval_prompt_tokens
            entry['tokens']['eval_completion_tokens'] = eval_completion_tokens
            entry['tokens']['eval_total_tokens'] = eval_total_tokens
            
            logs.append(entry)
            if verbose:
                print(json.dumps({
                    'question': q,
                    'answer': ans,
                    'hypothesis': hyp,
                    'autoeval_label': label
                }, indent=4), flush=True)
            print(json.dumps(entry), file=out_f, flush=True)
            qtype2acc[qid2qtype[entry['question_id']]].append(1 if label else 0)
            processed_question_ids.add(entry['question_id'])  # 記錄已處理

            
    print('')
    print('=' * 60)
    print('評估完成統計')
    print('=' * 60)
    print(f'總問題數: {len(hypotheses)}')
    print(f'跳過問題數: {skipped_count}')
    print(f'處理問題數: {len(hypotheses) - skipped_count}')
    print('')
    print('準確率:')
    print('  整體:', round(np.mean([1 if x['autoeval_label']['label'] else 0 for x in logs]).item(), 4))
    for k,v in qtype2acc.items():
        if len(v) > 0:
            print('\t{}: {} ({})'.format(k, round(np.mean(v), 4), len(v)))
    print('')
    print('Token 使用:')
    print(f'  總 Eval Prompt Tokens: {total_eval_prompt_tokens:,}')
    print(f'  總 Eval Completion Tokens: {total_eval_completion_tokens:,}')
    print(f'  總 Eval Tokens: {total_eval_prompt_tokens + total_eval_completion_tokens:,}')
    if len(hypotheses) - skipped_count > 0:
        print(f'  平均 Eval Tokens/問題: {(total_eval_prompt_tokens + total_eval_completion_tokens) / (len(hypotheses) - skipped_count):.1f}')
    print('=' * 60)
    print('結果已儲存至:', result_file)
