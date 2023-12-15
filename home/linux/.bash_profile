#!/bin/bash

echo "~~ $HOME/.bash_profile"
# Exit if we are a login shell, and ~/.bash_profile has already been sourced.

if ! $(shopt -q login_shell); then
  echo "~~ non-login shell, exiting"
  return 0
else
  if [ "${BASH_PROFILE_SOURCED:-}" == "true" ] && [ -n "$PS1" ]; then
    echo "BASH_PROFILE_SOURCED=${BASH_PROFILE_SOURCED}"
    source ~/.bashrc
  fi
fi
echo "~~ sourcing $HOME/.bash_profile"

# ENV configs -----------------------------------

# Use vim as editor instead of the default 'nano'
alias crontab="VIM_CRONTAB=true crontab"
export EDITOR=vim
export VISUAL=vim

export TERM=xterm-256color

# PATH ------------------------------------------

# Load personal scripts
PATH="$PATH:$HOME/bin/:$HOME/.local/bin:/usr/local/bin"
# Language paths
# - golang
export GOPATH="$HOME/go"
export GOROOT="/usr/lib/go-1.19/"
PATH="$PATH:$GOPATH/bin"
# Tool paths
PATH="$PATH:.emacs.d/bin"
export PATH

# Bash completion -------------------------------
sources_dirs=(
  "/usr/share/bash-completion/bash_completion" # bash/shell completions dir
)
sources_files=(
  "/usr/share/doc/git/contrib/completion/git-completion.bash" # git completions
  "$HOME/.cargo/env" # cargo/rust
  "$HOME/dev/z/z.sh" # z - jump around
  "$HOME/.secrets" # my api keys
)

for f in "${sources_dirs[@]}"; do
  for i in "$f"/*; do
    test -f "$i" && source "$i"
  done
done

for f in "${sources_files[@]}"; do
  test -f "$f" && source "$f"
done

# Finish ----------------------------------------

# Enter tmux before entering .bashrc
# Ensure that we're not already in tmux, and attach to existing session if possible
# TODO: improve this behaviour
# tmux ls &> /dev/null && tmux a || tmux -2
# if [ ! $TMUX ]; then
#   [ -n "${DEBUG:-}" ] && echo "~~ \$TMUX is unset, launching tmux"
#   tmux -2
# fi

if [ -f "$HOME/.bashrc" ]; then
  [ -n "${DEBUG:-}" ] && echo "~~ sourcing $HOME/.bashrc from $HOME/.bash_profile"
  source ~/.bashrc
fi
