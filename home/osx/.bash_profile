# Exit if we are a login shell, and ~/.bash_profile has already been sourced.
if ! $(shopt -q login_shell); then
  echo "~~ non-login shell, exiting"
  return 0
else
  echo "~~ login shell"
  if [ "${BASH_PROFILE_SOURCED:-}" == "true" ]; then
    source "$HOME/.bashrc"
    return 0
  fi
fi
echo "~~ sourcing .bash_profile"

# Link Homebrew installs in $HOME/bin
[ -d /usr/local/bin ] && PATH="/usr/local/bin:$PATH"
[ -d "$HOME/bin" ] && PATH="$HOME/bin:$PATH"

# TODO: Re-enable if needed, have switched to alacritty for the moment
# $HOME/bin/iterm_set_title_colour.sh $(hostname)

# export PYENV_ROOT="$HOME/.pyenv"
export PYTHONPATH="$PYENV_ROOT:$HOME/python-pkgs/lib/python/"
export CARGO_HOME=$HOME/.cargo
export GOPATH=$HOME/go
# export GOROOT=/usr/local/go

PATH="$PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH"       # Add python bins & shims under PYENV_ROOT
PATH="$HOME/.rvm/bin:$PATH"                          # Add rvm binaries
PATH="/usr/local/opt/coreutils/libexec/gnubin:$PATH" # Ensure that GNU utils are used over BSD
PATH="$PATH:/opt/homebrew/bin"                       # Add homebrew bins
PATH="/Library/Frameworks/Python.framework/Versions/3.11/bin:${PATH}"
PATH="/Users/tomm/Library/Python/3.11/:${PATH}"
PATH="$PATH:$HOME/Personal/dev/nvim-osx64/bin"       # Neovim
PATH="$CARGO_HOME:$CARGO_HOME/bin:$PATH"
PATH="$GOPATH/bin:$GOROOT/bin:$PATH"

export PATH
export TERM=xterm-256color

[ -r "$HOME/.fzf.bash" ] && source "$HOME/.fzf.bash"

# TODO: Should probably just remove these. They're really slow to load and
# affect the speed of opening any new bash session
# Load Ruby Version Manager & pyenv
# [[ -s "$HOME/.rvm/scripts/rvm" ]] && . "$HOME/.rvm/scripts/rvm"
# command -v pyenv 1>/dev/null 2>&1 && eval "$(pyenv init -)"

# Silence OSX Catalina warning about using bash instead of zsh
export BASH_SILENCE_DEPRECATION_WARNING=1

export BASH_PROFILE_SOURCED="true"

source "$HOME/.bashrc"
[ $TMUX ] || tmux -2
