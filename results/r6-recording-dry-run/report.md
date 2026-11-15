# Real-recording dry run (`r6-recording-dry-run`, commit `4ef5de6`)

Dummy 2-second tone, throwaway folder; `data/real/` not touched; no real clip exists or was read.

| Check | Result |
|---|---|
| record_page_status | 200 |
| real_prompts_by_split | {'test': 180, 'dev': 60} |
| real_prompt_status_counts | {'todo': 240} |
| upload_dev | {'status': 'review', 'transcribed': True, 'wer_reported': True} |
| upload_test | {'status': 'sealed', 'transcribed': False, 'wer_reported': False} |
| import_command | -m scripts.import_real --from-recordings --speaker DRY01 --root <tmp> |
| import_output | imported 1 dev and 1 test take(s) (test is sealed) |
| reimport_output | imported 0 dev and 0 test take(s) (test is sealed) |
| load_real_dev_clips | 1 |
| load_real_test | refused: real test recordings are sealed until the evaluator says so |
| real_data_dir_untouched | True |
| all_ok | True |
