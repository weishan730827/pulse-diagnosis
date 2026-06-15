#!/bin/bash
# v4.0 双轨辨证自动运行入口
# 用法: ./run.sh "左寸浮紧,左关中弦,左尺沉弱,右寸浮濡,右关弦,右尺沉微"
# 或管道: echo "左寸浮紧,左关中弦,左尺沉弱,右寸浮濡,右关弦,右尺沉微" | ./run.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PULSES="${1:-$(cat)}"

if [ -z "$PULSES" ]; then
    echo "用法: ./run.sh \"左寸浮紧,左关中弦,左尺沉弱,右寸浮濡,右关弦,右尺沉微\""
    exit 1
fi

python dual_track_pipeline_v4.py --pulses "$PULSES"
