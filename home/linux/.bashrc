#!/bin/bash
#
# github.com/tmck-code/dotfiles

# NOTE: Enter tmux in your .bash_profile, before entering .bashrc
if [ -n "${DEBUG:-}" ]; then
  echo '{"sourcing": ".bashrc"}'
  echo -n '{"$PS1": '
  [ -z "$PS1" ] && echo 'false}' || echo 'true}'
  echo -n '{".bash_profile sourced": '
  [ -z "${BASH_PROFILE_SOURCED:-}" ] && echo 'false}' || echo 'true}'
fi

# My utils that need to set before using tmux
for dirpath in $HOME/bin $HOME/bin/streaming $HOME/.local/bin /usr/local/bin; do
  [ -d "${dirpath}" ] && PATH="$PATH:${dirpath}"
done
export PATH

# My utils that need to set when using tmux and other tools
[ -f ~/.bash_aliases ] && source "$HOME/.bash_aliases"

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

# Change the file location because certain bash sessions truncate .bash_history file upon close.
# - http://superuser.com/questions/575479/bash-history-truncated-to-500-lines-on-each-login
export HISTFILE="$HOME/.bash_eternal_history"
# Force prompt to write history after every command (http://superuser.com/questions/20900/bash-history-loss)
PROMPT_COMMAND="history -a; $PROMPT_COMMAND"

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

  local commit
  if [ -f "${gitdir}/refs/heads/${GITBRANCH}" ]; then
    read -r commit < "${gitdir}/refs/heads/${GITBRANCH}"
  elif [ -f "${gitdir}/ORIG_HEAD" ]; then
    read -r commit < "${gitdir}/ORIG_HEAD"
  fi
  export GITCOMMIT="${commit:0:9}"
}

PS1_green='\[\e[1;32m\]'
PS1_purple='\[\e[3;35m\]'
PS1_reset='\[\e[0m\]'
PS1_yellow_bg='\[\e[1;33m\]'

_mk_prompt() {
  history -a # Update the a/.bash_history every time

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
export PROMPT_COMMAND="history -a; $PROMPT_COMMAND"

export LESS_TERMCAP_mb=$'\e[1;32m'
export LESS_TERMCAP_md=$'\e[1;32m'
export LESS_TERMCAP_me=$'\e[0m'
export LESS_TERMCAP_se=$'\e[0m'
export LESS_TERMCAP_so=$'\e[01;33m'
export LESS_TERMCAP_ue=$'\e[0m'
export LESS_TERMCAP_us=$'\e[1;4;31m'

# Detect if in SSH/SCP session, as printing the pokesay message causes scp to fail
# Only print the pokemon fortune if:
# - there isn't an SSH session detected (scp/ssh etc)
if [ -z "${SSH_CONNECTION:-}" ]; then
  # Present a pretty message, with a small chance to print a "shiny" version
  fortune | pokesay -jCub -w 40
fi

