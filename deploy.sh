#!/bin/bash

set -euxo pipefail

mv -v $HOME/.bashrc $HOME/.bashrc.bak

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
  ln -svf "$PWD/${dotfile}" "$HOME/.${dotfile}"
done

mkdir -p $HOME/bin && cp -Rv bin/* $HOME/bin/

