#!/bin/bash

set -euxo pipefail

if [ -z "${1:-}" ]; then
  echo "Must provide an OS as \$1"
  exit 1
fi

OS="${1}"

mv -v $HOME/.bashrc $HOME/.bashrc.bak || echo "- No bashrc file found! Nothing to back up here"

general_dotfiles=$(cat <<EOF
gitconfig
rubocop.yml
tmux.conf
vimrc
EOF
)

linux_dotfiles=$(cat <<EOF
bash_aliases
bash_profile
bashrc
inputrc
tmux.conf
EOF
)

osx_kitty_dotfiles=$(cat <<EOF
kitty.conf
kitty.light-gruvbox.conf
EOF
)

function install_general() {
    install_set "${general_dotfiles[@]}"
}

function install_linux() {
  install_set "${linux_dotfiles[@]}"
}

function install_osx() {
  install_set "{osx_dotfiles[@]}"
}

function install_set() {

}

install_general
install_linux

mkdir -p $HOME/bin && cp -Rv bin/* $HOME/bin/

