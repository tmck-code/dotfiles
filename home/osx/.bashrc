#!/bin/bash
# github.com/tmck-code/dotfiles

# TODO: clarify this statement
# [ -z "$PS1" ] && echo "No $PS1" && return 0
# [ -z "${BASH_PROFILE_SOURCED:-}" ] && echo "in .bashrc - profile not sourced" && return 0

# My utils that need to set when using tmux and other tools
[ -d /opt/homebrew/bin ] && PATH="$PATH:/opt/homebrew/bin"
[ -f ~/.bash_aliases ]   && source  ~/.bash_aliases
[ -d ~/bin ] && PATH="$HOME/bin:$PATH"

export PATH

export HISTFILESIZE=          # largest history written to file at one time
export HISTSIZE=              # large history file
export HISTCONTROL=ignoreboth # don't put duplicate lines or lines starting with space in the history.
shopt -s histappend           # append to the history file, don't overwrite it
# Change the file location because certain bash sessions truncate .bash_history file upon close.
# http://superuser.com/questions/575479/bash-history-truncated-to-500-lines-on-each-login
export HISTFILE=~/.bash_eternal_history
# Force prompt to write history after every command.
# http://superuser.com/questions/20900/bash-history-loss
PROMPT_COMMAND="history -a; $PROMPT_COMMAND"

export PROMPT_DIRTRIM=2

# Enable bash completion
# [[ -r /usr/local/etc/bash_completion.d ]] && . /usr/local/etc/bash_completion

# Function to shorten the current directory
short_pwd() {
  local pwd=$(pwd)
  pwd=${pwd/#$HOME/\~}
  sed 's:\([^/]\)[^/]*/:\1/:g' <<< "$pwd"
}

if [[ "$USER" == "root" ]]; then
  export PS1="\[\e[1;31m\]\u\[\e[0m\] \[\e[1;33m\]\w\[\e[0m\] "
else
  export PS1="\[\e[1;33m\]\$(short_pwd)\[\e[0m\] "
fi

# 100% pure Bash (no forking) function to determine the name of the current git branch
gitbranch() {
  local repo="${_GITBRANCH_LAST_REPO:-}"
  local gitdir=""

  # If repo is set, and we are in that repo
  if [[ ! -z "${repo:-}" && "$PWD" == "${repo}/*" ]]; then
    gitdir="$repo/.git"
  else
    local curr="$PWD"
    while [[ ! -z "$curr" ]]; do     # while we are in a dir
      if [[ -e "$curr/.git" ]]; then # check if .git exists
        repo="$curr"                 # if it does, set our vars and break
        gitdir="$curr/.git"
        break
      fi
      curr="${curr%/*}"              # else, go up one dir, i.e. "../"
    done
  fi

  if [[ -z "${gitdir:-}" ]]; then    # if we aren't in a git repo, just return
    unset _GITBRANCH_LAST_REPO
    unset GITBRANCH
    return 0
  fi

  local last_modified="$(gstat -c %Y "$gitdir/HEAD")"
  # if we are in the same repo, check if the repo has been modified since the last check
  if [[ "${_GITBRANCH_LAST_REPO:-}" == "$repo" && "$last_modified" == "${_GITBRANCH_LAST_MODIFIED:-}" ]]; then
    unset _GITBRANCH_MODIFIED
    return 0
  fi

  export _GITBRANCH_LAST_REPO="$repo"
  export _GITBRANCH_LAST_MODIFIED="$last_modified"
  export _GITBRANCH_MODIFIED=1

  # Read and export git branch from the HEAD file
  local head=""
  read head < "$gitdir/HEAD"
  case "$head" in
    ref:*) export GITBRANCH="${head##*/}" ;;
    "")  return 0 ;;
    *)   export GITBRANCH="$branch""d:${head:0:7}" ;;
  esac

  if [ -f "$gitdir/ORIG_HEAD" ]; then
    local commit=""
    read commit < "$gitdir/ORIG_HEAD"
    export GITCOMMIT="${commit:0:9}"
  fi
}

PS1_green='\[\e[1;32m\]'
PS1_purple='\[\e[3;35m\]'
PS1_reset='\[\e[0m\]'
PS1_yellow_bg='\[\e[1;33m\]'
export _PROMPT_PREFIX=(" \D{%T}")

_mk_prompt() {
  history -a # Update the ~/.bash_history every time

  # Change the window title of X terminals
  case $TERM in
    xterm*) echo -ne "\033]0;${USER}@${HOSTNAME%%.*}:${PWD/$HOME/~}\007" ;;
    screen) echo -ne "\033_${USER}@${HOSTNAME%%.*}:${PWD/$HOME/~}\033\\" ;;
  esac

  gitbranch

  sep="∈"
  local prefix=$_PROMPT_PREFIX
  if [[ ! -z "${GITBRANCH:-}" && ! -z "${_GITBRANCH_MODIFIED:-}" ]]; then
    _GITBRANCH_PREFIX=(" ${PS1_yellow_bg}${sep}${PS1_reset} ${PS1_green}${GITBRANCH}${PS1_reset} / ${PS1_purple}${GITCOMMIT}${PS1_reset}")

    # Modified files
    if [ ! -z "$(git ls-files -m)" ]; then
      _GITBRANCH_PREFIX+=("✹")
    fi
    # New, untracked files
    if [ ! -z "$(git ls-files --others --exclude-standard --directory --no-empty-directory --error-unmatch -- ':/*' 2> /dev/null)" ]; then
      _GITBRANCH_PREFIX+=("✭")
    fi
    export _GITBRANCH_PREFIX
  fi
  export PS1="${_PROMPT_PREFIX[@]}${_GITBRANCH_PREFIX[@]:-}\n ☯ $_MK_PROMPT_ORIG_PS1"
}

export _MK_PROMPT_ORIG_PS1="$PS1" # Keep a static copy of PS1
export PROMPT_COMMAND=_mk_prompt  # Create PS1 prompt

export LESS_TERMCAP_mb=$'\e[1;32m'
export LESS_TERMCAP_md=$'\e[1;32m'
export LESS_TERMCAP_me=$'\e[0m'
export LESS_TERMCAP_se=$'\e[0m'
export LESS_TERMCAP_so=$'\e[01;33m'
export LESS_TERMCAP_ue=$'\e[0m'
export LESS_TERMCAP_us=$'\e[1;4;31m'

[ -r ~/bin/uptime_tmux ] && source ~/bin/uptime_tmux
[ -d ~/bin/z ]           && source ~/bin/z/z.sh

# [ -r /usr/local/etc/profile.d/bash_completion.sh ] && \
#   source /usr/local/etc/profile.d/bash_completion.sh

# [ -r /usr/local/etc/bash_completion.d/git-completion.bash ] && \
#   source /usr/local/etc/bash_completion.d/git-completion.bash
# [ -r /opt/homebrew/etc/bash_completion.d/git-completion.bash ] && \
#   source /opt/homebrew/etc/bash_completion.d/git-completion.bash

export PATH="/opt/homebrew/opt/openjdk/bin:$PATH"
export PATH="$PATH:/Users/tomm/.lmstudio/bin"

# Present a pretty message, with a small chance to print a "shiny" version
if [ $[ $RANDOM % 10 ] == 0 ]; then
  fortune | pokesay -WujbC -F | lolcat
else
  fortune | pokesay -WujbC -F
fi

# . "$HOME/.cargo/env"
. "$HOME/.secrets"
. "$HOME/.local/bin/env"
