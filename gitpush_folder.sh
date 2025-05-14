#!/bin/bash

FOLDER=$1
MESSAGE=$2

if [ -z "$FOLDER" ] || [ -z "$MESSAGE" ]; then
  echo "Usage: ./gitpush_folder.sh <folder_path> \"commit message\""
  exit 1
fi

if [ ! -d "$FOLDER" ]; then
  echo "Error: Folder '$FOLDER' does not exist."
  exit 1
fi

# Check for large files (>50MB)
echo "Checking for large files..."
LARGE_FILES=$(find "$FOLDER" -type f -size +50M | wc -l)
if [ "$LARGE_FILES" -gt 0 ]; then
  echo "Warning: Found $LARGE_FILES files larger than 50MB in $FOLDER"
  echo "GitHub has a file size limit of 100MB and recommends files under 50MB"
  find "$FOLDER" -type f -size +50M
  read -p "Do you want to continue anyway? (y/n) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborting push. Consider using Git LFS for large files."
    exit 1
  fi
fi

CURRENT_BRANCH=$(git branch --show-current)

git add "$FOLDER"
git commit -m "$MESSAGE"

# Push with settings for handling larger repos
echo "Pushing changes to origin/$CURRENT_BRANCH..."
git -c http.postBuffer=524288000 push origin "$CURRENT_BRANCH"
