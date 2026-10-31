#!/usr/bin/env bash
# Fetch every model and dataset the app needs, so the demo runs fully offline afterwards.
# Usage: conda activate anpr && bash scripts/download_assets.sh
set -euo pipefail
cd "$(dirname "$0")/.."
M=models; D=data/raw

echo "== ASR: faster-whisper (CTranslate2) =="
hf download Systran/faster-whisper-small.en  --local-dir $M/asr/faster-whisper-small.en
hf download Systran/faster-whisper-medium.en --local-dir $M/asr/faster-whisper-medium.en
hf download Systran/faster-whisper-small     --local-dir $M/asr/faster-whisper-small   # multilingual, for Hinglish ablation

echo "== LLM: 3-4B instruct, Q4_K_M GGUF (primary + backup) =="
hf download unsloth/Qwen3-4B-Instruct-2507-GGUF Qwen3-4B-Instruct-2507-Q4_K_M.gguf --local-dir $M/llm
hf download bartowski/Llama-3.2-3B-Instruct-GGUF Llama-3.2-3B-Instruct-Q4_K_M.gguf --local-dir $M/llm

echo "== NER base model =="
hf download distilbert/distilbert-base-cased config.json tokenizer.json tokenizer_config.json vocab.txt model.safetensors \
  --local-dir $M/ner/distilbert-base-cased

echo "== Piper TTS voices (read-back + augmentation; l2arctic/vctk include Indian speakers) =="
for v in en/en_US/lessac/medium en/en_US/ryan/medium en/en_US/amy/medium en/en_US/kusal/medium \
         en/en_US/l2arctic/medium en/en_US/libritts_r/medium en/en_GB/alan/medium en/en_GB/vctk/medium \
         en/en_GB/southern_english_female/low hi/hi_IN/pratham/medium hi/hi_IN/priyamvada/medium hi/hi_IN/rohan/medium; do
  IFS=/ read -r _ loc spk q <<< "$v"; f="$v/$loc-$spk-$q"
  hf download rhasspy/piper-voices "$f.onnx" "$f.onnx.json" --local-dir $M/tts
done

echo "== Noise: ESC-50 (sirens, engines, etc.) =="
if [ ! -d $D/ESC-50-master ]; then
  curl -sSL -o $D/esc50.zip https://github.com/karoldvl/ESC-50/archive/master.zip
  unzip -q $D/esc50.zip -d $D && rm $D/esc50.zip
fi

echo "== Accent eval: Svarah (Indian-accented English) — optional, may be gated =="
hf download ai4bharat/Svarah --repo-type dataset --local-dir $D/svarah || echo "Svarah unavailable (gated?) — skipping"

echo "done"; du -sh $M $D
