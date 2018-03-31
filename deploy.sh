#!/bin/bash

set -euxo pipefail

os="$1"

cp $HOME/.bashrc $HOME/.bashrc.bak

home_dotfiles=(
  bashrc
  bash_aliases
  inputrc
  gitconfig
  tmux.conf
  tmux.conf.local
  vimrc
)

for dotfile in ${home_dotfiles[@]}; do
  ln -sv ${dotfile} $HOME/.${dotfile}
done

mkdir $HOME/bin && cp -Rv bin/* $HOME/bin/

