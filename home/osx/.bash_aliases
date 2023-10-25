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
  git checkout $(gb)
}

function gb() {
  git branch | fzf-tmux -d 15 | sed -e 's/^[[:space:]]*//'
}

# Just alias gnu variants over BSD default utilities
alias shuf="gshuf"
alias readlink="greadlink"
alias sed="gsed"
alias tr="gtr"
alias sort="LC_ALL=C gsort" # Makes GNU sort much faster
# alias bmon="bmon -p en0 -o 'curses:bgchar= '"

alias gpurge="git fetch origin --prune && git branch --merged | grep -v master | xargs git branch -d"

# Some nice helpers & shortcuts
alias j="cat ${1} | jq ."

if [ -f ~/.aws/credentials ]; then
  # This sed methods yields ~20x faster load times than using `aws configure`
  export AWS_ACCESS_KEY_ID="$(sed '2q;d' ~/.aws/credentials | cut -d '=' -f 2)"
  export AWS_SECRET_ACCESS_KEY="$(sed '3q;d' ~/.aws/credentials | cut -d '=' -f 2)"
  export AWS_SESSION_TOKEN="$(sed '4q;d' ~/.aws/credentials | cut -d '=' -f 2)"
  export AWS_DEFAULT_REGION="ap-southeast-2"
fi

