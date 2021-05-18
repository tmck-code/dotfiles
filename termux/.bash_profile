if $(shopt -q login_shell); then
  echo 'Login shell'
  if [ ! -z "${BASH_PROFILE_SOURCED:-}" ]; then
    echo '~/.bash_profile already loaded, exiting'
    source $HOME/.bashrc
    exit 0
  fi
fi


# Load Bash completions
if [ -f "$PREFIX/etc/bash_completion.d/*" ]; then
  source $PREFIX/etc/bash_completion.d/*
fi
# Set vim as default editor
alias crontab="VIM_CRONTAB=true crontab"
export EDITOR=vim
export VISUAL=vim

# Load personal scripts
PATH="$PATH:$HOME/bin/"
# Set up go
export GOPATH=$HOME/go
PATH=$PATH:$GOPATH/bin

export PATH

source $HOME/bin/z.sh

# Export some helper ENV vars
if [ "$(uname -o)" == "Android" ]; then
  export TERMUX=1
fi
export BASH_PROFILE_SOURCED="true"

# Load tmux once before entering .bashrc, ensure that we're not already in tmux
[ $TMUX ] || tmux
echo "entered tmux in bash_profile"

[ -f "$HOME/.bashrc" ] && source ~/.bashrc
