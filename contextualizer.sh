#!/bin/bash
# ==============================================================================
# AI Context Generator Script
# ==============================================================================
# --- Configuration ---
OUTPUT_FILE="ai_context.txt"

# Directories to ignore completely in both the tree and file content.
IGNORE_DIRS_TREE="node_modules|public|.next|.open-next|.wrangler|.git|dist|build|vendor|__pycache__|.venv|venv|.git|.idea|.vscode"
IGNORE_DIRS_FIND=("node_modules" "public" ".next" ".open-next" ".wrangler" ".git" "dist" "build" "vendor" "__pycache__" ".venv" "venv" ".idea" ".vscode")

# Specific files to ignore.
IGNORE_FILES=("package-lock.json")

# File extensions to include.
INCLUDE_EXTENSIONS=(
  "js" "jsx" "ts" "tsx" "html" "css" "scss" "sass" "less"
  "php" "go" "java" "c" "cpp" "h" "hpp" "cs"
  "json" "yml" "yaml" "xml" "md" "sql" "puml" "py" "rb"
  "Dockerfile" "docker-compose.yml" "package.json" "tsconfig.json" ".env.example"
)

# --- Script Logic ---
echo "🚀 Starting AI context generation..."

# Clear the output file.
> "$OUTPUT_FILE"

# 1. Add a header.
{
  echo "================================================="
  echo "PROJECT CONTEXT FOR AI ANALYSIS"
  echo "================================================="
  echo "This document contains the project structure and source code for review."
  echo "Project root: $(pwd)"
  echo "Generated on: $(date)"
  echo ""
  echo "-------------------------------------------------"
  echo "PROJECT FILE AND FOLDER STRUCTURE"
  echo "-------------------------------------------------"
  echo ""
} >> "$OUTPUT_FILE"

# 2. Generate tree.
if command -v tree &> /dev/null
then
  echo "🌳 Generating file tree..."
  ignore_patterns_tree="${IGNORE_DIRS_TREE}|${OUTPUT_FILE}"
  for file in "${IGNORE_FILES[@]}"; do
    ignore_patterns_tree+="|$file"
  done
  tree -a -I "$ignore_patterns_tree" >> "$OUTPUT_FILE"
else
  echo "⚠️ 'tree' command not found." >> "$OUTPUT_FILE"
fi

# 3. Separator.
{
  echo ""
  echo ""
  echo "-------------------------------------------------"
  echo "PROJECT SOURCE CODE FILES"
  echo "-------------------------------------------------"
  echo ""
} >> "$OUTPUT_FILE"

# 4. Find and process files.
echo "🔍 Finding and processing source files..."

# Build prune conditions
prune_ors=()
for dir in "${IGNORE_DIRS_FIND[@]}"; do
  prune_ors+=(-o -name "$dir")
done

if [ ${#prune_ors[@]} -gt 0 ]; then
  prune_inner="( -false ${prune_ors[@]} )"
  prune_part="( -type d $prune_inner -prune ) -o"
else
  prune_part=""
fi

# Build include conditions
include_ors=()
for ext in "${INCLUDE_EXTENSIONS[@]}"; do
  if [[ "$ext" == *.* ]] || [[ "$ext" == "Dockerfile" ]]; then
    name="$ext"
  else
    name="*.$ext"
  fi
  include_ors+=(-o -name "$name")
done

if [ ${#include_ors[@]} -eq 0 ]; then
  echo "❌ No file patterns to include."
  exit 1
fi

include_inner="( -false ${include_ors[@]} )"

# Build ignore conditions
ignore_ands=()
for file in "${IGNORE_FILES[@]}"; do
  ignore_ands+=(-a -not -name "$file")
done
ignore_part="${ignore_ands[*]}"

# --- CRITICAL FIX: Disable Globbing ---
# We disable shell globbing so wildcards like *.py are passed to 'find' literally,
# instead of being expanded by the shell into a list of filenames.
set -f

# Execute find
find . \
  ${prune_part} \
  -type f \
  \( $include_inner \) \
  ${ignore_part} \
  -not -path "./$OUTPUT_FILE" \
  -print0 |
while IFS= read -r -d '' file; do
  extension="${file##*.}"
  if [[ -z "$extension" ]] || [[ "$extension" == "$file" ]]; then
      extension="${file##*/}"
  fi
  lang_hint="${extension,,}"
  
  case "$lang_hint" in
    js|jsx) lang_hint="javascript" ;;
    ts|tsx) lang_hint="typescript" ;;
    puml|plantuml) lang_hint="plantuml" ;;
    py) lang_hint="python" ;;
    rb) lang_hint="ruby" ;;
    md) lang_hint="markdown" ;;
    yml|yaml) lang_hint="yaml" ;;
    sh) lang_hint="bash" ;;
    dockerfile) lang_hint="dockerfile" ;;
  esac
  
  echo " -> Processing: $file"
  {
    echo "========================================="
    echo "FILE: ${file#./}"
    echo "========================================="
    echo "\`\`\`${lang_hint}"
    cat "$file"
    echo ""
    echo "\`\`\`"
    echo ""
    echo ""
  } >> "$OUTPUT_FILE"
done

# Re-enable globbing (good practice, though script ends here)
set +f

echo "✅ Success! Context saved to '$OUTPUT_FILE'."
