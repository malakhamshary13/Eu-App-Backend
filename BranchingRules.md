# Git Workflow (Quick Guide)

## Branches
- `main` → stable only (no direct commits)
- `dev` → integration branch (no direct commits)

---

## Create a Branch
Before starting any task:
git checkout dev
git pull origin dev
git checkout -b feature/EU-XX-description

---

## Naming Rules

### Branch
feature/EU-12-meal-scheduling
fix/EU-18-login-bug

### Commit

feat(EU-12): add meal calendar
fix(EU-18): fix login issue

### Pull Request Title
feat(EU-12): meal scheduling feature


## Workflow

1. Create branch from `dev`
2. Work and commit regularly
3. Push branch
4. Open pull request into `dev`
5. Request review
6. Merge after approval

---

## Rules

- Do not commit directly to `main` or `dev`
- Always create a feature branch for each task
- Always include the Jira ID in branch names and commits
- Always pull the latest `dev` before starting work
- Use pull requests for all merges
