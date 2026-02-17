#!/bin/bash
# ==============================================================================
# AI Context Generator Script
#
# Description:
# This script creates a single text file (`ai_context.txt`) containing the
# directory tree and the contents of all relevant source code files in the
# current project directory. This is ideal for providing context to an AI model.
#
# Instructions:
# 1. Place this script in the root directory of your project.
# 2. Make it executable: chmod +x contextualizer.sh
# 3. Run it without arguments for default behavior:
#       ./contextualizer.sh
# 4. Or pass additional directories to ignore completely:
#       ./contextualizer.sh FILES FINAL node_modules otra_carpeta
# 5. The `ai_context.txt` file will be created in the same directory.
# ==============================================================================

# --- Parse command-line arguments for extra directories to ignore ---
EXTRA_IGNORE_DIRS=()
while [[ $# -gt 0 ]]; do
    EXTRA_IGNORE_DIRS+=("$1")
    shift
done

# --- Configuration ---
OUTPUT_FILE="ai_context.txt"

# Directorios ignorados por defecto
DEFAULT_IGNORE_DIRS=("node_modules" "public" ".next" ".open-next" ".wrangler" ".git" "dist" "build" "vendor" "__pycache__" ".venv" "venv" ".idea" ".vscode")

# Combinamos los predeterminados con los pasados como argumentos
IGNORE_DIRS_FIND=("${DEFAULT_IGNORE_DIRS[@]}" "${EXTRA_IGNORE_DIRS[@]}")

# Para el comando `tree` (formato separado por |)
IGNORE_DIRS_TREE=$(printf "%s|" "${DEFAULT_IGNORE_DIRS[@]}" "${EXTRA_IGNORE_DIRS[@]}")
IGNORE_DIRS_TREE=${IGNORE_DIRS_TREE%|}  # Eliminamos el último |

# Archivos específicos a ignorar
IGNORE_FILES=("package-lock.json")

# --- Script Logic ---
echo "🚀 Starting AI context generation..."

if [ ${#EXTRA_IGNORE_DIRS[@]} -gt 0 ]; then
  echo "📂 Ignorando directorios adicionales: ${EXTRA_IGNORE_DIRS[*]}"
fi

# Limpiamos el archivo de salida si ya existe
> "$OUTPUT_FILE"

# 1. Cabecera
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

# 2. Árbol de directorios
if command -v tree &> /dev/null; then
  echo "🌳 Generating file tree..."
  ignore_patterns_tree="${IGNORE_DIRS_TREE}|${OUTPUT_FILE}"
  for file in "${IGNORE_FILES[@]}"; do
    ignore_patterns_tree+="|$file"
  done
  tree -a -I "$ignore_patterns_tree" >> "$OUTPUT_FILE"
else
  echo "⚠️ 'tree' command not found. Skipping directory tree generation." >> "$OUTPUT_FILE"
  echo " For a better context, please install 'tree' (e.g., 'sudo apt-get install tree' or 'brew install tree')." >> "$OUTPUT_FILE"
fi

# 3. Separador antes del código
{
  echo ""
  echo ""
  echo "-------------------------------------------------"
  echo "PROJECT SOURCE CODE FILES"
  echo "-------------------------------------------------"
  echo ""
} >> "$OUTPUT_FILE"

# 4. Buscar y procesar archivos de texto/fuente (detección automática)
echo "🔍 Finding and processing text/source files..."

# Lógica de pruning (evita entrar en directorios ignorados)
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

# Ignorar archivos específicos
ignore_part=""
if [ ${#IGNORE_FILES[@]} -gt 0 ]; then
  ignore_ands=()
  first=true
  for file in "${IGNORE_FILES[@]}"; do
    if [ "$first" = true ]; then
      ignore_ands+=(-not -name "$file")
      first=false
    else
      ignore_ands+=(-a -not -name "$file")
    fi
  done
  ignore_part="${ignore_ands[*]}"
fi

# Búsqueda principal
find . \
  ${prune_part} \
  -type f \
  ${ignore_part} \
  -not -path "./$OUTPUT_FILE" \
  -print0 |
while IFS= read -r -d '' file; do
  # Detectar solo archivos de texto/script con `file`
  if file --brief "$file" | grep -Eq 'text|script|empty'; then
    echo " -> Processing: $file"

    # Hint de lenguaje a partir de la extensión (o nombre si no tiene)
    extension="${file##*.}"
    if [[ -z "$extension" ]] || [[ "$extension" == "$file" ]]; then
      extension="${file##*/}"
    fi
    lang_hint="${extension,,}"

    # Refinamientos comunes
    case "$lang_hint" in
      js|jsx) lang_hint="javascript" ;;
      ts|tsx) lang_hint="typescript" ;;
      py) lang_hint="python" ;;
      sh|bash) lang_hint="bash" ;;
      ps1) lang_hint="powershell" ;;
      md) lang_hint="markdown" ;;
      yml|yaml) lang_hint="yaml" ;;
      json) lang_hint="json" ;;
      gitignore) lang_hint="gitignore" ;;
      license) lang_hint="text" ;;
      dockerfile) lang_hint="dockerfile" ;;
      *) lang_hint="text" ;;
    esac

    # Añadir al archivo de salida
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
  else
    echo " -> Skipping non-text file: $file"
  fi
done

echo "✅ Success! Context saved to '$OUTPUT_FILE'."
echo "➡️ You can now copy the contents of this file into the AI prompt."