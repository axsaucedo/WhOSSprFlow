# WhOSSpr Flow - Manual End-to-End Test Plan

This document outlines manual testing procedures for validating WhOSSpr Flow functionality. These tests should be run after significant changes to ensure end-to-end functionality works correctly.

## Prerequisites

Before running tests:

1. **Install dependencies:**
   ```bash
   brew install portaudio
   uv sync
   ```

2. **Grant macOS permissions:**
   - Microphone access: Run `uv run whosspr check` and grant when prompted
   - Accessibility access: System Preferences → Security & Privacy → Privacy → Accessibility → Add Terminal

3. **Verify permissions:**
   ```bash
   uv run whosspr check
   ```
   Expected: Both Microphone and Accessibility show "✅ Granted"

---

## Test 1: Basic Startup

**Objective:** Verify the application starts correctly with default settings.

**Debug Command:**
```bash
uv run whosspr start --debug --log-file ./tmp/logs/test1_startup.log
```

**Steps:**
1. Run the command above
2. Observe startup panel showing configuration

**Expected Results:**
- Panel displays with correct version
- Model shows: `base`
- Hold shortcut shows: `ctrl+cmd+1`
- Toggle shortcut shows: `ctrl+cmd+2`
- No errors in output
- Log file created at `./tmp/logs/test1_startup.log`

**Cleanup:** Press `Ctrl+C` to stop

---

## Test 2: Hold-to-Dictate Shortcut

**Objective:** Verify the hold-to-dictate functionality works.

**Debug Command:**
```bash
uv run whosspr start --debug --log-file ./tmp/logs/test2_hold.log
```

**Steps:**
1. Start WhOSSpr with command above
2. Open a text editor (TextEdit, VS Code, etc.)
3. Click to place cursor in the text area
4. Hold `Ctrl+Cmd+1`
5. Speak: "Hello world test one two three"
6. Release the keys

**Expected Results:**
- State changes to "recording" when keys are held
- State changes to "transcribing" when released
- State changes to "inserting" when text is ready
- Text appears in the text editor
- State returns to "idle"
- Console shows: `Transcribed: Hello world...`

**Log Verification:**
```bash
cat ./tmp/logs/test2_hold.log | grep -E "(Recording|Transcri|Insert)"
```

**Cleanup:** Press `Ctrl+C` to stop

---

## Test 3: Toggle Dictation Shortcut

**Objective:** Verify toggle dictation mode works.

**Debug Command:**
```bash
uv run whosspr start --debug --log-file ./tmp/logs/test3_toggle.log
```

**Steps:**
1. Start WhOSSpr with command above
2. Open a text editor
3. Press `Ctrl+Cmd+2` to start recording
4. Speak: "Toggle mode test"
5. Press `Ctrl+Cmd+2` again to stop

**Expected Results:**
- First press: State changes to "recording"
- Speaking is captured
- Second press: State changes to "transcribing" → "inserting"
- Text appears in editor

**Cleanup:** Press `Ctrl+C` to stop

---

## Test 4: Different Model Sizes

**Objective:** Verify different Whisper models work correctly.

**Debug Commands:**
```bash
# Test tiny (fastest)
uv run whosspr start --model tiny --debug --log-file ./tmp/logs/test4_tiny.log

# Test small (better accuracy)
uv run whosspr start --model small --debug --log-file ./tmp/logs/test4_small.log
```

**Steps:**
1. Start with `--model tiny`
2. Test dictation with a simple phrase
3. Stop and restart with `--model small`
4. Test same phrase

**Expected Results:**
- Both models transcribe correctly
- `tiny` is faster but may have lower accuracy
- `small` takes longer but may be more accurate
- Startup panel shows correct model name

---

## Test 5: Text Enhancement (Requires API Key)

**Objective:** Verify LLM text enhancement works.

**Debug Command:**
```bash
export OPENAI_API_KEY=your-api-key-here
uv run whosspr start --enhancement --debug --log-file ./tmp/logs/test5_enhance.log
```

**Or with local LLM (Ollama):**
```bash
uv run whosspr start --enhancement \
  --api-key ollama \
  --api-base-url http://localhost:11434/v1 \
  --debug --log-file ./tmp/logs/test5_enhance_local.log
```

**Steps:**
1. Start with enhancement enabled
2. Speak with filler words: "um so like hello world uh yeah"
3. Release/toggle to transcribe

**Expected Results:**
- State shows "enhancing" after transcription
- Enhanced text is cleaner (filler words removed)
- Console shows both "Transcribed:" and "Enhanced:"

**Log Verification:**
```bash
cat ./tmp/logs/test5_enhance.log | grep -E "(Enhanced|Transcribed)"
```

---

## Test 6: Custom Configuration File

**Objective:** Verify custom config file is loaded correctly.

**Setup:**
```bash
uv run whosspr config --init --path ./tmp/test_config.json
```

**Edit the config to change model:**
```bash
# Manually edit ./tmp/test_config.json to set model_size to "tiny"
```

**Debug Command:**
```bash
uv run whosspr start --config ./tmp/test_config.json --debug --log-file ./tmp/logs/test6_config.log
```

**Expected Results:**
- Startup panel shows the settings from the custom config
- Log shows: `Loading config from ./tmp/test_config.json`

---

## Test 7: Error Handling - Short Recording

**Objective:** Verify short recordings are handled gracefully.

**Debug Command:**
```bash
uv run whosspr start --debug --log-file ./tmp/logs/test7_short.log
```

**Steps:**
1. Start WhOSSpr
2. Press and immediately release `Ctrl+Cmd+1` (very quick tap)

**Expected Results:**
- No crash occurs
- State returns to idle
- Log may show "Recording too short" warning

---

## Test 8: Error Recovery

**Objective:** Verify the application recovers from errors.

**Debug Command:**
```bash
uv run whosspr start --debug --log-file ./tmp/logs/test8_recovery.log
```

**Steps:**
1. Start WhOSSpr
2. Perform a successful dictation
3. If any error occurs, try another dictation

**Expected Results:**
- Application continues working after errors
- State returns to idle
- Subsequent dictations work normally

---

## Troubleshooting

### Logs Not Appearing
Check if the log directory exists:
```bash
ls -la ./tmp/logs/
```

### Permission Errors
Re-run permission check:
```bash
uv run whosspr check
```

### Audio Issues
Test microphone:
```bash
# Check if audio input works
python -c "import pyaudio; p = pyaudio.PyAudio(); print(p.get_device_count(), 'devices found')"
```

### Crash Investigation
When a crash occurs:
1. Check the log file for the test
2. Look for lines with `ERROR` or `EXCEPTION`
3. Check for full stack traces

```bash
# Search for errors in log
grep -E "(ERROR|EXCEPTION|Traceback)" ./tmp/logs/test*.log

# View last 50 lines before crash
tail -50 ./tmp/logs/<test_log>.log
```

---

## Running Automated Tests

In addition to manual testing, run the automated test suite:

```bash
# Run all tests
uv run pytest -v

# Run with coverage
uv run pytest --cov=whosspr

# Run only integration tests
uv run pytest tests/test_integration.py -v

# Run with debug output
uv run pytest -v -s --log-cli-level=DEBUG
```

---

## Test Log Locations

After running tests, logs are saved to:
- `./tmp/logs/test1_startup.log` - Startup test
- `./tmp/logs/test2_hold.log` - Hold-to-dictate test
- `./tmp/logs/test3_toggle.log` - Toggle test
- `./tmp/logs/test4_*.log` - Model tests
- `./tmp/logs/test5_enhance*.log` - Enhancement tests
- `./tmp/logs/test6_config.log` - Config test
- `./tmp/logs/test7_short.log` - Short recording test
- `./tmp/logs/test8_recovery.log` - Recovery test

To archive logs for bug reports:
```bash
tar -czvf whosspr_test_logs_$(date +%Y%m%d).tar.gz ./tmp/logs/
```
