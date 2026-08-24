# GitHub Actions Workflows

This directory contains automated CI/CD workflows for the AI CFO Platform.

## 🚀 Workflows Overview

### 1. **CI - Tests and Lint** (`ci.yml`)
**Trigger**: Pull requests and pushes to `main` and `develop`

**What it does**:
- ✅ Runs backend Python tests with PostgreSQL and Redis
- ✅ Runs backend linting (Ruff, Black, isort)
- ✅ Runs frontend build and type checking
- ✅ Security scanning with Trivy
- ✅ PR validation (conventional commits, merge conflicts, file sizes)
- ✅ Uploads coverage to Codecov

**Services**: PostgreSQL 15, Redis 7

---

### 2. **Auto Merge** (`auto-merge.yml`)
**Trigger**: PR opened/updated, PR review submitted, checks completed

**What it does**:
- ✅ Automatically enables auto-merge when conditions are met
- ✅ Checks for approvals and passing checks
- ✅ Respects `do-not-merge` label
- ✅ Skips draft PRs
- ✅ Adds `ready-to-merge` label
- ✅ Posts comment with merge status

**Auto-merge conditions**:
- All CI checks pass
- At least 1 approval OR `auto-merge` label
- Not a draft PR
- No `do-not-merge` label

---

### 3. **PR Labeler** (`pr-labeler.yml`)
**Trigger**: PR opened/updated

**What it does**:
- ✅ Auto-labels based on files changed
- ✅ Adds size labels (XS, S, M, L, XL)
- ✅ Detects breaking changes
- ✅ Auto-assigns reviewers
- ✅ Identifies area labels (backend, frontend, database, etc.)

**Labels applied**:
- **Area**: backend, frontend, api, database, ui, pages, services
- **Type**: enhancement, bug, documentation, refactoring, tests
- **Size**: size: XS/S/M/L/XL
- **Special**: breaking-change, ready-to-merge

---

### 4. **Deploy** (`deploy.yml`)
**Trigger**: Push to `main` with `[deploy]` in commit message, or manual

**What it does**:
- ✅ Deploys backend to Render
- ✅ Deploys frontend to Vercel
- ✅ Posts deployment status comment

**Required Secrets**:
- `RENDER_DEPLOY_HOOK_URL` - Render deploy hook
- `VERCEL_DEPLOY_HOOK_URL` - Vercel deploy hook

---

### 5. **Code Quality** (`code-quality.yml`)
**Trigger**: Pull requests and pushes to `main` and `develop`

**What it does**:
- ✅ CodeQL security analysis
- ✅ SonarCloud code quality scan
- ✅ Cyclomatic complexity check
- ✅ Maintainability index report
- ✅ Dependency vulnerability scanning
- ✅ Test coverage report with badge

**Tools**: CodeQL, SonarCloud, Radon, Safety, pip-audit

---

## 📋 Required Secrets

Set these in GitHub Settings > Secrets and variables > Actions:

### Optional (for full functionality):
- `CODECOV_TOKEN` - Codecov.io integration
- `SONAR_TOKEN` - SonarCloud integration
- `RENDER_DEPLOY_HOOK_URL` - Render deployment
- `VERCEL_DEPLOY_HOOK_URL` - Vercel deployment

---

## 🏷️ Labels Used

Make sure these labels exist in your repository:

### Auto-created by workflows:
- `backend`, `frontend`, `api`, `database`, `ui`, `pages`
- `services`, `tests`, `documentation`, `configuration`
- `ci-cd`, `dependencies`, `migration`, `styling`
- `enhancement`, `bug`, `refactoring`, `chore`, `performance`
- `size: XS`, `size: S`, `size: M`, `size: L`, `size: XL`
- `ready-to-merge`, `breaking-change`

### Manual labels (for control):
- `auto-merge` - Enable auto-merge without approval
- `do-not-merge` - Prevent auto-merge

---

## 🔧 How to Use

### For Pull Requests

1. **Create PR** with conventional commit format:
   ```
   feat: add new feature
   fix: bug fix
   docs: documentation update
   refactor: code refactoring
   test: add tests
   chore: maintenance
   ```

2. **Labels** are automatically added based on files changed

3. **CI checks** run automatically:
   - Backend tests
   - Frontend build
   - Linting
   - Security scan

4. **Get approval** from at least 1 reviewer

5. **Auto-merge** triggers when:
   - All checks pass ✅
   - Has 1+ approval ✅
   - Not a draft
   - No `do-not-merge` label

6. **PR is automatically merged** with squash merge

### For Deployments

**Option 1: Automatic (on push to main)**
```bash
git commit -m "feat: new feature [deploy]"
git push origin main
```

**Option 2: Manual**
- Go to Actions tab
- Select "Deploy to Production"
- Click "Run workflow"

### For Testing Locally

**Backend tests:**
```bash
cd backend
pytest tests/ -v --cov=.
```

**Frontend build:**
```bash
cd frontend
npm run build
```

**Linting:**
```bash
# Backend
cd backend
ruff check .
black --check .

# Frontend
cd frontend
npm run lint
```

---

## 📊 Status Badges

Add these to your README.md:

```markdown
![CI](https://github.com/sanchitmoh/CFO/workflows/CI%20-%20Tests%20and%20Lint/badge.svg)
![Code Quality](https://github.com/sanchitmoh/CFO/workflows/Code%20Quality/badge.svg)
[![codecov](https://codecov.io/gh/sanchitmoh/CFO/branch/main/graph/badge.svg)](https://codecov.io/gh/sanchitmoh/CFO)
```

---

## 🛠️ Customization

### Adjust auto-merge rules

Edit `.github/workflows/auto-merge.yml`:

```yaml
# Require 2 approvals instead of 1
const canMerge = approvals >= 2;

# Change merge method (squash, merge, rebase)
merge_method: 'merge'
```

### Change CI triggers

Edit `.github/workflows/ci.yml`:

```yaml
on:
  pull_request:
    branches: [main, develop, staging]  # Add more branches
```

### Add more labels

Edit `.github/workflows/pr-labeler.yml`:

```javascript
if (path.includes('your-pattern')) {
  labels.add('your-label');
}
```

---

## 🐛 Troubleshooting

### CI failing on test database

**Issue**: PostgreSQL connection errors  
**Fix**: Ensure service container health checks pass

### Auto-merge not working

**Issue**: PR not merging automatically  
**Checklist**:
- [ ] All checks passed?
- [ ] Has approval or `auto-merge` label?
- [ ] Not a draft?
- [ ] No `do-not-merge` label?

### Labels not applying

**Issue**: PR labels not added  
**Fix**: Check if labels exist in repository settings

### Deployment not triggering

**Issue**: Deploy workflow not running  
**Fix**: 
- Check commit message contains `[deploy]`
- Or manually trigger from Actions tab
- Verify secrets are configured

---

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Codecov](https://codecov.io/)
- [SonarCloud](https://sonarcloud.io/)

---

## 🎯 Best Practices

1. ✅ Always use conventional commit format
2. ✅ Keep PRs small and focused (< 500 lines)
3. ✅ Write tests for new features
4. ✅ Update documentation with code changes
5. ✅ Wait for CI to pass before requesting review
6. ✅ Address reviewer feedback promptly
7. ✅ Use draft PRs for work in progress
8. ✅ Add `do-not-merge` label if PR needs manual review

---

**Last Updated**: 2026-08-24
