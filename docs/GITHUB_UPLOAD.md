# GitHub Upload Guide — Fresh Upload

Use these steps from the project folder, for example:

```bat
cd C:\1bottle
```

## 1. Confirm files

```bat
dir
```

You should see:

```text
backend
frontend
docs
README.md
.gitignore
start_backend.bat
start_frontend.bat
```

## 2. Remove old local Git setup

```bat
rmdir /s /q .git
```

If it says `.git` not found, ignore it.

## 3. Remove nested Git from frontend/backend if present

```bat
rmdir /s /q frontend\.git
rmdir /s /q backend\.git
```

Ignore errors if these folders do not exist.

## 4. Initialize and push

```bat
git init
git branch -M main
git add .
git status
git commit -m "Initial commit - Bottle Signature Core v1.6.0"
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git push -u origin main
```

## If remote already exists

```bat
git remote remove origin
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git push -u origin main
```

## Do not commit

The `.gitignore` excludes:

```text
backend/venv/
frontend/node_modules/
backend/bottle_signatures.db
```
