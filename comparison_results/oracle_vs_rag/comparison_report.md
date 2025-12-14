# 實驗比較報告

**參考答案檔案**: `longmemeval_s_cleaned.json`

**實驗列表**:

- **Oracle_FullHistory**: `longmemeval_oracle.json_testlog_top1000context_jsonformat_useronlyfalse_20251212-0248.jsonl.eval-results-gpt-4o-mini`
- **RAG_Turn_K50**: `longmemeval_s_cleaned.json_retrievallog_turn_flat-stella_testlog_top50context_jsonformat_useronlyfalse_20251212-0340.jsonl.eval-results-gpt-4o-mini`

---


=== Overall Accuracy ===
```
           Experiment  is_correct
0  Oracle_FullHistory       0.608
1        RAG_Turn_K50       0.528

=== [2] Task Type Analysis ===

[2.1] Sample Count:
question_type       knowledge-update  multi-session  ...  single-session-user  temporal-reasoning
Experiment                                           ...                                         
Oracle_FullHistory                78            133  ...                   70                 133
RAG_Turn_K50                      78            133  ...                   70                 133

[2 rows x 6 columns]

[2.2] Accuracy:
Experiment                 Oracle_FullHistory  RAG_Turn_K50
question_type                                              
knowledge-update                     0.807692      0.769231
multi-session                        0.451128      0.390977
single-session-assistant             0.875000      0.535714
single-session-preference            0.433333      0.300000
single-session-user                  0.871429      0.900000
temporal-reasoning                   0.436090      0.375940

=== [3] Position Bias Analysis (Single-Evidence Only) ===

Analyzed samples: 352 / 1000

[3.1] Question Type Breakdown:
question_type       single-session-assistant  single-session-preference  single-session-user  temporal-reasoning
Experiment                                                                                                      
Oracle_FullHistory                        56                         30                   70                  20
RAG_Turn_K50                              56                         30                   70                  20

[3.2] Accuracy by Position Bin:
Experiment  Oracle_FullHistory  RAG_Turn_K50
pos_bin                                     
0-20%                 0.862069      0.758621
20-40%                0.777778      0.638889
40-60%                0.800000      0.480000
60-80%                0.666667      0.692308
80-100%               0.787234      0.659574

[Info] No token usage data found in logs.
```
