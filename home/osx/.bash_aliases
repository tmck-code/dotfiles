#!/bin/bash

export CLICOLOR="exfxcxdxbxegedabagacad" # enable colours in OSX bash

alias grep="grep --color=auto" # Enable grep colours
alias g="git"
# alias vim="nvim"
alias v="vim"
alias ls="gls --color"
alias find="gfind"
alias brew="arch -arm64 brew"

function cb() {
  # change branch interactively
  git checkout $(gb)
}

function gb() {
  # list branches interactively
  git branch | fzf-tmux -d 15 | sed -e 's/^[[:space:]]*//'
}

# Just alias gnu variants over BSD default utilities
alias shuf="gshuf"
alias readlink="greadlink"
alias sed="gsed"
alias tr="gtr"
alias sort="LC_ALL=C gsort" # Makes GNU sort much faster
# alias bmon="bmon -p en0 -o 'curses:bgchar= '"

alias gpurge="git fetch origin --prune && git branch --merged | grep -v master | grep -v main | xargs git branch -d"

# Some nice helpers & shortcuts
alias j="cat ${1} | jq ."
# add ANSI colour reset codes to the end of each line in a file (to STDOUT)
function cat-with-ansi-reset() { cat "$1" | sed 's/$/\[0m/g'; }

# -----------------------------------------------
# AWS commands

function s3ls_integrations() {
  # List all integrations in a client's S3 bucket
  client=$1
  pattern=$2
  aws s3 ls s3://lexer-client-$client/integrations/$pattern --rec 2>&1 | sed -E "s/integrations/s3:\/\/lexer-client-$client\/integrations/g" | sed -E 's/ +/ /g' # | cut -d ' ' -f 4
}

if [ -f ~/.aws/credentials ]; then
  # This sed methods yields ~20x faster load times than using `aws configure`
  export AWS_ACCESS_KEY_ID="$(sed '2q;d' ~/.aws/credentials | cut -d '=' -f 2)"
  export AWS_SECRET_ACCESS_KEY="$(sed '3q;d' ~/.aws/credentials | cut -d '=' -f 2)"
  export AWS_SESSION_TOKEN="$(sed '4q;d' ~/.aws/credentials | cut -d '=' -f 2)"
  export AWS_DEFAULT_REGION="ap-southeast-2"
fi

function s3ls() {
  aws s3api list-objects-v2 --bucket $1 --prefix $2 | jq -r '.Contents[].Key' | parallel -n1 -I{} echo s3://${1}{}
}

# -----------------------------------------------
# JQ colours

_JQ_REGULAR=0
_JQ_BRIGHT=1
_JQ_DIM=2
_JQ_UNDERSCORE=4
_JQ_BLINK=5
_JQ_REVERSE=7
_JQ_HIDDEN=8

_JQ_BLACK=30
_JQ_RED=31
_JQ_GREEN=32
_JQ_YELLOW=33
_JQ_BLUE=34
_JQ_MAGENTA=35
_JQ_CYAN=36
_JQ_WHITE=37

JQ_NULL="$_JQ_REVERSE;$_JQ_RED"
JQ_TRUE="$_JQ_DIM;$_JQ_GREEN"
JQ_FALSE="$_JQ_DIM;$_JQ_RED"
JQ_NUMBERS="$_JQ_UNDERSCORE;$_JQ_CYAN"
JQ_STRINGS="$_JQ_DIM;$_JQ_WHITE"
JQ_ARRAYS="$_JQ_REGULAR;$_JQ_BLUE"
JQ_OBJECTS="$_JQ_BRIGHT;$_JQ_WHITE"
JQ_OBJECT_KEYS="$_JQ_REVERSE;$_JQ_GREEN"

export JQ_COLORS="${JQ_NULL}:${JQ_FALSE}:${JQ_TRUE}:${JQ_NUMBERS}:${JQ_STRINGS}:${JQ_ARRAYS}:${JQ_OBJECTS}:${JQ_OBJECT_KEYS}"

