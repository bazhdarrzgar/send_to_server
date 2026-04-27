#!/bin/bash

# Configuration
BRANCH="main"

# Get the commit message from arguments, or use a default one
COMMIT_MSG=${1:-"Update: $(date)"}

echo "Adding changes to Git..."
git add .

echo "Committing changes with message: '$COMMIT_MSG'..."
git commit -m "$COMMIT_MSG"

echo "Pushing to GitHub on branch $BRANCH..."
git push origin "$BRANCH"

echo "Done!"


