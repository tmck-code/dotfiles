#!/bin/bash

[ -n "${DEBUG:-}" ] && echo "~~ $HOME/.bash_profile"
# Exit if we are a login shell, and ~/.bash_profile has already been sourced.

if ! shopt -q login_shell; then
  [ -n "${DEBUG:-}" ] && echo "~~ non-login shell, exiting"
  return 0
else
  if [ "${BASH_PROFILE_SOURCED:-}" == "true" ] && [ -n "$PS1" ]; then
    echo "BASH_PROFILE_SOURCED=${BASH_PROFILE_SOURCED}"
    source ~/.bashrc
  fi
fi
[ -n "${DEBUG:-}" ] && echo "~~ sourcing $HOME/.bash_profile"

# ENV configs -----------------------------------

# Use vim as editor instead of the default 'nano'
alias crontab="VIM_CRONTAB=true crontab"
export EDITOR=nvim
export VISUAL=nvim

# PATH ------------------------------------------

# Load personal scripts
PATH="$PATH:$HOME/bin/:$HOME/.local/bin:/usr/local/bin"
# Language paths
# - golang
export GOPATH="$HOME/go"
# export GOROOT="/usr/lib/go-1.18/"
export NVM_DIR="$HOME/.nvm" # node version manager
PATH="/usr/local/go/bin:$PATH:$NVM_DIR"
# Tool paths
PATH="$PATH:.emacs.d/bin"
export PATH


# Bash completion -------------------------------
sources_dirs=(
  "/etc/bash_completion.d" # bash completions
)
sources_files=(
  # personal vars -------------------------------
  "$HOME/.secrets"           # my api keys/secrets
  # terminal experience -------------------------
  "/usr/share/bash-completion/bash_completion" # this is sourced by /etc/bash_completion, so just source it directly
  "$HOME/dev/z/z.sh"         # z - jump around e.g. `z lang` == `cd $HOME/dev/lang_tests/`
  # language version managers -------------------
  "$HOME/.cargo/env"         # cargo/rust
  "$HOME/.venv/bin/activate" # pyhon virtual env
  "$NVM_DIR/nvm.sh"          # nvm (node version manager)
)

for f in "${sources_dirs[@]}"; do
  for i in "$f"/*; do
    test -f "$i" && source "$i"
  done
done

for f in "${sources_files[@]}"; do
  test -f "$f" && source "$f"
done

. $HOME/.venv/bin/activate

# Finish ----------------------------------------

# Enter tmux before entering .bashrc
# TODO: improve this behaviour (?)
if test -v TMUX; then
  [ -n "${DEBUG:-}" ] && echo "~~ \$Already in a TMUX session, skipping session launch"
else
  [ -n "${DEBUG:-}" ] && echo "~~ \$TMUX is unset, launching tmux"
  tmux -2
fi

if [ -f "$HOME/.bashrc" ]; then
  [ -n "${DEBUG:-}" ] && echo "~~ sourcing $HOME/.bashrc from $HOME/.bash_profile"
  source ~/.bashrc
fi
. "$HOME/.cargo/env"
