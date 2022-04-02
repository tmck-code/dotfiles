#!/bin/bash

echo "~~ sourcing .bash_profile"
# Exit if we are a login shell, and ~/.bash_profile has already been sourced.
if ! $(shopt -q login_shell); then
  echo "~~ non-login shell, exiting"
  return 0
else
  if [ "${BASH_PROFILE_SOURCED:-}" == "true" ] && [ -n "$PS1" ]; then
    echo "BASH_PROFILE_SOURCED=${BASH_PROFILE_SOURCED}"
    source ~/.bashrc
    return 0
  fi
fi
echo "~~ sourcing .bash_profile"

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
export GOPATH=$HOME/go
PATH=$PATH:$GOPATH/bin:$GOROOT/bin
PATH="$PYENV_ROOT/bin:$PATH"

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
for f in ${sources[@]}; do
  if test -f $f; then
    echo "sourcing $f"
    source "${f}"

  elif test -d $f; then

    echo "souring files from $f"
    for i in "${f}/*"; do
      test -f $i
      source "${i}"
    done
  fi
done



# Finish ----------------------------------------

# Enter tmux before entering .bashrc
# Ensure that we're not already in tmux, and attach to existing session if possible
# TODO: improve this behaviour
# tmux ls &> /dev/null && tmux a || tmux -2
if [ ! $TMUX ]; then
  tmux -2
fi

[ -f "$HOME/.bashrc" ] && source ~/.bashrc
