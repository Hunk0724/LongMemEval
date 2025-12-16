# 實驗分析報告

**生成結果檔案**: `longmemeval_oracle.json_testlog_top1000context_jsonformat_useronlyfalse_20251215-1521.jsonl.eval-results-gpt-4o-mini`

**參考答案檔案**: `longmemeval_oracle.json`

---


================================================================================

--- 快速摘要（論文格式）---

--------------------------------------------------------------------------------

評估模型: gpt-4o-mini-2024-07-18

按任務類型的準確率:
  knowledge-update              : 0.8077 (78)
  multi-session                 : 0.4361 (133)
  single-session-assistant      : 0.8750 (56)
  single-session-preference     : 0.5333 (30)
  single-session-user           : 0.8286 (70)
  temporal-reasoning            : 0.4436 (133)

Task-averaged Accuracy: 0.6540
Overall Accuracy:       0.6060
Abstention Accuracy:    0.9333 (30)

================================================================================

--- 詳細分析報告 ---

--------------------------------------------------------------------------------
總樣本數: 500
平均準確率: 0.6060

================================================================================

--- [2] 準確率 vs. 問題類型 ---

--------------------------------------------------------------------------------
```
                          is_correct       recall@10
                                mean count  <lambda>
question_type                                       
knowledge-update            0.807692    78         0
multi-session               0.436090   133         0
single-session-assistant    0.875000    56         0
single-session-preference   0.533333    30         0
single-session-user         0.828571    70         0
temporal-reasoning          0.443609   133         0
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
40-60%             0.767045   176         0
60-80%                  NaN     0         0
80-100% (Newest)        NaN     0         0
```


✓ 圖表已儲存: analysis_results/oracle_fullhistory_con2/position_bias_single_evidence.png

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
Multi             knowledge-update              0.8077    78         0      288.2692
                  multi-session                 0.4361   133         0      390.3083
                  temporal-reasoning            0.4159   113         0      414.4602
Single            single-session-assistant      0.8750    56         0      240.7500
                  single-session-preference     0.5333    30         0      270.6333
                  single-session-user           0.8286    70         0      175.0857
                  temporal-reasoning            0.6000    20         0      255.2000
```


================================================================================

--- [5] Input Tokens 分析 ---

--------------------------------------------------------------------------------

[5.1] 整體統計
平均 Prompt Tokens: 320
中位數 Prompt Tokens: 287
最小值: 121
最大值: 1167

[5.2] 按答題正確性分組的 Tokens 統計
```
            mean  median  count
Incorrect  375.0   322.0    197
Correct    285.0   264.0    303
```


[5.3] 按問題類型的 Tokens 統計
                           avg_tokens  median_tokens  accuracy
question_type                                                 
knowledge-update               288.27          282.5      0.81
multi-session                  390.31          361.0      0.44
single-session-assistant       240.75          237.0      0.88
single-session-preference      270.63          271.0      0.53
single-session-user            175.09          178.0      0.83
temporal-reasoning             390.51          336.0      0.44

[5.4] 按 Evidence 數量的 Tokens 統計
                   avg_tokens  median_tokens  accuracy  count
evidence_category                                            
Multi                  374.17          330.5      0.52    324
Single                 221.37          214.0      0.77    176

✓ 圖表已儲存: analysis_results/oracle_fullhistory_con2/tokens_analysis.png

================================================================================

--- [6] Multi-Evidence 詳細分析 ---

--------------------------------------------------------------------------------
Multi-Evidence 樣本數: 324 / 500

[6.1] 準確率 vs. Evidence 數量
```
               is_correct       evidence_span
                     mean count          mean
evidence_count                               
2                0.560000   250      0.500000
3                0.365854    41      0.666667
4                0.473684    19      0.750000
5                0.363636    11      0.800000
6                0.000000     3      0.833333
```


[6.2] 準確率 vs. Evidence 跨度
```
                        mean  count
span_bin                           
Small (<0.33)       0.560000    250
Medium (0.33-0.67)  0.365854     41
Large (>0.67)       0.393939     33
```


================================================================================

--- [7] Context Length 分析 ---

--------------------------------------------------------------------------------
```
            is_correct       recall@10
                  mean count  <lambda>
history_bin                           
0-50             0.606   500         0
50-100             NaN     0         0
100-150            NaN     0         0
150-200            NaN     0         0
```


================================================================================
分析完成！

--------------------------------------------------------------------------------
