import sys
import json
import os
import glob
from tqdm import tqdm
import openai
import backoff
import random
import numpy as np
from datetime import datetime, timedelta
import argparse
from transformers import AutoTokenizer
import tiktoken


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--in_file', type=str, required=True)
    parser.add_argument('--out_dir', type=str, required=True)
    parser.add_argument('--out_file_suffix', type=str, default="")
    parser.add_argument('--resume', action='store_true', 
                       help='啟用斷點續傳：如果輸出檔案已存在，將跳過已處理的問題')
        
    parser.add_argument('--model_name', type=str, required=True)
    parser.add_argument('--model_alias', type=str, required=True)
    parser.add_argument('--openai_base_url', type=str, default=None)
    parser.add_argument('--openai_key', type=str, required=True)
    parser.add_argument('--openai_organization', type=str, default=None)

    parser.add_argument('--retriever_type', type=str, required=True)
    parser.add_argument('--topk_context', type=int, required=True)
    parser.add_argument('--history_format', type=str, required=True, choices=['json', 'nl'])
    parser.add_argument('--useronly', type=str, required=True, choices=['true', 'false'])
    parser.add_argument('--cot', type=str, required=True, choices=['true', 'false'])
    parser.add_argument('--con', type=str, required=False, choices=['true', 'false'], default='false')

    # user fact expansion
    parser.add_argument('--merge_key_expansion_into_value', type=str, choices=['merge', 'replace', 'none'], default='none')     # merge key expansion into value

    parser.add_argument('--gen_length', type=int, default=None)
    
    return parser.parse_args()


def check_args(args):
    print(args)


def prepare_prompt(entry, retriever_type, topk_context: int, useronly: bool, history_format: str, cot: bool, tokenizer, tokenizer_backend, max_retrieval_length, merge_key_expansion_into_value, con=False, con_model=None):    
    if retriever_type == 'no-retrieval':
        answer_prompt_template = '{}'
        if cot:
            answer_prompt_template += 'Answer step by step.'
            
    else:
        if merge_key_expansion_into_value is None or merge_key_expansion_into_value == 'none':
            if cot:
                answer_prompt_template = 'I will give you several history chats between you and a user. Please answer the question based on the relevant chat history. Answer the question step by step: first extract all the relevant information, and then reason over the information to get the answer.\n\n\nHistory Chats:\n\n{}\n\nCurrent Date: {}\nQuestion: {}\nAnswer (step by step):'
            else:
                answer_prompt_template = 'I will give you several history chats between you and a user. Please answer the question based on the relevant chat history.\n\n\nHistory Chats:\n\n{}\n\nCurrent Date: {}\nQuestion: {}\nAnswer:'
        elif merge_key_expansion_into_value == 'merge':
            if cot:
                answer_prompt_template = 'I will give you several history chats between you and a user, as well as the relevant user facts extracted from the chat history. Please answer the question based on the relevant chat history and the user facts. Answer the question step by step: first extract all the relevant information, and then reason over the information to get the answer.\n\n\nHistory Chats:\n\n{}\n\nCurrent Date: {}\nQuestion: {}\nAnswer (step by step):'
            else:
                answer_prompt_template = 'I will give you several history chats between you and a user, as well as the relevant user facts extracted from the chat history. Please answer the question based on the relevant chat history and the user facts\n\n\nHistory Chats:\n\n{}\n\nCurrent Date: {}\nQuestion: {}\nAnswer:'
        elif merge_key_expansion_into_value == 'replace':
            if cot:
                answer_prompt_template = 'I will give you several facts extracted from history chats between you and a user. Please answer the question based on the relevant facts. Answer the question step by step: first extract all the relevant information, and then reason over the information to get the answer.\n\n\nHistory Chats:\n\n{}\n\nCurrent Date: {}\nQuestion: {}\nAnswer (step by step):'
            else:
                answer_prompt_template = 'I will give you several facts extracted from history chats between you and a user. Please answer the question based on the relevant facts.\n\n\nHistory Chats:\n\n{}\n\nCurrent Date: {}\nQuestion: {}\nAnswer:'
        else:
            raise NotImplementedError
        
    question_date_string = entry['question_date']
    question_string = entry['question']

    corpusid2date, corpusid2entry = {}, {}
    for session_date, session_id, session_entry in zip(entry['haystack_dates'], entry['haystack_session_ids'], entry['haystack_sessions']):
        corpusid2date[session_id] = session_date
        corpusid2entry[session_id] = session_entry
        for i_turn, turn_entry in enumerate(session_entry):
            corpusid2date[session_id + '_' + str(i_turn+1)] = session_date
            corpusid2entry[session_id + '_' + str(i_turn+1)] = turn_entry

    corpusid2retvalue = {}
    try:
        for ret_result_entry in entry['retrieval_results']['ranked_items']:
            corpusid2retvalue[ret_result_entry['corpus_id']] = ret_result_entry['text']
    except:
        pass
    
    retrieved_chunks = []
    # get chunks in the original order
    if retriever_type == "orig-session":   # no retrieval, session
        for session_date, session_entry in zip(entry['haystack_dates'], entry['haystack_sessions']):
            if useronly:
                retrieved_chunks.append((session_date, [x for x in session_entry if x['role'] == 'user']))
            else:
                retrieved_chunks.append((session_date, session_entry))
    elif retriever_type == "orig-turn":  # no retrieval, turn
        for session_date, session_entry in zip(entry['haystack_dates'], entry['haystack_sessions']):
            if useronly:
                retrieved_chunks += [(session_date, x) for x in session_entry if x['role'] == 'user']
            else:
                retrieved_chunks += [(session_date, x) for x in session_entry]

    # only retain oracle chunks 
    elif retriever_type == "oracle-session":   # no retrieval, session
        for session_date, session_entry in zip(entry['haystack_dates'], entry['haystack_sessions']):
            if useronly:
                retrieved_chunks.append((session_date, [x for x in session_entry if x['role'] == 'user']))
            else:
                retrieved_chunks.append((session_date, session_entry))
    elif retriever_type == "oracle-turn":  # no retrieval, turn
        for session_date, session_entry in zip(entry['haystack_dates'], entry['haystack_sessions']):
            if useronly:
                retrieved_chunks += [(session_date, x) for x in session_entry if x['role'] == 'user']
            else:
                retrieved_chunks += [(session_date, x) for x in session_entry]

    # get retrieved chunks
    elif retriever_type == "flat-turn":
        for ret_result_entry in entry['retrieval_results']['ranked_items']:
            converted_corpus_id = '_'.join(ret_result_entry['corpus_id'].replace('noans_', 'answer_').split('_')[:-1])
            converted_turn_id = int(ret_result_entry['corpus_id'].replace('noans_', 'answer_').split('_')[-1]) - 1   # we had offset one during retrieval
            # automatically expand turn into round
            try:
                cur_round_data = [corpusid2entry[converted_corpus_id][converted_turn_id]]
                converted_next_turn_id = converted_turn_id + 1
                if converted_next_turn_id < len(corpusid2entry[converted_corpus_id]):
                    cur_round_data.append(corpusid2entry[converted_corpus_id][converted_next_turn_id])
                
            except:
                continue
            
            # handle optional merging key into the value
            if merge_key_expansion_into_value is None or merge_key_expansion_into_value == 'none':
                retrieved_chunks.append((corpusid2date[converted_corpus_id], cur_round_data))
            elif merge_key_expansion_into_value == 'replace':
                retrieved_chunks.append((corpusid2date[converted_corpus_id], corpusid2retvalue[ret_result_entry['corpus_id']]))
            elif merge_key_expansion_into_value == 'merge':
                retrieved_chunks.append((corpusid2date[converted_corpus_id], corpusid2retvalue[ret_result_entry['corpus_id']], cur_round_data))
            else:
                raise NotImplementedError

        if useronly and not merge_key_expansion_into_value == 'replace':
            retrieved_chunks = [x for x in retrieved_chunks if x[-1]['role'] == 'user']     

    elif retriever_type == "flat-session":
        for ret_result_entry in entry['retrieval_results']['ranked_items']:
            # handle optional merging key into the value
            if merge_key_expansion_into_value is None or merge_key_expansion_into_value == 'none':
                if useronly:
                    retrieved_chunks.append((corpusid2date[ret_result_entry['corpus_id'].replace('noans_', 'answer_')],
                                            [x for x in corpusid2entry[ret_result_entry['corpus_id'].replace('noans_', 'answer_')] if x['role'] == 'user']))
                else:
                    retrieved_chunks.append((corpusid2date[ret_result_entry['corpus_id'].replace('noans_', 'answer_')], corpusid2entry[ret_result_entry['corpus_id'].replace('noans_', 'answer_')]))
            elif merge_key_expansion_into_value == 'replace':
                retrieved_chunks.append((corpusid2date[ret_result_entry['corpus_id'].replace('noans_', 'answer_')], corpusid2retvalue[ret_result_entry['corpus_id']]))
            elif merge_key_expansion_into_value == 'merge':
                if useronly:
                    retrieved_chunks.append((corpusid2date[ret_result_entry['corpus_id'].replace('noans_', 'answer_')], corpusid2retvalue[ret_result_entry['corpus_id']], [x for x in corpusid2entry[ret_result_entry['corpus_id'].replace('noans_', 'answer_')] if x['role'] == 'user']))
                else:
                    retrieved_chunks.append((corpusid2date[ret_result_entry['corpus_id'].replace('noans_', 'answer_')], corpusid2retvalue[ret_result_entry['corpus_id']], corpusid2entry[ret_result_entry['corpus_id'].replace('noans_', 'answer_')]))
            else:
                raise NotImplementedError

    elif retriever_type == "no-retrieval":
        retrieved_chunks = []
        
    else:
        raise NotImplementedError

    if retriever_type in ["orig-turn", "orig-session"]:
        retrieved_chunks = retrieved_chunks[-topk_context:]  # keep latest
    else:
        retrieved_chunks = retrieved_chunks[:topk_context]

    # clean up
    retrieved_chunks_cleaned = []
    for retrieved_item in retrieved_chunks:
        try:
            date, session_entry = retrieved_item
            for turn_entry in session_entry:
                if type(turn_entry) == dict and 'has_answer' in turn_entry:
                    turn_entry.pop('has_answer')
            retrieved_chunks_cleaned.append((date, session_entry))
        except:
            date, expansion_entry, session_entry = retrieved_item
            for turn_entry in session_entry:
                if type(turn_entry) == dict and 'has_answer' in turn_entry:
                    turn_entry.pop('has_answer')
            retrieved_chunks_cleaned.append((date, expansion_entry, session_entry))
    retrieved_chunks = retrieved_chunks_cleaned

    # optional: if CoN is specified, add an information extraction process before feeding into the model
    if con:
        con_prompt = "I will give you a chat history between you and a user, as well as a question from the user. Write reading notes to extract all the relevant user information relevant to answering the answer. If no relevant information is found, just output \"empty\". \n\n\nChat History:\nSession Date: {}\nSession Content:\n{}\n\nQuestion Date: {}\nQuestion: {}\nExtracted note (information relevant to answering the question):"
        retrieved_chunks_with_notes = []
        for i, cur_item in enumerate(retrieved_chunks):
            if merge_key_expansion_into_value == 'merge':
                (chunk_date, chunk_expansion_entry, chunk_entry) = cur_item
                                
            else:
                (chunk_date, chunk_entry) = cur_item
                
            kwargs = {
                'model': con_model,
                'messages':[
                    {"role": "user", "content": con_prompt.format(chunk_date, json.dumps(chunk_entry), question_date_string, question_string)}
                ],
                'n': 1,
                'temperature': 0,
                'max_tokens': 500,
            }
            completion = chat_completions_with_backoff(**kwargs) 
            cur_note = completion.choices[0].message['content'].strip()
            chunk_entry_con = {'session_summary': cur_note}

            if merge_key_expansion_into_value == 'merge':
                retrieved_chunks_with_notes.append((chunk_date, chunk_expansion_entry, chunk_entry_con))
            else:
                retrieved_chunks_with_notes.append((chunk_date, chunk_entry_con))

        retrieved_chunks = retrieved_chunks_with_notes
                
    # sort sessions by their dates
    retrieved_chunks.sort(key=lambda x: x[0])
    
    history_string = ""
    for i, cur_item in enumerate(retrieved_chunks):
        if merge_key_expansion_into_value == 'merge':
            (chunk_date, chunk_expansion_entry, chunk_entry) = cur_item
        else:
            (chunk_date, chunk_entry) = cur_item

        if history_format == 'json':
            if merge_key_expansion_into_value == 'merge':
                sess_string = '\n' + json.dumps({'session_summary_facts': chunk_expansion_entry, 'original_session': chunk_entry})
            else:
                sess_string = '\n' + json.dumps(chunk_entry)
        elif history_format == 'nl':
            sess_string = ""
            if merge_key_expansion_into_value == 'merge':
                sess_string += "\n\nSession summary and facts:" + chunk_expansion_entry
            if type(chunk_entry) == list:
                for turn_entry in chunk_entry:
                    sess_string += "\n\n{}: {}".format(turn_entry['role'], turn_entry['content'].strip())
            else:
                sess_string += "{}: {}".format(chunk_entry['role'], chunk_entry['content'].strip())    
        else:
            raise NotImplementedError

        if retriever_type in ["orig-session", "flat-session", "oracle-session"]:
            history_string += '\n### Session {}:\nSession Date: {}\nSession Content:\n{}\n'.format(i+1, chunk_date, sess_string)
        elif retriever_type in ["orig-turn", "flat-turn", "oracle-turn"]:  
            # history_string += '\n### Round {}:\nDate: {}\nRound Content:\n{}\n'.format(i+1, chunk_date, sess_string)
            history_string += '\n### Session {}:\nSession Date: {}\nSession Content:\n{}\n'.format(i+1, chunk_date, sess_string)  # we include both sides right now
        elif retriever_type == "no-retrieval":
            history_string += ""
        else:
            raise NotImplementedError

    assert retriever_type == "no-retrieval" or history_string != ""
    if retriever_type == "no-retrieval":
        prompt = answer_prompt_template.format(question_string)
    else:
        # truncate history string
        if tokenizer_backend == 'openai':
            tokens = tokenizer.encode(history_string, allowed_special={'<|endoftext|>'})
            if len(tokens) > max_retrieval_length:
                print('Truncating from {} to {}'.format(len(tokens), max_retrieval_length), flush=True)
                truncated_tokens = tokens[:max_retrieval_length]
                history_string = tokenizer.decode(truncated_tokens)
        elif tokenizer_backend == 'huggingface':
            encoded_input = tokenizer(history_string, max_length=max_retrieval_length, truncation=False, return_tensors="pt")
            if len(encoded_input['input_ids'][0]) > max_retrieval_length:
                print('Truncating from {} to {}'.format(len(encoded_input['input_ids'][0]), max_retrieval_length))
                encoded_input = tokenizer(history_string, max_length=max_retrieval_length, truncation=True, return_tensors="pt")
                history_string = tokenizer.decode(encoded_input['input_ids'][0], skip_special_tokens=True)
        else:
            raise NotImplementedError
        prompt = answer_prompt_template.format(history_string, question_date_string, question_string)

    return prompt
    

@backoff.on_exception(backoff.constant, (openai.error.RateLimitError,), 
                      interval=5)
def chat_completions_with_backoff(**kwargs):
    return openai.ChatCompletion.create(**kwargs)


def main(args):
    # setup
    openai.api_key = args.openai_key
    if args.openai_base_url:
        openai.api_base = args.openai_base_url
    if args.openai_organization:
        openai.organization = args.openai_organization

    try:
        in_data = json.load(open(args.in_file))
    except:
        in_data = [json.loads(line) for line in open(args.in_file).readlines()]

    in_file_tmp = args.in_file.split('/')[-1]
    # 如果啟用斷點續傳，使用固定檔名（不含時間戳）；否則使用時間戳
    if args.resume:
        # 斷點續傳模式：使用固定檔名，嘗試找到已存在的檔案
        if args.merge_key_expansion_into_value is not None and args.merge_key_expansion_into_value != 'none':
            out_file_base = args.out_dir + '/' + in_file_tmp + '_testlog_top{}context_{}format_useronly{}_factexpansion{}'.format(args.topk_context, args.history_format, args.useronly, args.merge_key_expansion_into_value)
        else:
            out_file_base = args.out_dir + '/' + in_file_tmp + '_testlog_top{}context_{}format_useronly{}'.format(args.topk_context, args.history_format, args.useronly)
        if args.out_file_suffix.strip() != "":
            out_file_base += args.out_file_suffix
        
        # 尋找已存在的檔案（可能有多個，取最新的）
        existing_files = glob.glob(out_file_base + '_*.jsonl')
        if existing_files:
            # 找到已存在的檔案，使用它
            out_file = max(existing_files, key=os.path.getmtime)
            print(f"斷點續傳模式：使用已存在的檔案 {out_file}")
        else:
            # 沒有找到，創建新的（加上時間戳）
            out_file = out_file_base + '_' + datetime.now().strftime("%Y%m%d-%H%M") + '.jsonl'
    else:
        # 正常模式：使用時間戳
        if args.merge_key_expansion_into_value is not None and args.merge_key_expansion_into_value != 'none':
            out_file = args.out_dir + '/' + in_file_tmp + '_testlog_top{}context_{}format_useronly{}_factexpansion{}_{}.jsonl'.format(args.topk_context, args.history_format, args.useronly, args.merge_key_expansion_into_value, datetime.now().strftime("%Y%m%d-%H%M"))
        else:
            out_file = args.out_dir + '/' + in_file_tmp + '_testlog_top{}context_{}format_useronly{}_{}.jsonl'.format(args.topk_context, args.history_format, args.useronly, datetime.now().strftime("%Y%m%d-%H%M"))
        if args.out_file_suffix.strip() != "":
            out_file = out_file.replace('.jsonl', '') + args.out_file_suffix + '.jsonl'
    
    # 斷點續傳：檢查已處理的問題
    processed_question_ids = set()
    if args.resume and os.path.exists(out_file):
        print(f"發現已存在的輸出檔案: {out_file}")
        print("正在讀取已處理的問題...")
        try:
            with open(out_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if 'question_id' in entry:
                            processed_question_ids.add(entry['question_id'])
                    except:
                        continue
            print(f"已找到 {len(processed_question_ids)} 個已處理的問題，將跳過這些問題")
        except Exception as e:
            print(f"讀取已處理問題時發生錯誤: {e}，將重新開始")
            processed_question_ids = set()
    elif os.path.exists(out_file) and not args.resume:
        print(f"警告: 輸出檔案已存在: {out_file}")
        print("如果希望斷點續傳，請使用 --resume 參數")
        print("否則將覆蓋現有檔案")
        response = input("是否繼續？(y/n): ")
        if response.lower() != 'y':
            print("已取消")
            sys.exit(0)
        processed_question_ids = set()
    
    # 以追加模式開啟檔案（如果已存在且有已處理的問題）或寫入模式（如果不存在）
    if len(processed_question_ids) > 0:
        out_f = open(out_file, 'a')
        print(f"以追加模式開啟檔案，將從問題 {len(processed_question_ids) + 1} 開始")
    else:
        out_f = open(out_file, 'w')

    # inference
    model2maxlength = {
        'gpt-4o': 128000,
        'gpt-4o-2024-08-06': 128000,
        "gpt-4o-mini-2024-07-18": 128000,
        'meta-llama/Meta-Llama-3.1-8B-Instruct': 128000,
        'llama3.1:8b-128k': 128000,  # Ollama 模型
        'meta-llama/Meta-Llama-3.1-70B-Instruct': 128000,
        'microsoft/Phi-3-medium-128k-instruct': 120000,
        'microsoft/Phi-3.5-mini-instruct': 120000,
        'microsoft/phi-4': 16000,
        'mistral-7b-instruct-v0.2': 32000,
        'mistral-7b-instruct-v0.3': 32000,
        'In2Training/FILM-7B': 32000,
    }
    model_max_length = model2maxlength.get(args.model_name, 128000)  # 預設 128k
    
    # 判斷 tokenizer 類型
    if 'gpt-4' in args.model_name.lower() or 'gpt-3.5' in args.model_name.lower():
        tokenizer = tiktoken.get_encoding('o200k_base')
        tokenizer_backend = 'openai'
    elif ':' in args.model_name:
        # Ollama 模型格式（如 llama3.1:8b-128k）
        # 使用對應的 HuggingFace 模型作為 tokenizer
        if 'llama3.1' in args.model_name.lower():
            tokenizer = AutoTokenizer.from_pretrained('meta-llama/Meta-Llama-3.1-8B-Instruct')
        elif 'llama3' in args.model_name.lower():
            tokenizer = AutoTokenizer.from_pretrained('meta-llama/Meta-Llama-3-8B-Instruct')
        else:
            # 預設使用 Llama 3.1 tokenizer
            tokenizer = AutoTokenizer.from_pretrained('meta-llama/Meta-Llama-3.1-8B-Instruct')
        tokenizer_backend = 'huggingface'
    else:
        tokenizer = AutoTokenizer.from_pretrained(args.model_name)
        tokenizer_backend = 'huggingface'

    total_prompt_tokens, total_completion_tokens = 0, 0
    skipped_count = 0
    
    for entry in tqdm(in_data, desc="生成答案"):
        # 斷點續傳：跳過已處理的問題
        if entry['question_id'] in processed_question_ids:
            skipped_count += 1
            continue

        # Ttruncate the retrieval part of the prompt such that the context length never exceeds
        gen_length = args.gen_length
        if gen_length is None:
            gen_length = 500 if not args.cot else 800
        max_retrieval_length = model_max_length - gen_length - 1000

        if args.con == 'true':
            prompt = prepare_prompt(entry, args.retriever_type, args.topk_context, args.useronly=='true',
                                    args.history_format, args.cot=='true', 
                                    tokenizer=tokenizer, tokenizer_backend=tokenizer_backend, max_retrieval_length=max_retrieval_length,
                                    merge_key_expansion_into_value=args.merge_key_expansion_into_value,
                                    con=True, con_model=args.model_name)
        else:
            prompt = prepare_prompt(entry, args.retriever_type, args.topk_context, args.useronly=='true',
                                    args.history_format, args.cot=='true', 
                                    tokenizer=tokenizer, tokenizer_backend=tokenizer_backend, max_retrieval_length=max_retrieval_length,
                                    merge_key_expansion_into_value=args.merge_key_expansion_into_value)

        try:
            print(json.dumps({'question_id': entry['question_id'], 'question': entry['question'], 'answer': entry['answer']}, indent=4), flush=True)
            
            kwargs = {
                'model': args.model_name,
                'messages':[
                    {"role": "user", "content": prompt}
                ],
                'n': 1,
                'temperature': 0,
                'max_tokens': gen_length,
            }
            completion = chat_completions_with_backoff(**kwargs) 
            answer = completion.choices[0].message['content'].strip()

            # 提取 tokens 資訊
            prompt_tokens = completion.usage.get('prompt_tokens', 0)
            completion_tokens = completion.usage.get('completion_tokens', 0)
            total_tokens = completion.usage.get('total_tokens', prompt_tokens + completion_tokens)
            
            # 計算 prompt 的實際 token 長度（用於分析文本長度）
            if tokenizer_backend == 'openai':
                prompt_token_count = len(tokenizer.encode(prompt, allowed_special={'<|endoftext|>'}))
            else:
                prompt_token_count = len(tokenizer.encode(prompt, add_special_tokens=False))
            
            total_prompt_tokens += prompt_tokens
            total_completion_tokens += completion_tokens
            
            # 記錄詳細的 tokens / usage 資訊到輸出
            output_entry = {
                'question_id': entry['question_id'],
                'hypothesis': answer,
                'usage': {
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': total_tokens,
                },
                'tokens': {
                    'prompt_tokens': prompt_tokens,  # API 回傳的 prompt tokens
                    'completion_tokens': completion_tokens,
                    'total_tokens': total_tokens,
                    'prompt_token_count': prompt_token_count  # 實際計算的 prompt token 數（用於分析）
                }
            }
            
            print(json.dumps({'hypothesis': answer}), flush=True)
            print(json.dumps(output_entry), file=out_f, flush=True)
        except Exception as e:
            print('One exception captured', repr(e))
            continue

    out_f.close()
    
    print('')
    print('=' * 60)
    print('生成完成統計')
    print('=' * 60)
    print(f'總問題數: {len(in_data)}')
    print(f'跳過問題數: {skipped_count}')
    print(f'處理問題數: {len(in_data) - skipped_count}')
    print(f'總 Prompt Tokens: {total_prompt_tokens:,}')
    print(f'總 Completion Tokens: {total_completion_tokens:,}')
    print(f'總 Tokens: {total_prompt_tokens + total_completion_tokens:,}')
    if len(in_data) - skipped_count > 0:
        print(f'平均 Prompt Tokens/問題: {total_prompt_tokens / (len(in_data) - skipped_count):.1f}')
        print(f'平均 Completion Tokens/問題: {total_completion_tokens / (len(in_data) - skipped_count):.1f}')
    print(f'輸出檔案: {out_file}')
    print('=' * 60)
    

if __name__ == '__main__':
    args = parse_args()
    check_args(args)
    main(args)
