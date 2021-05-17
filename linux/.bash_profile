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

# Load personal scripts
PATH="$PATH:$HOME/bin/:$HOME/.local/bin"

# Set up go
export GOPATH=$HOME/go
export GOROOT=/usr/local/go
PATH=$PATH:$GOPATH/bin:$GOROOT/bin

alias crontab="VIM_CRONTAB=true crontab"
export EDITOR=vim
export VISUAL=vim

# Enable bash completion
[[ -r /etc/bash_completion ]] && . /etc/bash_completion
[[ -d /etc/bash_completion.d ]] && . /etc/bash_completion.d/*

# Export final path & other important vars
export PATH
export TERM=xterm-256color

export BASH_PROFILE_SOURCED="true"

# Enter tmux before entering .bashrc
# Ensure that we're not already in tmux, and attach to existing session if possible
if [ ! $TMUX ]; then
  tmux -2
  # tmux ls &> /dev/null && tmux a || tmux -2
fi

eval "$(pyenv init -)"
[ -f "$HOME/.bashrc" ] && source ~/.bashrc
source "$HOME/.cargo/env"
