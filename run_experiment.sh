#!/usr/bin/env bash

# ============================================
# LongMemEval 統一實驗腳本
# 使用參數控制不同的實驗配置
# ============================================

set -e

export HOME_DIR=/home/yhchiang/LongMemEval
export PYTHONPATH=${PYTHONPATH}:${HOME_DIR}

# 載入 .env 文件（如果存在）
if [ -f "${HOME_DIR}/.env" ]; then
    export $(grep -v '^#' ${HOME_DIR}/.env | xargs)
fi

# 顏色輸出
GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================
# 使用說明
# ============================================

show_usage() {
    cat << EOF
用法: $0 [選項]

選項:
  -d, --data DATA          數據集 (s|oracle|m)
                           s = longmemeval_s_cleaned.json
                           oracle = longmemeval_oracle.json
                           m = longmemeval_m_cleaned.json

  -m, --method METHOD      方法 (rag|fullhistory)
                           rag = 檢索增強生成
                           fullhistory = 直接輸入所有歷史

  -r, --retriever RET      檢索器 (bm25|stella|contriever)
                           僅 rag 方法需要

  -e, --expansion EXP      Index Expansion (none|userfact|keyphrase|summ)
                           僅 rag 方法需要
                           注意: Turn 級別只支持 userfact, keyphrase

  -t, --reading TYPE       閱讀方法 (direct|cot|con)
                           direct = 直接回答
                           cot = Chain-of-Thought
                           con = Chain-of-Note (論文最佳)

  -k, --topk K             Top-K 檢索數量 (預設: 50，論文設定)
  
  -g, --granularity GRAN   檢索粒度 (turn|session)
                           預設: turn (論文 Figure 5 顯示 Turn 更好)

  --time-aware             啟用 Time-Aware Query Expansion
                           (僅對 temporal-reasoning 任務有效)
                           需要時間戳事件檔案

  --model MODEL            生成模型 (預設: llama3.1:8b-128k)
  --eval-model EVAL        評估模型 (預設: gpt-4o-mini)
  --skip-retrieval         跳過檢索步驟
  --skip-generation        跳過生成步驟
  --skip-evaluation        跳過評估步驟
  --resume                 啟用斷點續傳（生成階段會跳過已處理的問題）

  -h, --help               顯示此幫助信息

範例:
  # RAG 最佳配置（論文設定：Turn 粒度 + User Fact + CoN）
  $0 -d s -m rag -r stella -e userfact -t con -g turn

  # Full History
  $0 -d oracle -m fullhistory -t cot

  # BM25 基礎配置
  $0 -d oracle -m rag -r bm25 -t cot

  # Session 粒度（如果想測試）
  $0 -d s -m rag -r stella -e userfact -t con -g session

EOF
}

# ============================================
# 參數解析
# ============================================

# 預設值（根據論文最佳配置）
DATA="oracle"
METHOD="rag"
RETRIEVER="stella"
EXPANSION="userfact"
READING="con"
TOPK=50  # 論文預設
GRANULARITY="turn"  # 論文 Figure 5: Turn 優於 Session
TIME_AWARE=false  # Time-Aware Query Expansion
MODEL="llama3.1:8b-128k"
EVAL_MODEL="gpt-4o-mini"
SKIP_RETRIEVAL=false
SKIP_GENERATION=false
SKIP_EVALUATION=false
RESUME=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--data) DATA="$2"; shift 2 ;;
        -m|--method) METHOD="$2"; shift 2 ;;
        -r|--retriever) RETRIEVER="$2"; shift 2 ;;
        -e|--expansion) EXPANSION="$2"; shift 2 ;;
        -t|--reading) READING="$2"; shift 2 ;;
        -k|--topk) TOPK="$2"; shift 2 ;;
        -g|--granularity) GRANULARITY="$2"; shift 2 ;;
        --time-aware) TIME_AWARE=true; shift ;;
        --model) MODEL="$2"; shift 2 ;;
        --eval-model) EVAL_MODEL="$2"; shift 2 ;;
        --skip-retrieval) SKIP_RETRIEVAL=true; shift ;;
        --skip-generation) SKIP_GENERATION=true; shift ;;
        --skip-evaluation) SKIP_EVALUATION=true; shift ;;
        --resume) RESUME=true; shift ;;
        -h|--help) show_usage; exit 0 ;;
        *) echo_error "未知參數: $1"; show_usage; exit 1 ;;
    esac
done

# ============================================
# 配置驗證和設置
# ============================================

# 數據文件映射
case $DATA in
    s) DATA_FILE="${HOME_DIR}/data/longmemeval_s_cleaned.json" ;;
    oracle) DATA_FILE="${HOME_DIR}/data/longmemeval_oracle.json" ;;
    m) DATA_FILE="${HOME_DIR}/data/longmemeval_m_cleaned.json" ;;
    *) echo_error "無效的數據集: $DATA"; exit 1 ;;
esac

# 檢查數據文件
if [ ! -f "$DATA_FILE" ]; then
    echo_error "數據文件不存在: $DATA_FILE"
    exit 1
fi

# 模型配置
MODEL_ALIAS=$(echo $MODEL | sed 's/:/-/g' | sed 's/\//-/g')
OLLAMA_BASE_URL="http://localhost:11434/v1"
OLLAMA_API_KEY="ollama"

# 檢索器配置
if [ "$METHOD" = "rag" ]; then
    case $RETRIEVER in
        bm25) RETRIEVER_NAME="flat-bm25" ;;
        stella) RETRIEVER_NAME="flat-stella" ;;
        contriever) RETRIEVER_NAME="flat-contriever" ;;
        *) echo_error "無效的檢索器: $RETRIEVER"; exit 1 ;;
    esac
    
    # 驗證粒度
    if [ "$GRANULARITY" != "turn" ] && [ "$GRANULARITY" != "session" ]; then
        echo_error "無效的粒度: $GRANULARITY (應為 turn 或 session)"
        exit 1
    fi
fi

# Index Expansion 配置
if [ "$METHOD" = "rag" ] && [ "$EXPANSION" != "none" ]; then
    # 根據粒度選擇對應的 expansion
    if [ "$GRANULARITY" = "turn" ]; then
        case $EXPANSION in
            userfact)
                EXPANSION_TYPE="turn-userfact"
                EXPANSION_CACHE="${HOME_DIR}/index_expansion_logs/merged_cache_turn-userfact_llama-3.1-8b-instruct_ICL.json"
                ;;
            keyphrase)
                EXPANSION_TYPE="turn-keyphrase"
                EXPANSION_CACHE="${HOME_DIR}/index_expansion_logs/merged_cache_turn-keyphrase_llama-3.1-8b-instruct_zeroshot.json"
                ;;
            *)
                echo_error "Turn 級別不支持 $EXPANSION expansion"
                echo_info "Turn 級別支持: userfact, keyphrase"
                exit 1
                ;;
        esac
    else
        # Session 級別
        case $EXPANSION in
            userfact)
                EXPANSION_TYPE="session-userfact"
                EXPANSION_CACHE="${HOME_DIR}/index_expansion_logs/merged_cache_session-userfact_llama-3.1-8b-instruct_ICL.json"
                ;;
            keyphrase)
                EXPANSION_TYPE="session-keyphrase"
                EXPANSION_CACHE="${HOME_DIR}/index_expansion_logs/merged_cache_session-keyphrase_llama-3.1-8b-instruct_zeroshot.json"
                ;;
            summ)
                EXPANSION_TYPE="session-summ"
                EXPANSION_CACHE="${HOME_DIR}/index_expansion_logs/merged_cache_session-summ_llama-3.1-8b-instruct_zeroshot.json"
                ;;
            *) echo_error "無效的 expansion: $EXPANSION"; exit 1 ;;
        esac
    fi
    EXPANSION_JOIN_MODE="merge"
    
    if [ ! -f "$EXPANSION_CACHE" ]; then
        echo_error "Index Expansion 緩存不存在: $EXPANSION_CACHE"
        echo_info "將不使用 Index Expansion"
        EXPANSION="none"
    fi
fi

# 閱讀方法配置
case $READING in
    direct) COT="false"; CON="false" ;;
    cot) COT="true"; CON="false" ;;
    con) COT="true"; CON="true" ;;
    *) echo_error "無效的閱讀方法: $READING"; exit 1 ;;
esac

# ============================================
# 顯示配置
# ============================================

echo_info "=========================================="
echo_info "實驗配置"
echo_info "=========================================="
echo "數據集: $DATA ($DATA_FILE)"
echo "方法: $METHOD"
if [ "$METHOD" = "rag" ]; then
    echo "檢索器: $RETRIEVER"
    echo "Index Expansion: $EXPANSION"
    echo "Top-K: $TOPK"
fi
    echo "閱讀方法: $READING"
    echo "生成模型: $MODEL"
    echo "評估模型: $EVAL_MODEL"
    if [ "$RESUME" = true ]; then
        echo "斷點續傳: 啟用（將跳過已處理的問題）"
    else
        echo "斷點續傳: 關閉（將覆蓋已存在的檔案）"
    fi
    echo_info "=========================================="
    echo ""

# ============================================
# 環境檢查
# ============================================

check_environment() {
    echo_info "檢查環境..."
    
    # 檢查 Ollama
    if ! ollama list | grep -q "$MODEL"; then
        echo_error "Ollama 模型未安裝: $MODEL"
        exit 1
    fi
    
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo_error "Ollama 服務未運行，請運行: ollama serve"
        exit 1
    fi
    
    # 檢查 API Key（如果需要評估）
    if [ "$SKIP_EVALUATION" = false ] && [ -z "${OPENAI_API_KEY}" ]; then
        echo_error "未設置 OPENAI_API_KEY"
        echo_info "請在 .env 文件中設置或手動輸入"
        read -p "OpenAI API Key: " OPENAI_API_KEY
        export OPENAI_API_KEY
    fi
    
    # 設置 OPENAI_ORGANIZATION（如果有）
    if [ -n "${OPENAI_ORGANIZATION}" ]; then
        export OPENAI_ORGANIZATION
    fi
    
    echo_info "✓ 環境檢查完成"
    echo ""
}

# ============================================
# 步驟 1: 檢索
# ============================================

run_retrieval() {
    if [ "$METHOD" != "rag" ] || [ "$SKIP_RETRIEVAL" = true ]; then
        return
    fi
    
    echo_info "=========================================="
    echo_info "步驟 1: 記憶檢索"
    echo_info "=========================================="
    
    cd ${HOME_DIR}/src/retrieval
    
    if [ "$EXPANSION" != "none" ]; then
        bash run_retrieval.sh \
            "$DATA_FILE" \
            "$RETRIEVER_NAME" \
            "$GRANULARITY" \
            "$EXPANSION_TYPE" \
            "$EXPANSION_JOIN_MODE" \
            "$EXPANSION_CACHE" \
            "llama-3.1-8b-instruct"
    else
        bash run_retrieval.sh \
            "$DATA_FILE" \
            "$RETRIEVER_NAME" \
            "$GRANULARITY"
    fi
    
    # Time-Aware Query Expansion（如果啟用）
    if [ "$TIME_AWARE" = true ]; then
        echo_info "------------------------------------------"
        echo_info "步驟 1.5: Time-Aware Query Expansion"
        echo_info "------------------------------------------"
        
        # 檢查時間戳事件檔案
        TIMESTAMP_FILE="${HOME_DIR}/index_expansion_logs/longmemeval_${GRANULARITY}_timestamped_events.json"
        if [ ! -f "$TIMESTAMP_FILE" ]; then
            echo_error "時間戳事件檔案不存在: $TIMESTAMP_FILE"
            echo_info "請執行: ./download_timestamped_events.sh"
            exit 1
        fi
        
        # 找到檢索結果檔案
        if [ "$EXPANSION" != "none" ]; then
            RETRIEVAL_DIR="${HOME_DIR}/retrieval_logs/${RETRIEVER_NAME}_expansion_w_${EXPANSION_TYPE}/llama-3.1-8b-instruct/joinmode${EXPANSION_JOIN_MODE}"
        else
            RETRIEVAL_DIR="${HOME_DIR}/retrieval_logs/${RETRIEVER_NAME}/${GRANULARITY}"
        fi
        RETRIEVAL_LOG=$(ls -t ${RETRIEVAL_DIR}/*$(basename $DATA_FILE)* 2>/dev/null | head -1)
        
        if [ -z "$RETRIEVAL_LOG" ]; then
            echo_error "找不到檢索結果檔案"
            exit 1
        fi
        
        echo_info "輸入檢索日誌: $(basename $RETRIEVAL_LOG)"
        echo_info "時間戳事件: $(basename $TIMESTAMP_FILE)"
        
        cd ${HOME_DIR}/src/index_expansion
        python3 temp_query_search_pruning.py \
            "$TIMESTAMP_FILE" \
            "$RETRIEVAL_LOG" \
            "$GRANULARITY"
        
        echo_info "✓ Time-Aware 過濾完成"
    fi
    
    echo ""
}

# ============================================
# 步驟 2: 生成
# ============================================

run_generation() {
    if [ "$SKIP_GENERATION" = true ]; then
        return
    fi
    
    echo_info "=========================================="
    echo_info "步驟 2: 生成答案"
    echo_info "=========================================="
    
    # 確定輸入文件
    if [ "$METHOD" = "rag" ]; then
        # 找到檢索結果
        if [ "$EXPANSION" != "none" ]; then
            RETRIEVAL_DIR="${HOME_DIR}/retrieval_logs/${RETRIEVER_NAME}_expansion_w_${EXPANSION_TYPE}/llama-3.1-8b-instruct/joinmode${EXPANSION_JOIN_MODE}"
        else
            RETRIEVAL_DIR="${HOME_DIR}/retrieval_logs/${RETRIEVER_NAME}/${GRANULARITY}"
        fi
        INPUT_FILE=$(ls -t ${RETRIEVAL_DIR}/*$(basename $DATA_FILE)* 2>/dev/null | head -1)
        
        if [ -z "$INPUT_FILE" ]; then
            echo_error "找不到檢索結果"
            exit 1
        fi
        
        RETRIEVER_TYPE="flat-${GRANULARITY}"
    else
        # Full History
        INPUT_FILE="$DATA_FILE"
        RETRIEVER_TYPE="orig-session"
        TOPK=1000
    fi
    
    # 輸出目錄
    # 包含所有關鍵設定：METHOD, RETRIEVER, EXPANSION, GRANULARITY, READING
    if [ "$METHOD" = "rag" ]; then
        EXP_NAME="${METHOD}_${RETRIEVER}_${EXPANSION}_${GRANULARITY}"
    else
        EXP_NAME="${METHOD}_${RETRIEVER:-fullhistory}_${EXPANSION:-none}"
    fi
    OUT_DIR="${HOME_DIR}/generation_logs/${EXP_NAME}/${MODEL_ALIAS}/${READING}"
    mkdir -p "$OUT_DIR"
    
    echo_info "輸入: $INPUT_FILE"
    echo_info "輸出: $OUT_DIR"
    
    cd ${HOME_DIR}/src/generation
    
    RESUME_FLAG=""
    if [ "$RESUME" = true ]; then
        RESUME_FLAG="--resume"
        echo_info "啟用斷點續傳模式"
    fi
    
    python3 run_generation.py \
        --in_file "$INPUT_FILE" \
        --out_dir "$OUT_DIR" \
        --model_name "$MODEL" \
        --model_alias "$MODEL_ALIAS" \
        --openai_base_url "$OLLAMA_BASE_URL" \
        --openai_key "$OLLAMA_API_KEY" \
        --retriever_type "$RETRIEVER_TYPE" \
        --topk_context "$TOPK" \
        --history_format json \
        --useronly false \
        --cot "$COT" \
        --con "$CON" \
        --merge_key_expansion_into_value none \
        $RESUME_FLAG \
        $RESUME_FLAG
    
    echo ""
}

# ============================================
# 步驟 3: 評估
# ============================================

run_evaluation() {
    if [ "$SKIP_EVALUATION" = true ]; then
        return
    fi
    
    echo_info "=========================================="
    echo_info "步驟 3: 評估結果"
    echo_info "=========================================="
    
    # 與生成步驟保持一致的路徑命名
    if [ "$METHOD" = "rag" ]; then
        EXP_NAME="${METHOD}_${RETRIEVER}_${EXPANSION}_${GRANULARITY}"
    else
        EXP_NAME="${METHOD}_${RETRIEVER:-fullhistory}_${EXPANSION:-none}"
    fi
    GEN_DIR="${HOME_DIR}/generation_logs/${EXP_NAME}/${MODEL_ALIAS}/${READING}"
    
    HYPO_FILE=$(ls -t ${GEN_DIR}/*.jsonl 2>/dev/null | head -1)
    
    if [ -z "$HYPO_FILE" ]; then
        echo_error "找不到生成結果"
        exit 1
    fi
    
    cd ${HOME_DIR}/src/evaluation
    
    echo_info "評估: $HYPO_FILE"
    python3 evaluate_qa.py "$EVAL_MODEL" "$HYPO_FILE" "$DATA_FILE"
    
    LOG_FILE="${HYPO_FILE}.log"
    if [ -f "$LOG_FILE" ]; then
        echo ""
        echo_info "結果:"
        python3 print_qa_metrics.py "$LOG_FILE" "$DATA_FILE"
    fi
    
    echo ""
}

# ============================================
# 主流程
# ============================================

main() {
    check_environment
    run_retrieval
    run_generation
    run_evaluation
    
    echo_info "=========================================="
    echo_info "實驗完成！"
    echo_info "=========================================="
}

main "$@"

