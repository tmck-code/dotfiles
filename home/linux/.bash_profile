#!/bin/bash

# export DEBUG=true

if [ -n "${DEBUG:-}" ]; then
  echo '{"file": ".bash_profile", "sourcing": ".bash_profile", "DEBUG": "'${DEBUG:-}'"}'
fi
# Exit if we are a login shell, and ~/.bash_profile has already been sourced.

if ! shopt -q login_shell; then
  [ -n "${DEBUG:-}" ] && echo '{"file": ".bash_profile", "status": "exiting", "is login shell?": false"}'
  return 0
elif [ "${BASH_PROFILE_SOURCED:-}" == "true" ] && [ -n "$PS1" ]; then
  [ -n "${DEBUG:-}" ] && echo -n '{"status": "exiting", ".bash_profile sourced": true}'
  . ~/.bashrc
  return 0
fi

export BASH_PROFILE_SOURCED=true

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
PATH="$PATH:/usr/local/go/bin:$NVM_DIR"
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
  # "$HOME/.venv/bin/activate" # pyhon virtual env
  "$HOME/.uvenv/bin/activate" # pyhon virtual env
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

# Finish ----------------------------------------

# Enter tmux before entering .bashrc
# TODO: improve this behaviour (?)
if [ $TERM == "tmux-256color" ]; then
  [ -n "${DEBUG:-}" ] && echo "{"already in tmux?": true}"
else
  [ -n "${DEBUG:-}" ] && echo "{"status": "launching tmux", "already in tmux?": false}"
  tmux -2
fi

if [ -f "$HOME/.bashrc" ]; then
  [ -n "${DEBUG:-}" ] && echo '{"file": ".bash_profile", "sourcing": ".bashrc", "DEBUG": "'${DEBUG:-}'"}'
  source ~/.bashrc
fi
