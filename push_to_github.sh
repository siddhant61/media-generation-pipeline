#!/bin/bash

# GitHub Setup Script for Media Generation Pipeline
# Usage: ./push_to_github.sh [repository-name]

echo "🚀 GitHub Setup for Media Generation Pipeline"
echo "=============================================="

# Default repository name
REPO_NAME="${1:-media-generation-pipeline}"
GITHUB_USERNAME="siddhant61"

echo "📍 Repository will be created as: ${GITHUB_USERNAME}/${REPO_NAME}"
echo ""

# Check if git is configured
if ! git config user.name >/dev/null || ! git config user.email >/dev/null; then
    echo "❌ Git is not configured. Please run:"
    echo "   git config user.name 'Siddhant Gadamsetti'"
    echo "   git config user.email 'siddhant.gadamsetti@gmail.com'"
    exit 1
fi

echo "✅ Git is configured for: $(git config user.name) <$(git config user.email)>"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Not in a git repository. Please run 'git init' first."
    exit 1
fi

echo "✅ Git repository detected"

# Check if there are any commits
if ! git log --oneline -1 > /dev/null 2>&1; then
    echo "❌ No commits found. Please make an initial commit first."
    exit 1
fi

echo "✅ Repository has commits"

# Check if remote already exists
if git remote get-url origin > /dev/null 2>&1; then
    echo "⚠️  Remote 'origin' already exists: $(git remote get-url origin)"
    echo "Do you want to continue? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
else
    echo "📡 Adding remote repository..."
    git remote add origin "https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"
    echo "✅ Remote added: https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"
fi

echo ""
echo "🔑 Authentication Setup"
echo "======================"
echo "Before pushing, make sure you have authentication set up:"
echo "  1. GitHub Personal Access Token (recommended)"
echo "  2. SSH keys"
echo "  3. GitHub CLI (gh auth login)"
echo ""
echo "Continue with push? (y/N)"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "🚀 Pushing to GitHub..."
    
    # Push to GitHub
    if git push -u origin main; then
        echo ""
        echo "🎉 SUCCESS! Your repository has been pushed to GitHub!"
        echo ""
        echo "📊 Repository Details:"
        echo "   URL: https://github.com/${GITHUB_USERNAME}/${REPO_NAME}"
        echo "   Branch: main"
        echo "   Files pushed: $(git ls-tree -r HEAD --name-only | wc -l) files"
        echo ""
        echo "🔗 Next steps:"
        echo "   1. Visit your repository: https://github.com/${GITHUB_USERNAME}/${REPO_NAME}"
        echo "   2. Add a description and topics"
        echo "   3. Star your repository"
        echo "   4. Share with the community!"
        echo ""
        echo "📝 Don't forget to:"
        echo "   - Add API keys to environment variables"
        echo "   - Test the setup with: python setup.py"
        echo "   - Run examples with: python example_usage.py"
        
    else
        echo "❌ Push failed. Please check:"
        echo "   1. Repository exists on GitHub"
        echo "   2. Authentication is working"
        echo "   3. Internet connection"
        echo "   4. Repository permissions"
        echo ""
        echo "💡 Manual push command:"
        echo "   git push -u origin main"
    fi
else
    echo "Push cancelled. You can manually push later with:"
    echo "   git push -u origin main"
fi

echo ""
echo "📚 For detailed setup instructions, see: github_setup.md" 