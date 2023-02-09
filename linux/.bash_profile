#!/bin/bash

# echo "~~ sourcing .bash_profile"
if ! shopt -q login_shell; then
  echo "~~ non-login shell, exiting"
  return 0
else
  if [ "${BASH_PROFILE_SOURCED:-}" == "true" ] && [ -n "$PS1" ]; then
    echo "~~ .bash_profile already sourced"
    # source ~/.bashrc
    return 0
  fi
fi

# ENV configs -----------------------------------

# Use vim as editor instead of the default 'nano'
alias crontab="VIM_CRONTAB=true crontab"
export EDITOR=vim
export VISUAL=vim

export TERM=xterm-256color
export BASH_PROFILE_SOURCED="true"

# PATH ------------------------------------------

# Load personal scripts
PATH="$PATH:$HOME/bin/:$HOME/.local/bin"
# Language paths
# - golang
export GOPATH="$HOME/go"
export GOROOT="/usr/lib/go-1.19/"
PATH="$PATH:$GOPATH/bin"

# Tool paths
PATH="$PATH:.emacs.d/bin"

export PATH

# Bash completion -------------------------------
sources=(
  "/etc/bash_completion" # bash/shell completions dir
  "/usr/share/bash-completion/bash_completion" # bash/shell completions dir
  "$HOME/.cargo/env" # cargo/rust
  "$HOME/dev/z/z.sh" # z - jump around
)

for f in "${sources[@]}"; do
  if test -f "$f"; then
    source "$f"
  elif test -d "$f"; then
    for i in "${f}/*"; do
      if test -f "$i"; then
        source "$i"
      fi
    done
  fi
done

# Finish ----------------------------------------

# Enter tmux, which has default command bash -i, which will load the bashrc
if [ ! "$TMUX" ]; then
  tmux -2
else
  echo "loading bashrc!"
  source "$HOME/.bashrc"
fi

