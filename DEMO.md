# Build in Public - Hackathon Demo Guide (2-3 Minutes)

This step-by-step guide walks through demonstrating the **Build in Public Automated Content Creator** during a hackathon or presentation.

---

## Pre-Demo Setup

1. Open PowerShell terminal in the project directory.
2. Ensure dependencies are installed:
   ```powershell
   python -m pip install --no-build-isolation --no-deps -e .
   ```
3. Ensure `.env` is set up with a valid `GEMINI_API_KEY`:
   ```powershell
   Copy-Item .env.example .env
   ```

---

## 2-3 Minute Live Demo Script

### Step 1: Scan Unprocessed Commits (15 seconds)
Show how the application inspects local repository activity:
```powershell
buildinpublic scan
```
**Talk Track:** *"Build in Public automatically tracks local Git commits. Notice how it extracts SHA, commit author, timestamps, diff stats, and flags commits that haven't been published yet."*

---

### Step 2: Generate X & LinkedIn Drafts (45 seconds)
Generate social media posts using Gemini LLM:
```powershell
buildinpublic generate
```
**Talk Track:** *"With one command, Gemini analyzes the actual Git message and changed file statistics to produce two formatted updates: a short, snappy tweet with hashtags for X, and a structured, professional narrative for LinkedIn."*

---

### Step 3: Verify History & Duplicate Prevention (30 seconds)
Mark the commit as processed and verify duplicate prevention:
```powershell
buildinpublic generate --mark-processed
buildinpublic scan
buildinpublic history
```
**Talk Track:** *"Notice that once content is generated and published, the commit is recorded in our local history file. Re-running `scan` now confirms that no unprocessed commits remain, ensuring we never post about the same commit twice."*

---

### Step 4: Background Watcher Daemon (30 seconds)
Demonstrate background automated polling:
```powershell
buildinpublic start --interval 5
```
*(Press `Ctrl+C` after 10 seconds to cleanly shut down)*

**Talk Track:** *"In daemon mode, the utility runs in the background while you code. Whenever you commit new work, it automatically generates social media drafts in dry-run mode and handles graceful shutdowns on Ctrl+C."*

---

## Key Talking Points for Judges
1. **Factual Grounding:** Prompts strictly instruct Gemini not to fabricate features outside the Git diff.
2. **Failure Safety:** Commits remain unprocessed if an API call fails, enabling zero-loss retries.
3. **Modular & Lightweight:** Zero server infrastructure, zero database servers; runs anywhere Python runs.
