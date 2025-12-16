# 實驗分析報告

**生成結果檔案**: `longmemeval_oracle.json_testlog_top1000context_jsonformat_useronlyfalse_20251215-0646.jsonl.eval-results-gpt-4o-mini`

**參考答案檔案**: `longmemeval_oracle.json`

---


================================================================================

--- 快速摘要（論文格式）---

--------------------------------------------------------------------------------

評估模型: gpt-4o-mini-2024-07-18

按任務類型的準確率:
  knowledge-update              : 0.7179 (78)
  multi-session                 : 0.4511 (133)
  single-session-assistant      : 0.9821 (56)
  single-session-preference     : 0.4667 (30)
  single-session-user           : 0.8857 (70)
  temporal-reasoning            : 0.5263 (133)

Task-averaged Accuracy: 0.6717
Overall Accuracy:       0.6340
Abstention Accuracy:    0.7333 (30)

================================================================================

--- 詳細分析報告 ---

--------------------------------------------------------------------------------
總樣本數: 500
平均準確率: 0.6340

================================================================================

--- [2] 準確率 vs. 問題類型 ---

--------------------------------------------------------------------------------
```
                          is_correct       recall@10
                                mean count  <lambda>
question_type                                       
knowledge-update            0.717949    78         0
multi-session               0.451128   133         0
single-session-assistant    0.982143    56         0
single-session-preference   0.466667    30         0
single-session-user         0.885714    70         0
temporal-reasoning          0.526316   133         0
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
0-20% (Oldest)          NaN     0         0
20-40%                  NaN     0         0
40-60%             0.835227   176         0
60-80%                  NaN     0         0
80-100% (Newest)        NaN     0         0
```


✓ 圖表已儲存: analysis_results/oracle_fullhistory_cot/position_bias_single_evidence.png

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
Multi             knowledge-update              0.7179    78         0     6641.0256
                  multi-session                 0.4511   133         0     8736.1955
                  temporal-reasoning            0.4779   113         0     8343.4690
Single            single-session-assistant      0.9821    56         0     1425.8750
                  single-session-preference     0.4667    30         0     4406.8000
                  single-session-user           0.8857    70         0     3421.7143
                  temporal-reasoning            0.8000    20         0     3546.0500
```


================================================================================

--- [5] Input Tokens 分析 ---

--------------------------------------------------------------------------------

[5.1] 整體統計
平均 Prompt Tokens: 6290
中位數 Prompt Tokens: 6324
最小值: 268
最大值: 24146

[5.2] 按答題正確性分組的 Tokens 統計
```
             mean  median  count
Incorrect  8065.0  7161.0    183
Correct    5266.0  5305.0    317
```


[5.3] 按問題類型的 Tokens 統計
                           avg_tokens  median_tokens  accuracy
question_type                                                 
knowledge-update              6641.03         6552.0      0.72
multi-session                 8736.20         7331.0      0.45
single-session-assistant      1425.88         1325.5      0.98
single-session-preference     4406.80         4302.5      0.47
single-session-user           3421.71         3559.0      0.89
temporal-reasoning            7622.05         7195.0      0.53

[5.4] 按 Evidence 數量的 Tokens 統計
                   avg_tokens  median_tokens  accuracy  count
evidence_category                                            
Multi                 8094.83         7161.0      0.52    324
Single                2968.72         3182.5      0.84    176

✓ 圖表已儲存: analysis_results/oracle_fullhistory_cot/tokens_analysis.png

================================================================================

--- [6] Multi-Evidence 詳細分析 ---

--------------------------------------------------------------------------------
Multi-Evidence 樣本數: 324 / 500

[6.1] 準確率 vs. Evidence 數量
```
               is_correct       evidence_span
                     mean count          mean
evidence_count                               
2                0.588000   250      0.500000
3                0.390244    41      0.666667
4                0.263158    19      0.750000
5                0.181818    11      0.800000
6                0.000000     3      0.833333
```


[6.2] 準確率 vs. Evidence 跨度
```
                        mean  count
span_bin                           
Small (<0.33)       0.588000    250
Medium (0.33-0.67)  0.390244     41
Large (>0.67)       0.212121     33
```


================================================================================

--- [7] Context Length 分析 ---

--------------------------------------------------------------------------------
```
            is_correct       recall@10
                  mean count  <lambda>
history_bin                           
0-50             0.634   500         0
50-100             NaN     0         0
100-150            NaN     0         0
150-200            NaN     0         0
```


================================================================================
分析完成！

--------------------------------------------------------------------------------
