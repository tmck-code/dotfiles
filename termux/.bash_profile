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
export GOROOT=$PREFIX/lib/go
PATH=$PATH:$GOPATH/bin

export PATH

[ -f "$HOME/bin/z.sh" ] && source $HOME/bin/z.sh

# Export some helper ENV vars
if [ "$(uname -o)" == "Android" ]; then
  export TERMUX=1
fi
export BASH_PROFILE_SOURCED="true"

[ -r "$HOME/bin/theme" ] && source "$HOME/bin/theme"
# Load previous theme
set -o allexport; source $HOME/.termux/current; set +o allexport

h="$(date +%H)"
if [[ "$h" > "19" ]]; then
  [[ "$TERMUX_THEME" = "light" ]] && set_theme dark
elif [[ "$h" > "07" ]]; then
  [[ "$TERMUX_THEME" = "dark" ]] && set_theme light
fi

# Load tmux once before entering .bashrc, ensure that we're not already in tmux
[ $TMUX ] || tmux

# [ -f "$HOME/.bashrc" ] && source ~/.bashrc
