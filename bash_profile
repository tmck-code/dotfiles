source ~/.profile
export PATH=$PATH:/Applications/Postgres.app/Contents/Versions/latest/bin

[[ -s "$HOME/.rvm/scripts/rvm" ]] && source "$HOME/.rvm/scripts/rvm" # Load RVM into a shell session *as a function*
if [ -f ~/.bashrc ]; then . ~/.bashrc; fi

# Add ruby and rvm to the PATH
export PATH="$PATH:$HOME/.rvm/bin"
export PATH="$HOME/.gem/ruby/2.4.2/bin:$PATH"
export GEM_PATH="$HOME/.gem/ruby/2.4.2/bin:$GEM_PATH"

# Load RVM into a shell session *as a function*
[[ -s "$HOME/.rvm/scripts/rvm" ]] && source "$HOME/.rvm/scripts/rvm"

# Load personal scripts
export PATH="$PATH:$HOME/bin/"

# Set up go
export GOPATH=$HOME/go
export GOROOT=/usr/local/opt/go/libexec
export PATH=$PATH:$GOPATH/bin
export PATH=$PATH:$GOROOT/bin

alias crontab="VIM_CRONTAB=true crontab"
export EDITOR=vim
export VISUAL=vim

