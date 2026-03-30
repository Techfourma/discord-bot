# Contributing Guide & Pull Request Instructions

> **Complete guide for setting up, developing, and submitting pull requests for Techfour Discord Bot**

---

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Creating a Pull Request](#creating-a-pull-request)
- [PR Structure & Checklist](#pr-structure--checklist)
- [Merging & Deployment](#merging--deployment)
- [Code Standards](#code-standards)
- [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

### For Contributors:

```bash
# 1. Clone the repository
git clone https://github.com/Techfourma/discord-bot.git
cd discord-bot

# 2. Create a feature branch
git checkout -b feature/your-feature-name

# 3. Make your changes
# ... edit files ...

# 4. Commit changes
git add .
git commit -m "feat: description of changes"

# 5. Push to your branch
git push origin feature/your-feature-name

# 6. Create Pull Request (see next section)
```

---

## 🛠️ Development Setup

### Prerequisites:
- Python 3.10+
- Git
- Virtual environment manager (recommended)

### Step 1: Clone & Setup Environment

```bash
git clone https://github.com/Techfourma/discord-bot.git
cd discord-bot
```

### Step 2: Create Virtual Environment

```bash
# Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Setup Environment Variables

```bash
# Create .env file from template (if available)
cp .env.example .env

# Or create manually and add:
DISCORD_TOKEN=your_token_here
GEMINI_API_KEY=your_key_here
# ... other env vars
```

### Step 5: Test Locally

```bash
# Run the bot
python main.py

# You should see: ✅ Gemini API configured, ✅ Bot ready
```

---

## ✏️ Making Changes

### Branch Naming Convention

```
feature/   → New features           (e.g., feature/add-music-commands)
bugfix/    → Bug fixes              (e.g., bugfix/fix-cache-issue)
docs/      → Documentation updates  (e.g., docs/update-readme)
refactor/  → Code refactoring       (e.g., refactor/improve-error-handling)
chore/     → Tasks/maintenance      (e.g., chore/update-dependencies)
```

### Commit Message Format

```
type: brief description of change

Optional longer explanation of why and what was changed.
Can span multiple lines.

Related issues: #123, #456
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `refactor:` - Code refactoring
- `perf:` - Performance improvement
- `test:` - Testing
- `chore:` - Maintenance

**Examples:**
```bash
git commit -m "feat: add caching for AI responses"
git commit -m "fix: resolve import error in services"
git commit -m "docs: update installation guide"
git commit -m "refactor: improve error handling in ai_bot_service"
```

### Code Style Guidelines

#### Python (PEP 8):
```python
# ✅ DO
def get_ai_response(prompt: str, user_id: str) -> str:
    """Get AI response with proper error handling."""
    if not prompt:
        raise ValueError("Prompt cannot be empty")
    return ai_service.get_response(prompt)

# ❌ DON'T
def get_ai_response(prompt,user_id):
    if not prompt:
        raise Exception("error")
    return ai_service.get_response(prompt)
```

#### JavaScript/Google Apps Script:
```javascript
// ✅ DO
function getStudentsData() {
  try {
    var sheet = getSheet("DaftarUangKas");
    if (!sheet) {
      return errorOut("Sheet not found");
    }
    // ... rest of function
  } catch (error) {
    Logger.log("Error: " + error.toString());
    return errorOut("Failed to get students data");
  }
}

// ❌ DON'T
function getStudentsData(){
var sheet=getSheet("DaftarUangKas")
return sheet.getDataRange().getValues()
}
```

### File Organization

Files should be placed in appropriate folders:

```
services/          → All service logic (.py and .js files)
config/            → Configuration references
main.py            → Bot entry point
README.md          → Main documentation
requirements.txt   → Python dependencies
```

---

## 📤 Creating a Pull Request

### Step 1: Push Your Changes

```bash
# Push to your feature branch
git push origin feature/your-feature-name

# Or if pushing for the first time
git push -u origin feature/your-feature-name
```

### Step 2: Open GitHub

Navigate to:
```
https://github.com/Techfourma/discord-bot
```

You should see a notification to create a PR. Click "Compare & pull request"

---

## 📋 PR Structure & Checklist

### PR Title Format:

```
[type]: brief description

Examples:
- feat: reorganize project structure for clean code
- fix: resolve Railway deployment issue
- docs: update comprehensive documentation
- refactor: improve error handling
```

### PR Body Template:

```markdown
## 📝 Description

Brief explanation of what this PR does and why.

## ✨ Changes

- Change 1
- Change 2
- Change 3

## 🧪 Testing

Describe how you tested these changes, and any test cases.

## 📸 Related Issues

Fixes #123
Relates to #456

## ✅ Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added/updated
- [ ] All tests passing

## 🚀 Deployment Notes

Any notes about deployment or breaking changes? None/Specific notes here.
```

### Complete Example PR:

```markdown
## 📝 Description

This PR reorganizes the project structure for better maintainability and adds comprehensive documentation. Refactoring puts services in dedicated folders and updates all imports accordingly.

## ✨ Changes

- Reorganized code into `services/` and `config/` folders
- Updated all imports from root-level to package-level imports
- Added comprehensive README with setup, deployment, and usage guides
- Restored `requirements.txt` and `runtime.txt` to root for Railway compatibility
- Added PR templates for future contributions

## 🧪 Testing

- [x] Code runs without errors locally
- [x] All imports resolve correctly
- [x] Services initialized properly
- [x] Deployment files in correct locations

## 📸 Related Issues

- Improves code organization (clean code principles)
- Better documentation for maintainability

## ✅ Checklist

- [x] Code follows project style guidelines
- [x] Self-review completed
- [x] Comments added for complex logic
- [x] Documentation updated
- [x] No new warnings generated
- [x] All tests passing
- [x] No breaking changes

## 🚀 Deployment Notes

100% backward compatible. No additional configuration needed. Ready for production deployment.
```

---

## 🏷️ PR Labels

When creating a PR, add appropriate labels:

- **enhancement** - New feature or improvement
- **bug** - Bug fix
- **documentation** - Documentation update
- **refactoring** - Code reorganization
- **urgent** - High priority
- **wontfix** - Decided not to implement

---

## 👥 Requesting Review

1. **Add Reviewers:** Click "Reviewers" section, add team members
2. **Add Assignees:** Click "Assignees" to assign yourself or others
3. **Add Labels:** Add relevant labels as listed above
4. **Leave Comments:** Be descriptive about changes

---

## 🔄 Responding to Review Comments

When reviewers request changes:

1. **Read the comment carefully**
2. **Make the necessary changes** to your code
3. **Commit with descriptive message:**
   ```bash
   git commit -m "review: address feedback on error handling"
   ```
4. **Push changes:**
   ```bash
   git push origin feature/your-feature-name
   ```
5. **Reply to comment** explaining the fix

> Note: The PR automatically updates with your new commits

---

## ✅ Merging & Deployment

### PR Approval Process:

1. ✅ PR passes all automated checks
2. ✅ All reviewers approve
3. ✅ No conflicts with base branch
4. ✅ Lead maintainer approves

### Merging PR:

1. Click "Merge pull request" button on GitHub
2. Choose merge strategy:
   - **Squash and merge** - Cleaner history (recommended)
   - **Create a merge commit** - Preserves all history
   - **Rebase and merge** - Linear history

3. **After merge:**
   - PR is closed automatically
   - Changes deploy to production (via Railway/CI)
   - Local branch can be deleted

### After Merge (Local Cleanup):

```bash
# Update local main branch
git checkout main
git pull origin main

# Delete local feature branch
git branch -d feature/your-feature-name

# Delete remote feature branch
git push origin --delete feature/your-feature-name
```

---

## 📝 Code Standards

### Python Best Practices:

```python
# ✅ Always add docstrings
def get_response(prompt: str) -> str:
    """
    Get AI response for the given prompt.
    
    Args:
        prompt: User's question or statement
        
    Returns:
        AI generated response
        
    Raises:
        ValueError: If prompt is empty
    """
    pass

# ✅ Use type hints
from typing import Optional, List

def process_data(data: List[str], cache: Optional[dict] = None) -> dict:
    pass

# ✅ Proper error handling
try:
    result = some_operation()
except ValueError as e:
    logger.error(f"Value error occurred: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise

# ✅ Use logging instead of print
import logging
logger = logging.getLogger(__name__)
logger.info("Bot started successfully")
logger.error("Failed to connect to API")
```

### General Standards:

- **Line length:** Maximum 88 characters
- **Spacing:** 2 blank lines between functions, 1 between methods
- **Naming:** `snake_case` for functions/variables, `CamelCase` for classes
- **Comments:** Start with `#`, capitalize first word
- **Docstrings:** Triple quotes for module/function documentation

---

## 🐛 Troubleshooting

### Common Issues:

#### Issue: "Conflict with base branch"
```bash
# Update your branch with latest main
git fetch origin
git rebase origin/main

# Or merge approach
git merge origin/main
```

#### Issue: "Your fork is out of sync"
```bash
# Add upstream remote (if not exists)
git remote add upstream https://github.com/Techfourma/discord-bot.git

# Fetch from upstream
git fetch upstream

# Rebase your branch
git rebase upstream/main
```

#### Issue: "Failed to push - permission denied"
```bash
# Check SSH key or use HTTPS
git remote -v

# If using HTTPS, ensure credentials are configured
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

#### Issue: "ModuleNotFoundError"
```bash
# Ensure requirements are installed
pip install -r requirements.txt --force-reinstall

# Or in virtual environment
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

---

## 📚 Resources

- **Git Documentation:** https://git-scm.com/doc
- **GitHub Flow:** https://guides.github.com/introduction/flow/
- **Python Style Guide (PEP 8):** https://pep8.org/
- **Commit Message Guide:** https://www.conventionalcommits.org/

---

## 🤝 Getting Help

- **GitHub Issues:** Report bugs and request features
- **GitHub Discussions:** Ask questions and discuss ideas
- **Email:** techfour@example.com
- **Discord:** Join our community server

---

## 📋 Summary Checklist

Before submitting your PR:

- [ ] Code is tested locally
- [ ] Commits have descriptive messages
- [ ] Branch is up to date with main
- [ ] No merge conflicts
- [ ] PR title is clear and follows format
- [ ] PR description explains changes
- [ ] Appropriate labels are added
- [ ] Code follows project standards
- [ ] Documentation is updated
- [ ] No breaking changes (or documented)

---

## 🎉 Thank You!

Thank you for contributing to Techfour Discord Bot! Your efforts help make this project better for everyone.

**Happy coding! 🚀**

---

*Last Updated: March 30, 2026*
*Version: 1.0*
