# Tools

This folder keeps helper scripts out of the project root.

## `tools/dev`

Development and verification helpers:

- `run_tests.cmd`
- `run_tests.ps1`
- `run_harness_comparison.cmd`
- `run_builder_demo.cmd`
- `run_web.ps1`

## `tools/gpu`

GPU / Local LLM Node helpers:

- `upload_gpu_api_update.cmd`
- `start_gpu_local_llm_api.cmd`
- `open_gpu_local_llm_tunnel.cmd`
- `verify_gpu_remote_node.cmd`
- `run_local_llm_remote_demo.cmd`
- `run_gpu_replay_demo.cmd`
- `run_final_base_benchmark.cmd`
- `download_final_base_benchmark.cmd`

Recommended stable demo:

```bat
tools\gpu\run_gpu_replay_demo.cmd
```

Live API mode is experimental because it depends on SSH tunnel state, GPU
process state, CUDA memory state, and remote server availability.

Final baseline evidence collection:

```bat
tools\gpu\run_final_base_benchmark.cmd
tools\gpu\download_final_base_benchmark.cmd
```

Keep the root directory for the main user-facing launchers:

- `run_builder_app.cmd`
- `run_desktop.cmd`
- `run_web.cmd`
- `run_verify.cmd`
