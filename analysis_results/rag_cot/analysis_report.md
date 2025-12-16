# 實驗分析報告

**生成結果檔案**: `longmemeval_s_cleaned.json_retrievallog_turn_flat-stella_testlog_top50context_jsonformat_useronlyfalse_20251215-0653.jsonl.eval-results-gpt-4o-mini`

**參考答案檔案**: `longmemeval_s_cleaned.json`

**檢索結果檔案**: `longmemeval_s_cleaned.json_retrievallog_turn_flat-stella`

---

✓ 載入檢索結果: 500 個問題

================================================================================

--- 快速摘要（論文格式）---

--------------------------------------------------------------------------------

評估模型: gpt-4o-mini-2024-07-18

按任務類型的準確率:
  knowledge-update              : 0.5769 (78)
  multi-session                 : 0.2556 (133)
  single-session-assistant      : 0.8036 (56)
  single-session-preference     : 0.1000 (30)
  single-session-user           : 0.8429 (70)
  temporal-reasoning            : 0.3083 (133)

Task-averaged Accuracy: 0.4812
Overall Accuracy:       0.4540
Abstention Accuracy:    0.7333 (30)

================================================================================

--- 詳細分析報告 ---

--------------------------------------------------------------------------------
總樣本數: 500
平均準確率: 0.4540

================================================================================

--- [1] Retrieval Recall 分析 ---

--------------------------------------------------------------------------------
平均 Recall@5:  0.6779
平均 Recall@10: 0.7620
平均 Recall@50: 0.8101

[1.1] Recall@10 vs. 準確率
```
                       mean  count
recall_bin                        
Low (<0.5)         0.279070     43
Medium (0.5-0.99)  0.125000     24
Perfect (1.0)      0.434783    345
```


[1.2] 錯誤歸因分析（整體）
檢索失敗 (Recall < 1.0): 78 / 273 (28.6%)
推理失敗 (Recall = 1.0): 195 / 273 (71.4%)

[1.3] 按問題類型分解的 Recall 和錯誤歸因

完整統計表：
            question_type  count  accuracy  avg_recall@10  incorrect  retrieval_fail  retrieval_fail_%  reasoning_fail  reasoning_fail_%
         knowledge-update     78  0.576923       0.910256         33               1          3.030303              32         96.969697
            multi-session    133  0.255639       0.822807         99              29         29.292929              70         70.707071
 single-session-assistant     56  0.803571       0.089286         11              10         90.909091               1          9.090909
single-session-preference     30  0.100000       0.966667         27               1          3.703704              26         96.296296
      single-session-user     70  0.842857       0.900000         11               2         18.181818               9         81.818182
       temporal-reasoning    133  0.308271       0.778697         92              35         38.043478              57         61.956522

================================================================================

--- [2] 準確率 vs. 問題類型 ---

--------------------------------------------------------------------------------
```
                          is_correct       recall@10
                                mean count      mean
question_type                                       
knowledge-update            0.576923    78  0.910256
multi-session               0.255639   133  0.822807
single-session-assistant    0.803571    56  0.089286
single-session-preference   0.100000    30  0.966667
single-session-user         0.842857    70  0.900000
temporal-reasoning          0.308271   133  0.778697
```


================================================================================

--- [3] 位置偏差分析（僅 Single-Evidence 樣本）---

--------------------------------------------------------------------------------
Single-Evidence 樣本數: 176 / 500

[3.1] 準確率 vs. Evidence 位置
```
                 is_correct       recall@10
                       mean count      mean
pos_bin                                    
0-20% (Oldest)     0.793103    29  0.689655
20-40%             0.583333    36  0.611111
40-60%             0.720000    25  0.600000
60-80%             0.589744    39  0.564103
80-100% (Newest)   0.723404    47  0.723404
```


✓ 圖表已儲存: analysis_results/rag_without_userfact_cot/position_bias_single_evidence.png

================================================================================

--- [4] Single-Evidence vs Multi-Evidence 按問題類型分析 ---

--------------------------------------------------------------------------------

[4.1] 整體分布
Single-Evidence: 176 題
Multi-Evidence:  324 題

[4.2] 按問題類型和證據數量分解的準確率
```
                                            is_correct       recall@10 prompt_tokens
                                                  mean count      mean          mean
evidence_category question_type                                                     
Multi             knowledge-update              0.5769    78    0.9103    24840.6923
                  multi-session                 0.2556   133    0.8228    24650.7744
                  temporal-reasoning            0.2566   113    0.7749    24826.9292
Single            single-session-assistant      0.8036    56    0.0893    23329.8750
                  single-session-preference     0.1000    30    0.9667    27117.8667
                  single-session-user           0.8429    70    0.9000    23468.4286
                  temporal-reasoning            0.6000    20    0.8000    24006.7000
```


================================================================================

--- [5] Input Tokens 分析 ---

--------------------------------------------------------------------------------

[5.1] 整體統計
平均 Prompt Tokens: 24529
中位數 Prompt Tokens: 24692
最小值: 13671
最大值: 30832

[5.2] 按答題正確性分組的 Tokens 統計
```
              mean   median  count
Incorrect  24947.0  25039.0    273
Correct    24027.0  24095.0    227
```


[5.3] 按問題類型的 Tokens 統計
                           avg_tokens  median_tokens  accuracy
question_type                                                 
knowledge-update             24840.69        24919.5      0.58
multi-session                24650.77        24656.0      0.26
single-session-assistant     23329.88        23700.5      0.80
single-session-preference    27117.87        27148.0      0.10
single-session-user          23468.43        23771.5      0.84
temporal-reasoning           24703.59        24950.0      0.31

[5.4] 按 Evidence 數量的 Tokens 統計
                   avg_tokens  median_tokens  accuracy  count
evidence_category                                            
Multi                24757.93        24892.0      0.33    324
Single               24107.57        24152.5      0.68    176

✓ 圖表已儲存: analysis_results/rag_without_userfact_cot/tokens_analysis.png

================================================================================

--- [6] Multi-Evidence 詳細分析 ---

--------------------------------------------------------------------------------
Multi-Evidence 樣本數: 324 / 500

[6.1] 準確率 vs. Evidence 數量
```
               is_correct       evidence_span
                     mean count          mean
evidence_count                               
2                0.396000   250      0.401130
3                0.121951    41      0.476404
4                0.157895    19      0.672279
5                0.090909    11      0.636521
6                0.000000     3      0.543235
```


[6.2] 準確率 vs. Evidence 跨度
```
                        mean  count
span_bin                           
Small (<0.33)       0.325581    129
Medium (0.33-0.67)  0.305785    121
Large (>0.67)       0.391892     74
```


================================================================================

--- [7] Context Length 分析 ---

--------------------------------------------------------------------------------
```
            is_correct       recall@10
                  mean count      mean
history_bin                           
0-50          0.424242   396  0.755261
50-100        0.567308   104  0.787660
100-150            NaN     0       NaN
150-200            NaN     0       NaN
```


================================================================================
分析完成！

--------------------------------------------------------------------------------
