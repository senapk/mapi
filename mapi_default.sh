title=""
required=""
rename=""
readme=./Readme.md
local_script=./local.sh
description=./q.html
cases=./q.tio
output=./mapi.json

# running local scripts
[[ -f "$local_script" ]] && source "$local_script"

# load title
title=`head -1 "$readme" | sed 's/[#^ ]* *//'`

# # building description
md2html Readme.md -o "$description"

# # building tests if not found
sources=`find . -name "*.tio" -o -name "*.vpl"`
[[ ! -f $cases ]] && tk build "$cases" $readme $sources

vpl_scripts=`find . -maxdepth 1 -name "vpl_*"`
problem_files=`find . -maxdepth 1 -name "data*" -o -name "main*" -o -name "lib*"`

mb   "$title" "$description"\
    --tests     "$cases"\
    --upload    $vpl_scripts\
    --keep      $problem_files\
    --required  "$required" "$rename"\
    --output    "$output"
