# 實驗分析報告

**生成結果檔案**: `longmemeval_s_cleaned.json_retrievallog_turn_flat-stella.timefilteredgpt-4o_testlog_top50context_jsonformat_useronlyfalse_20251212-1054.jsonl.eval-results-gpt-4o-mini`

**參考答案檔案**: `longmemeval_s_cleaned.json`

---


================================================================================

--- 快速摘要（論文格式）---

--------------------------------------------------------------------------------

評估模型: gpt-4o-mini-2024-07-18

按任務類型的準確率:
  knowledge-update              : 0.7564 (78)
  multi-session                 : 0.3759 (133)
  single-session-assistant      : 0.5357 (56)
  single-session-preference     : 0.3000 (30)
  single-session-user           : 0.8571 (70)
  temporal-reasoning            : 0.3383 (133)

Task-averaged Accuracy: 0.5273
Overall Accuracy:       0.5060
Abstention Accuracy:    0.8667 (30)

================================================================================

--- 詳細分析報告 ---

--------------------------------------------------------------------------------
總樣本數: 500
平均準確率: 0.5060

================================================================================

--- [2] 準確率 vs. 問題類型 ---

--------------------------------------------------------------------------------
```
                          is_correct       recall@10
                                mean count  <lambda>
question_type                                       
knowledge-update            0.756410    78         0
multi-session               0.375940   133         0
single-session-assistant    0.535714    56         0
single-session-preference   0.300000    30         0
single-session-user         0.857143    70         0
temporal-reasoning          0.338346   133         0
```


================================================================================

--- [3] 位置偏差分析（僅 Single-Evidence 樣本）---

--------------------------------------------------------------------------------
Single-Evidence 樣本數: 176 / 500

[3.1] 準確率 vs. Evidence 位置
```
                 is_correct       recall@10
                       mean count  <lambda>
pos_bin                                    
0-20% (Oldest)     0.724138    29         0
20-40%             0.583333    36         0
40-60%             0.480000    25         0
60-80%             0.666667    39         0
80-100% (Newest)   0.638298    47         0
```


✓ 圖表已儲存: analysis_results/rag_with_time/position_bias_single_evidence.png

================================================================================

--- [4] Single-Evidence vs Multi-Evidence 按問題類型分析 ---

--------------------------------------------------------------------------------

[4.1] 整體分布
Single-Evidence: 176 題
Multi-Evidence:  324 題

[4.2] 按問題類型和證據數量分解的準確率
```
                                            is_correct       recall@10 prompt_tokens
                                                  mean count  <lambda>          mean
evidence_category question_type                                                     
Multi             knowledge-update              0.7564    78         0     2096.5385
                  multi-session                 0.3759   133         0     2218.1353
                  temporal-reasoning            0.3009   113         0     2450.2035
Single            single-session-assistant      0.5357    56         0     2937.5714
                  single-session-preference     0.3000    30         0     3051.2333
                  single-session-user           0.8571    70         0     1946.9429
                  temporal-reasoning            0.5500    20         0     2788.8500
```


================================================================================

--- [5] Input Tokens 分析 ---

--------------------------------------------------------------------------------

[5.1] 整體統計
平均 Prompt Tokens: 2367
中位數 Prompt Tokens: 2146
最小值: 1739
最大值: 6095

[5.2] 按答題正確性分組的 Tokens 統計
```
             mean  median  count
Incorrect  2487.0  2229.0    247
Correct    2250.0  2046.0    253
```


[5.3] 按問題類型的 Tokens 統計
                           avg_tokens  median_tokens  accuracy
question_type                                                 
knowledge-update              2096.54         1997.5      0.76
multi-session                 2218.14         2085.0      0.38
single-session-assistant      2937.57         2814.5      0.54
single-session-preference     3051.23         2924.5      0.30
single-session-user           1946.94         1874.5      0.86
temporal-reasoning            2501.13         2255.0      0.34

[5.4] 按 Evidence 數量的 Tokens 統計
                   avg_tokens  median_tokens  accuracy  count
evidence_category                                            
Multi                 2269.80         2113.0      0.44    324
Single                2546.05         2321.0      0.62    176

✓ 圖表已儲存: analysis_results/rag_with_time/tokens_analysis.png

================================================================================

--- [6] Multi-Evidence 詳細分析 ---

--------------------------------------------------------------------------------
Multi-Evidence 樣本數: 324 / 500

[6.1] 準確率 vs. Evidence 數量
```
               is_correct       evidence_span
                     mean count          mean
evidence_count                               
2                0.468000   250      0.401130
3                0.414634    41      0.476404
4                0.315789    19      0.672279
5                0.181818    11      0.636521
6                0.333333     3      0.543235
```


[6.2] 準確率 vs. Evidence 跨度
```
                        mean  count
span_bin                           
Small (<0.33)       0.403101    129
Medium (0.33-0.67)  0.479339    121
Large (>0.67)       0.445946     74
```


================================================================================

--- [7] Context Length 分析 ---

--------------------------------------------------------------------------------
```
            is_correct       recall@10
                  mean count  <lambda>
history_bin                           
0-50          0.489899   396         0
50-100        0.567308   104         0
100-150            NaN     0         0
150-200            NaN     0         0
```


================================================================================
分析完成！

--------------------------------------------------------------------------------
