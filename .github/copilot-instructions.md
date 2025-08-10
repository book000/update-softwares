# update-softwares

**CRITICAL: Always follow these instructions completely and precisely. Only resort to additional search or context gathering if the information provided here is incomplete or found to be in error.**

Software update automation tool that manages package updates for Linux (apt) and Windows (scoop) systems. The application integrates with GitHub Issues API to track and report update progress in table format across multiple machines.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## 日本語コミュニケーション要件

すべてのコミュニケーションは日本語で行ってください。

### Issue および PR の記述要件

- **Issue タイトル・本文**: 日本語で記述
- **PR タイトル・本文**: 日本語で記述（Conventional Commits の仕様に従う）
- **コミットメッセージ**: 日本語で記述（Conventional Commits の仕様に従う）
- **レビューコメント**: 日本語で記述
- **コード内コメント**: 日本語で記述

### Conventional Commits の仕様

コミットメッセージおよび PR タイトルは以下の形式に従ってください：

```
<type>: <description>

[optional body]
```

`<type>` は以下のいずれかを使用：

- `feat`: 新機能追加
- `fix`: バグ修正
- `docs`: ドキュメント変更
- `style`: コードフォーマット変更
- `refactor`: リファクタリング
- `test`: テスト追加・修正
- `chore`: その他の変更

`<description>` は日本語で簡潔に記述してください。  
`[optional body]` は変更の詳細な説明を日本語で記述します。

### フォーマット要件

- すべての Heading とその本文の間には、空白行を入れる
- 英数字と日本語の間には、半角スペースを入れる

## Working Effectively

### Setup and Dependencies
- Install Python dependencies: `pip install -r requirements.txt` -- takes ~5 seconds, NEVER CANCEL, set timeout to 60+ seconds for safety
- NEVER CANCEL: Most operations are fast (<10 seconds), but Windows tests take ~25 seconds due to sleep timers
- Dependencies: `requests==2.32.4` and `psutil==7.0.0`
- Python 3.12+ required for optimal compatibility

### Build and Test Process
- Run all tests: `python3 -m unittest discover -s src -p "test_*.py"` -- takes ~25 seconds, NEVER CANCEL, set timeout to 60+ seconds
- Run Linux-specific tests: `python3 -m unittest discover -s src/linux -p "test_*.py"` -- takes ~0.2 seconds, NEVER CANCEL, set timeout to 30+ seconds
- Run Windows-specific tests: `python3 -m unittest discover -s src/windows -p "test_*.py"` -- takes ~25 seconds, NEVER CANCEL, set timeout to 60+ seconds
- Run atomic update tests: `python3 -m unittest src.test_github_issue_atomic` -- takes ~0.2 seconds, NEVER CANCEL, set timeout to 30+ seconds  
- Run common utility tests: `python3 -m unittest src.test_common` -- takes ~0.2 seconds, NEVER CANCEL, set timeout to 30+ seconds
- Windows tests include sleep timers and take significantly longer than Linux tests

### Running the Application
- REQUIRED SETUP: Create `data/github_token.txt` with valid GitHub personal access token
- Run with: `python3 -m src ISSUE_NUMBER` where ISSUE_NUMBER is a valid GitHub issue number
- Application requires root privileges for apt operations on Linux
- Application connects to GitHub API to fetch and update issue status

### Application Architecture
- **Main entry**: `src/__main__.py` - parses issue number, initializes GitHubIssue, runs platform-specific updates
- **Core logic**: `src/__init__.py` - GitHubIssue class with atomic update functionality  
- **Linux support**: `src/linux/update_apt_softwares.py` - apt package management
- **Windows support**: `src/windows/update_scoop_softwares.py` - scoop package management
- **Tests**: Comprehensive unit tests with mocking for external dependencies

## Validation

### Manual Testing Steps
- Always run the complete test suite before making changes
- **Complete End-to-End Validation Workflow:**
  ```bash
  # 1. Install dependencies
  pip install -r requirements.txt
  
  # 2. Test core imports and functionality
  python3 -c "import src; print('Import successful')"
  python3 -c "
  from src import get_real_hostname, is_valid_issue_number, is_root
  print(f'Hostname: {get_real_hostname()}')
  print(f'Valid issue: {is_valid_issue_number(\"123\")}')
  print(f'Is root: {is_root()}')
  "
  
  # 3. Run all test suites
  python3 -m unittest src.test_github_issue_atomic  # ~0.2s
  python3 -m unittest src.test_common               # ~0.2s  
  python3 -m unittest discover -s src/linux -p "test_*.py"  # ~0.2s
  # Note: Windows tests take ~25s due to sleep timers - NEVER CANCEL
  
  # 4. Test application setup
  mkdir -p data && echo "test_token" > data/github_token.txt
  python3 -m src 123  # Should fail at GitHub API call, not before
  ```
- **Expected Results:** All imports work, all tests pass, application starts and attempts GitHub API call

### CI/CD Integration
- Linux CI: `.github/workflows/linux-ci.yml` installs apt packages and runs all tests
- Windows CI: `.github/workflows/windows-ci.yml` tests Python 3.8-3.13 compatibility
- CI installs system packages from `.devcontainer/apt-packages.txt` on Linux
- NEVER CANCEL: CI builds complete in under 2 minutes, but set timeouts to 5+ minutes

### Code Quality
- No formal linting tools configured - follow existing code style
- Use unittest for all testing - comprehensive mocking patterns established
- Follow Python naming conventions and existing patterns
- All external dependencies (requests, apt, psutil) should be mocked in tests

## Common Tasks

### Development Environment
```bash
# Repository root contents
.devcontainer/         # Docker development environment
.github/workflows/     # CI pipelines for Linux and Windows
.vscode/              # VSCode configuration
src/                  # Main Python package
├── __init__.py       # Core GitHubIssue class and utilities
├── __main__.py       # Main entry point
├── linux/           # Linux (apt) specific code
├── windows/         # Windows (scoop) specific code
├── test_*.py        # Unit tests
requirements.txt      # Python dependencies
update-softwares.sh   # Linux deployment script
update-softwares.ps1  # Windows deployment script
```

### Key Functions and Classes
- `GitHubIssue` class: Manages GitHub issue updates with atomic retry logic
- `is_valid_issue_number()`: Validates issue number format
- `get_real_hostname()`: Cross-platform hostname detection
- `get_github_token()`: Reads token from data/github_token.txt
- `is_root()`: Unix root privilege detection

### Deployment Scripts
- Linux: `update-softwares.sh` - requires root, installs git/python3, clones repo, runs application
- Windows: `update-softwares.ps1` - installs to user profile, requires ISSUE_NUMBER environment variable
- Both scripts clone from GitHub and run the application with provided issue number

### GitHub Integration
- Application parses issue body for software update status table
- Updates table rows with checkmarks (⏳ running, ✅ success, 🔴 failed)
- Uses atomic updates with retry logic to prevent race conditions
- Posts comments with update details and package counts
- Requires issues to have specific comment format: `<!-- update-softwares#hostname#package_manager -->`

### Platform-Specific Notes
- **Linux**: Uses python3-apt library for package management, requires root privileges
- **Windows**: Uses scoop command-line tool, manages PowerShell execution
- **Cross-platform**: Hostname detection, issue number validation, GitHub API integration

### Error Handling
- Missing GitHub token: "Please create data/github_token.txt"
- Invalid issue number: Logs error and exits cleanly
- Network failures: GitHub API calls have retry logic with exponential backoff
- Concurrent updates: Atomic update mechanism prevents conflicts between multiple instances