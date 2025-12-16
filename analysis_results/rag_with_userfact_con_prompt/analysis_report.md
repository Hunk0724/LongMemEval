# 實驗分析報告

**生成結果檔案**: `longmemeval_s_cleaned.json_retrievallog_turn_flat-stella_testlog_top50context_jsonformat_useronlyfalse_20251215-1518.jsonl.eval-results-gpt-4o-mini`

**參考答案檔案**: `longmemeval_s_cleaned.json`

**檢索結果檔案**: `longmemeval_s_cleaned.json_retrievallog_turn_flat-stella`

---

✓ 載入檢索結果: 500 個問題

================================================================================

--- 快速摘要（論文格式）---

--------------------------------------------------------------------------------

評估模型: gpt-4o-mini-2024-07-18

按任務類型的準確率:
  knowledge-update              : 0.7692 (78)
  multi-session                 : 0.3985 (133)
  single-session-assistant      : 0.5357 (56)
  single-session-preference     : 0.3000 (30)
  single-session-user           : 0.8857 (70)
  temporal-reasoning            : 0.3759 (133)

Task-averaged Accuracy: 0.5442
Overall Accuracy:       0.5280
Abstention Accuracy:    0.9000 (30)

================================================================================

--- 詳細分析報告 ---

--------------------------------------------------------------------------------
總樣本數: 500
平均準確率: 0.5280

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
Low (<0.5)         0.372549     51
Medium (0.5-0.99)  0.347826     23
Perfect (1.0)      0.544118    340
```


[1.2] 錯誤歸因分析（整體）
檢索失敗 (Recall < 1.0): 81 / 236 (34.3%)
推理失敗 (Recall = 1.0): 155 / 236 (65.7%)

[1.3] 按問題類型分解的 Recall 和錯誤歸因

完整統計表：
            question_type  count  accuracy  avg_recall@10  incorrect  retrieval_fail  retrieval_fail_%  reasoning_fail  reasoning_fail_%
         knowledge-update     78  0.769231       0.910256         18               1          5.555556              17         94.444444
            multi-session    133  0.398496       0.785088         80              28         35.000000              52         65.000000
 single-session-assistant     56  0.535714       0.071429         26              25         96.153846               1          3.846154
single-session-preference     30  0.300000       0.933333         21               2          9.523810              19         90.476190
      single-session-user     70  0.885714       0.914286          8               0          0.000000               8        100.000000
       temporal-reasoning    133  0.375940       0.794110         83              25         30.120482              58         69.879518

================================================================================

--- [2] 準確率 vs. 問題類型 ---

--------------------------------------------------------------------------------
```
                          is_correct       recall@10
                                mean count      mean
question_type                                       
knowledge-update            0.769231    78  0.910256
multi-session               0.398496   133  0.785088
single-session-assistant    0.535714    56  0.071429
single-session-preference   0.300000    30  0.933333
single-session-user         0.885714    70  0.914286
temporal-reasoning          0.375940   133  0.794110
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
0-20% (Oldest)     0.758621    29  0.689655
20-40%             0.638889    36  0.666667
40-60%             0.480000    25  0.600000
60-80%             0.692308    39  0.538462
80-100% (Newest)   0.638298    47  0.702128
```


✓ 圖表已儲存: analysis_results/rag_with_userfact_con_prompt/position_bias_single_evidence.png

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
Multi             knowledge-update              0.7692    78    0.9103     2099.5000
                  multi-session                 0.3985   133    0.7851     2281.9549
                  temporal-reasoning            0.3274   113    0.7842     2485.4867
Single            single-session-assistant      0.5357    56    0.0714     2937.5714
                  single-session-preference     0.3000    30    0.9333     3051.2333
                  single-session-user           0.8857    70    0.9143     1951.5714
                  temporal-reasoning            0.6500    20    0.8500     2858.0500
```


================================================================================

--- [5] Input Tokens 分析 ---

--------------------------------------------------------------------------------

[5.1] 整體統計
平均 Prompt Tokens: 2396
中位數 Prompt Tokens: 2197
最小值: 1739
最大值: 6095

[5.2] 按答題正確性分組的 Tokens 統計
```
             mean  median  count
Incorrect  2542.0  2306.0    236
Correct    2265.0  2048.0    264
```


[5.3] 按問題類型的 Tokens 統計
                           avg_tokens  median_tokens  accuracy
question_type                                                 
knowledge-update              2099.50         1999.5      0.77
multi-session                 2281.95         2145.0      0.40
single-session-assistant      2937.57         2814.5      0.54
single-session-preference     3051.23         2924.5      0.30
single-session-user           1951.57         1874.5      0.89
temporal-reasoning            2541.51         2291.0      0.38

[5.4] 按 Evidence 數量的 Tokens 統計
                   avg_tokens  median_tokens  accuracy  count
evidence_category                                            
Multi                 2309.02         2158.5      0.46    324
Single                2555.75         2333.0      0.65    176

✓ 圖表已儲存: analysis_results/rag_with_userfact_con_prompt/tokens_analysis.png

================================================================================

--- [6] Multi-Evidence 詳細分析 ---

--------------------------------------------------------------------------------
Multi-Evidence 樣本數: 324 / 500

[6.1] 準確率 vs. Evidence 數量
```
               is_correct       evidence_span
                     mean count          mean
evidence_count                               
2                0.500000   250      0.401130
3                0.365854    41      0.476404
4                0.368421    19      0.672279
5                0.181818    11      0.636521
6                0.333333     3      0.543235
```


[6.2] 準確率 vs. Evidence 跨度
```
                        mean  count
span_bin                           
Small (<0.33)       0.449612    129
Medium (0.33-0.67)  0.487603    121
Large (>0.67)       0.445946     74
```


================================================================================

--- [7] Context Length 分析 ---

--------------------------------------------------------------------------------
```
            is_correct       recall@10
                  mean count      mean
history_bin                           
0-50          0.512626   396  0.751978
50-100        0.586538   104  0.762019
100-150            NaN     0       NaN
150-200            NaN     0       NaN
```


================================================================================
分析完成！

--------------------------------------------------------------------------------
