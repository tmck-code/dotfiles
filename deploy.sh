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
  for d in "$(echo ${general_dotfiles[@]})"; do
    ln -s "$(pwd)/general/${d}"
  done
}

function install_linux() {
  for d in "$(echo ${linux_dotfiles[@]})"; do
    ln -s "$(pwd)/linux/${d}"
  done
}

function install_osx() {
  for d in "$(echo ${osx_dotfiles[@]})"; do
    ln -s "$(pwd)/osx/${d}"
  done
}

function install_set() {
  dotfiles="${1}"
  for i in "${dotfiles[@]}"; do
    echo "${i}"
  done
}

install_general
install_linux

mkdir -p $HOME/bin && cp -Rv bin/* $HOME/bin/

