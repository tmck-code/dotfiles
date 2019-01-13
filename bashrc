#!/bin/bash
# github.com/tmck-code/dotfiles

[ -z "$PS1" ] && return 0

# Homebrew installs to $HOME/bin now, need to set before using tmux
[ -d ~/bin ] && export PATH="$HOME/bin:/usr/local/bin:$PATH"

# Enter tmux as soon as possible, rather than at the end of the file
# This avoids loading things again
[ $TMUX ] || tmux -2

shopt -s histappend  # append to the history file, don't overwrite it
HISTFILESIZE=10000000  # largest history written to file at one time - 10 million lines
HISTSIZE=10000000      # large history file - 10 million lines
HISTCONTROL=ignoreboth # don't put duplicate lines or lines starting with space in the history.
PROMPT_DIRTRIM=2

# Function to shorten the current directory
short_pwd() {
  local pwd=$(pwd)
  pwd=${pwd/#$HOME/\~}
  sed 's:\([^/]\)[^/]*/:\1/:g' <<<"$pwd"
}

if [[ "$USER" == "root" ]]; then
  export PS1="\[\e[1;31m\]\u\[\e[0m\] \[\e[1;33m\]\w\[\e[0m\] ";
else
  export PS1="\[\e[1;33m\]\$(short_pwd)\[\e[0m\] ";
fi

# Going to export PS1 again later with a prefix, so keep a static copy
export _MK_PROMPT_ORIG_PS1="$PS1"

# 100% pure Bash (no forking) function to determine the name of the current git branch
gitbranch() {
  export GITBRANCH=""

  local repo="${_GITBRANCH_LAST_REPO-}"
  local gitdir=""

  # If repo is set, and we are in that repo
  if [[ ! -z "${repo}" && "$PWD" == "${repo}/*" ]]; then
    gitdir="$repo/.git"
  else
    local curr="$PWD"
    while [[ ! -z "$curr" ]]; do
      if [[ -e "$curr/.git" ]]; then
        repo="$curr"
        gitdir="$curr/.git"
        break
      fi
      curr="${curr%/*}"
    done
  fi

  if [[ -z "$gitdir" ]]; then
    unset _GITBRANCH_LAST_REPO
    return 0
  fi

  export _GITBRANCH_LAST_REPO="${repo}"

  local head=""
  read head < "$gitdir/HEAD"
  case "$head" in
    ref:*) export GITBRANCH="${head##*/}" ;;
    "")  return 0 ;;
    *)   export GITBRANCH="$branch""d:${head:0:7}" ;;
  esac
}

PS1_green='\[\e[32m\]'
PS1_reset='\[\e[0m\]'

_mk_prompt() {
  # Update the ~/.bash_history every time
  history -a

  # Change the window title of X terminals
  case $TERM in
    xterm*) echo -ne "\033]0;${USER}@${HOSTNAME%%.*}:${PWD/$HOME/~}\007" ;;
    screen) echo -ne "\033_${USER}@${HOSTNAME%%.*}:${PWD/$HOME/~}\033\\" ;;
  esac

  gitbranch

  local prefix=("\D{%T}")
  if [[ ! -z "$GITBRANCH" ]]; then
    prefix+=("${PS1_green}$GITBRANCH${PS1_reset}")

    # Modified files
    if [ ! -z "$(git ls-files -m)" ]; then
    prefix+=("✹")
    fi
    # New, untracked files
    if [ ! -z "$(git ls-files --others --exclude-standard --directory --no-empty-directory --error-unmatch -- ':/*' 2> /dev/null)" ]; then
    prefix+=("✭")
    fi
  fi
  export PS1=" ${prefix[@]} │ ☯ $_MK_PROMPT_ORIG_PS1"
}

export PROMPT_COMMAND=_mk_prompt

# Load aliases
[ -f ~/.bash_aliases ]   && source  ~/.bash_aliases

[ -f ~/bin/uptime_tmux ] && source ~/bin/uptime_tmux
[ -f ~/bin/battery ]     && source ~/bin/battery

# Enable colours by default
export CLICOLOR="exfxcxdxbxegedabagacad" # enable colours
alias grep="grep --color=auto"

# Present a pretty message
fortune -a | pokemonsay | sed 's/^/  /g'
echo

