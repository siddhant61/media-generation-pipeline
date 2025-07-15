# GitHub Repository Setup Guide

Follow these steps to create and push your Media Generation Pipeline to GitHub:

## Step 1: Create GitHub Repository

1. **Go to GitHub**: Navigate to [https://github.com/new](https://github.com/new)

2. **Repository Details**:
   - **Repository name**: `media-generation-pipeline`
   - **Description**: `AI-powered video generation pipeline with OpenAI narration and Stability AI image generation`
   - **Visibility**: Choose Public or Private
   - **Initialize**: Do NOT initialize with README, .gitignore, or license (we already have these)

3. **Click "Create repository"**

## Step 2: Push to GitHub

After creating the repository, GitHub will show you commands. Use these commands in your terminal:

```bash
# Add the remote repository
git remote add origin https://github.com/siddhant61/media-generation-pipeline.git

# Push your code to GitHub
git push -u origin main
```

## Step 3: Verify Your Repository

Once pushed, your repository should contain:
- ✅ Complete project structure
- ✅ Professional README with setup instructions
- ✅ MIT License
- ✅ Proper .gitignore for Python/AI projects
- ✅ All source code files
- ✅ Original Jupyter notebook (preserved)

## Step 4: Repository Settings (Optional)

1. **Add Topics**: Go to your repository → Settings → Topics
   - Add topics like: `python`, `ai`, `machine-learning`, `video-generation`, `openai`, `stability-ai`

2. **Enable GitHub Pages** (if you want to host documentation):
   - Go to Settings → Pages
   - Select source as "Deploy from a branch"
   - Choose `main` branch

3. **Add Repository Description**: 
   - Edit the description at the top of your repository page

## Step 5: Create .env.example File

Create a `.env.example` file in your repository root:

```bash
# Create the example environment file
cat > .env.example << 'EOF'
# Media Generation Pipeline - Environment Variables
# Copy this file to .env and add your actual API keys

# OpenAI API Key
# Get your key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=your-openai-api-key-here

# Stability AI API Key  
# Get your key from: https://platform.stability.ai/account/keys
STABILITY_API_KEY=your-stability-api-key-here

# Optional: Custom output directory
# OUTPUT_DIR=custom_output_directory
EOF

# Add and commit the new file
git add .env.example
git commit -m "Add environment variables example file"
git push
```

## Next Steps

1. **Star your own repository** to make it more discoverable
2. **Share with the community** - post on social media, relevant forums
3. **Add collaborators** if you want others to contribute
4. **Create releases** as you add new features
5. **Consider adding GitHub Actions** for CI/CD

## Repository URL

Your repository will be available at:
**https://github.com/siddhant61/media-generation-pipeline**

## Troubleshooting

If you encounter issues:

1. **Authentication Error**: 
   - Use GitHub Personal Access Token instead of password
   - Or use SSH keys for authentication

2. **Repository Already Exists**:
   - Choose a different name like `ai-video-generation-pipeline`

3. **Large File Warning**:
   - The Jupyter notebook might be large
   - Consider using Git LFS for large files if needed

Congratulations! Your professional AI project is now on GitHub! 🎉 