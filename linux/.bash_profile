# Exit if we are a login shell, and ~/.bash_profile has already been sourced.
if ! $(shopt -q login_shell); then
  echo "~~ non-login shell, exiting"
  return 0
else
  if [ "${BASH_PROFILE_SOURCED:-}" == "true" ] && [ -n "$PS1" ]; then
    source ~/.bashrc
    return 0
  fi
fi
echo "~~ sourcing .bash_profile"

# PATH ------------------------------------------

# Load personal scripts
PATH="$PATH:$HOME/bin/:$HOME/.local/bin"

# Go paths
export GOPATH=$HOME/go
export GOROOT=/usr/local/go
PATH=$PATH:$GOPATH/bin:$GOROOT/bin
# Pyenv paths
export PYENV_ROOT="$HOME/.pyenv"
PATH="$PYENV_ROOT/bin:$PATH"

export PATH

# ENV configs -----------------------------------

# Use vim as editor instead of the default 'nano'
alias crontab="VIM_CRONTAB=true crontab"
export EDITOR=vim
export VISUAL=vim

export TERM=xterm-256color
export BASH_PROFILE_SOURCED="true"

# Program setup/sourcing ------------------------

# Enable bash completion
[[ -r /etc/bash_completion ]] && . /etc/bash_completion
[[ -d /etc/bash_completion.d ]] && . /etc/bash_completion.d/*

# Enable pyenv
eval "$(pyenv init --path)"
# Source cargo/rust
source "$HOME/.cargo/env"

# Finish ----------------------------------------

# Enter tmux before entering .bashrc
# Ensure that we're not already in tmux, and attach to existing session if possible
if [ ! $TMUX ]; then
  tmux -2
  # tmux ls &> /dev/null && tmux a || tmux -2
fi

[ -f "$HOME/.bashrc" ] && source ~/.bashrc
