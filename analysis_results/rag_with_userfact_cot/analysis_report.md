# 實驗分析報告

**生成結果檔案**: `longmemeval_s_cleaned.json_retrievallog_turn_flat-stella_testlog_top50context_jsonformat_useronlyfalse_20251215-0646.jsonl.eval-results-gpt-4o-mini`

**參考答案檔案**: `longmemeval_s_cleaned.json`

**檢索結果檔案**: `longmemeval_s_cleaned.json_retrievallog_turn_flat-stella`

---

✓ 載入檢索結果: 500 個問題

================================================================================

--- 快速摘要（論文格式）---

--------------------------------------------------------------------------------

評估模型: gpt-4o-mini-2024-07-18

按任務類型的準確率:
  knowledge-update              : 0.6154 (78)
  multi-session                 : 0.2556 (133)
  single-session-assistant      : 0.7857 (56)
  single-session-preference     : 0.1667 (30)
  single-session-user           : 0.7143 (70)
  temporal-reasoning            : 0.3835 (133)

Task-averaged Accuracy: 0.4869
Overall Accuracy:       0.4640
Abstention Accuracy:    0.8000 (30)

================================================================================

--- 詳細分析報告 ---

--------------------------------------------------------------------------------
總樣本數: 500
平均準確率: 0.4640

================================================================================

--- [1] Retrieval Recall 分析 ---

--------------------------------------------------------------------------------
平均 Recall@5:  0.6582
平均 Recall@10: 0.7541
平均 Recall@50: 0.8081

[1.1] Recall@10 vs. 準確率
```
                       mean  count
recall_bin                        
Low (<0.5)         0.294118     51
Medium (0.5-0.99)  0.130435     23
Perfect (1.0)      0.444118    340
```


[1.2] 錯誤歸因分析（整體）
檢索失敗 (Recall < 1.0): 79 / 268 (29.5%)
推理失敗 (Recall = 1.0): 189 / 268 (70.5%)

[1.3] 按問題類型分解的 Recall 和錯誤歸因

完整統計表：
            question_type  count  accuracy  avg_recall@10  incorrect  retrieval_fail  retrieval_fail_%  reasoning_fail  reasoning_fail_%
         knowledge-update     78  0.615385       0.910256         30               1          3.333333              29         96.666667
            multi-session    133  0.255639       0.785088         99              36         36.363636              63         63.636364
 single-session-assistant     56  0.785714       0.071429         12              11         91.666667               1          8.333333
single-session-preference     30  0.166667       0.933333         25               2          8.000000              23         92.000000
      single-session-user     70  0.714286       0.914286         20               0          0.000000              20        100.000000
       temporal-reasoning    133  0.383459       0.794110         82              29         35.365854              53         64.634146

================================================================================

--- [2] 準確率 vs. 問題類型 ---

--------------------------------------------------------------------------------
```
                          is_correct       recall@10
                                mean count      mean
question_type                                       
knowledge-update            0.615385    78  0.910256
multi-session               0.255639   133  0.785088
single-session-assistant    0.785714    56  0.071429
single-session-preference   0.166667    30  0.933333
single-session-user         0.714286    70  0.914286
temporal-reasoning          0.383459   133  0.794110
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
0-20% (Oldest)     0.655172    29  0.689655
20-40%             0.500000    36  0.666667
40-60%             0.680000    25  0.600000
60-80%             0.615385    39  0.538462
80-100% (Newest)   0.680851    47  0.702128
```


✓ 圖表已儲存: analysis_results/rag_with_userfact_cot/position_bias_single_evidence.png

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
Multi             knowledge-update              0.6154    78    0.9103    27082.8590
                  multi-session                 0.2556   133    0.7851    27603.4211
                  temporal-reasoning            0.3540   113    0.7842    27322.2920
Single            single-session-assistant      0.7857    56    0.0714    25533.0000
                  single-session-preference     0.1667    30    0.9333    28451.2000
                  single-session-user           0.7143    70    0.9143    26778.7714
                  temporal-reasoning            0.5500    20    0.8500    26918.9500
```


================================================================================

--- [5] Input Tokens 分析 ---

--------------------------------------------------------------------------------

[5.1] 整體統計
平均 Prompt Tokens: 27135
中位數 Prompt Tokens: 27170
最小值: 18498
最大值: 35116

[5.2] 按答題正確性分組的 Tokens 統計
```
              mean   median  count
Incorrect  27533.0  27621.0    268
Correct    26675.0  26638.0    232
```


[5.3] 按問題類型的 Tokens 統計
                           avg_tokens  median_tokens  accuracy
question_type                                                 
knowledge-update             27082.86        27020.5      0.62
multi-session                27603.42        27467.0      0.26
single-session-assistant     25533.00        25454.0      0.79
single-session-preference    28451.20        28216.0      0.17
single-session-user          26778.77        26688.0      0.71
temporal-reasoning           27261.64        27487.0      0.38

[5.4] 按 Evidence 數量的 Tokens 統計
                   avg_tokens  median_tokens  accuracy  count
evidence_category                                            
Multi                27380.05        27452.0      0.38    324
Single               26683.39        26886.0      0.62    176

✓ 圖表已儲存: analysis_results/rag_with_userfact_cot/tokens_analysis.png

================================================================================

--- [6] Multi-Evidence 詳細分析 ---

--------------------------------------------------------------------------------
Multi-Evidence 樣本數: 324 / 500

[6.1] 準確率 vs. Evidence 數量
```
               is_correct       evidence_span
                     mean count          mean
evidence_count                               
2                0.444000   250      0.401130
3                0.170732    41      0.476404
4                0.157895    19      0.672279
5                0.090909    11      0.636521
6                0.000000     3      0.543235
```


[6.2] 準確率 vs. Evidence 跨度
```
                        mean  count
span_bin                           
Small (<0.33)       0.372093    129
Medium (0.33-0.67)  0.363636    121
Large (>0.67)       0.405405     74
```


================================================================================

--- [7] Context Length 分析 ---

--------------------------------------------------------------------------------
```
            is_correct       recall@10
                  mean count      mean
history_bin                           
0-50          0.444444   396  0.751978
50-100        0.538462   104  0.762019
100-150            NaN     0       NaN
150-200            NaN     0       NaN
```


================================================================================
分析完成！

--------------------------------------------------------------------------------
