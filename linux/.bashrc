#!/bin/bash
# github.com/tmck-code/dotfiles

# TODO: clarify this statement
# [ -z "$PS1" ] && echo "No \$PS1" && return 0
# [ -z "${BASH_PROFILE_SOURCED:-}" ] && echo "in .bashrc - .bash_profile not sourced" && return 0

# Enter tmux before entering .bashrc
# Ensure that we're not already in tmux, and attach to existing session if possible
if [ ! $TMUX ]; then
  tmux -2
  # tmux ls &> /dev/null && tmux a || tmux -2
fi
# My utils that need to set before using tmux
for dirpath in $HOME/bin $HOME/.local/bin /usr/local/bin; do
  [ -d "${dirpath}" ] && PATH="$PATH:${dirpath}"
done
export PATH

# My utils that need to set when using tmux and other tools
[ -d ~/bin ] && export PATH="$HOME/bin:$PATH"
[ -f ~/.bash_aliases ] && source "$HOME/.bash_aliases"

shopt -s histappend             # append to the history file, don't overwrite it
export HISTFILESIZE=10000000000 # largest history written to file at one time
export HISTSIZE=100000000000000 # large history file
export HISTCONTROL=ignoreboth   # don't put duplicate lines or lines starting with space in the history.
export PROMPT_DIRTRIM=2

# Function to shorten the current directory
short_pwd() {
  sed 's:\([^/]\)[^/]*/:\1/:g' <<< "${PWD/#${HOME}/\~}"
}

if [[ "$USER" == "root" ]]; then
  export PS1="\[\e[1;31m\]\u\[\e[0m\] \[\e[1;33m\]\w\[\e[0m\] "
else
  export PS1="\[\e[1;33m\]\$(short_pwd)\[\e[0m\] "
fi

# 100% pure Bash (no forking) function to determine the name of the current git branch
gitbranch() {
  export GITBRANCH=""

  local repo="${_GITBRANCH_LAST_REPO-}"
  local gitdir=""

  # If repo is set, and we are in that repo
  if [[ -n "${repo:-}" && "$PWD" == "${repo}/*" ]]; then
    gitdir="$repo/.git"
  else
    local curr="$PWD"
    while [[ -n "$curr" ]]; do     # while we are in a dir
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
    return 0
  fi

  export _GITBRANCH_LAST_REPO="${repo}"

  # Read and export git branch from the HEAD file
  local head
  read -r head < "${gitdir}/HEAD"
  case "${head}" in
    ref:*) export GITBRANCH="${head##*/}" ;;
    "")  return 0 ;;
    *)   export GITBRANCH="d:${head:0:7}" ;;
  esac

  if [ -f "${gitdir}/ORIG_HEAD" ]; then
    local commit
    read -r commit < "${gitdir}/ORIG_HEAD"
    export GITCOMMIT="${commit:0:9}"
  fi
}

PS1_green='\[\e[1;32m\]'
PS1_purple='\[\e[3;35m\]'
PS1_reset='\[\e[0m\]'
PS1_yellow_bg='\[\e[1;33m\]'

_mk_prompt() {
  history -a # Update the ~/.bash_history every time

  # Change the window title of X terminals
  if [[ "$TERM" =~ xterm* ]]; then
    echo -ne "\033]0;${USER}@${HOSTNAME%%.*}:${PWD/$HOME/~}\007"
  fi

  gitbranch

  sep="∈"
  local prefix=("\D{%T}")
  if [ -n "${GITBRANCH:-}" ]; then
    prefix+=("${PS1_yellow_bg}${sep}${PS1_reset} ${PS1_green}${GITBRANCH}${PS1_reset} / ${PS1_purple}${GITCOMMIT}${PS1_reset}")

    # Modified files
    if [ -n "$(git ls-files -m)" ]; then
      prefix+=("✹")
    fi
    # New, untracked files
    if [ -n "$(git ls-files --others --exclude-standard --directory --no-empty-directory --error-unmatch -- ':/*' 2> /dev/null)" ]; then
      prefix+=("✭")
    fi
  fi
  export PS1=" ${prefix[@]}\n ☯ $_MK_PROMPT_ORIG_PS1"
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

[ -r /etc/bash_completion ]    && source /etc/bash_completion
[ -r "$HOME/bin/z/z.sh" ]      && source "$HOME/bin/z/z.sh"
[ -r "$HOME/bin/uptime_tmux" ] && source "$HOME/bin/uptime_tmux"
[ -r "$HOME/bin/theme" ] && source "$HOME/bin/theme"
[ -r "$HOME/.secrets" ] && source "$HOME/.secrets"

# Check if we're running an interactive shell, as printing the pokesay message
# causes scp to fail
if [ -n "$PS1" ]; then # && $(shopt -q login_shell); then
  # Present a pretty message, with a small chance to print a "shiny" version
  if [ $(( RANDOM % 10 )) == 0 ]; then
    fortune | pokesay -nowrap | lolcat
  else
    fortune | pokesay -nowrap
  fi
fi
