#!/bin/bash

function print_256_colours() {
  # From https://misc.flogisoft.com/bash/tip_colors_and_formatting
  local fgbg=$1

  echo "╭──────────────────────────────────────────────────────────────────────────╮"
  echo -n "│ "
  for color in {0..255} ; do
    # Display the color
    printf "\e[${fgbg};5;%sm  ${fgbg};5;%-3s  \e[0m" $color $color
    # Display 6 colors per lines
    if [ $((($color + 1) % 6)) == 4 ]; then
      if [ $color -eq 3 ] ; then
        echo -ne "                         │\n│ "
      elif [ $color -ne 255 ] ; then
        echo -ne " │\n│ "
      else
        echo -ne " │\n"
      fi
    fi
  done
  echo "╰──────────────────────────────────────────────────────────────────────────╯"
}

function print_8_16_colours() {
  # From https://misc.flogisoft.com/bash/tip_colors_and_formatting

  local reset="\e[0m"
  echo "╭─────────────────────────────────────────────────────╮"
  printf "│ 0;30m \e[0;30mBlack  ${reset}1;30m \e[1;30mBlack bold  0;90m \e[0;90mBlack bright\e[0m   │\n"
  printf "│ 0;31m \e[0;31mRed    ${reset}1;31m \e[1;31mRed bold    0;91m \e[0;91mRed bright\e[0m     │\n"
  printf "│ 0;32m \e[0;32mGreen  ${reset}1;32m \e[1;32mGreen bold  0;92m \e[0;92mGreen bright\e[0m   │\n"
  printf "│ 0;33m \e[0;33mYellow ${reset}1;33m \e[1;33mYellow bold 0;93m \e[0;93mYellow bright\e[0m  │\n"
  printf "│ 0;34m \e[0;34mBlue   ${reset}1;34m \e[1;34mBlue bold   0;94m \e[0;94mBlue bright\e[0m    │\n"
  printf "│ 0;35m \e[0;35mPurple ${reset}1;35m \e[1;35mPurple bold 0;95m \e[0;95mPurple bright\e[0m  │\n"
  printf "│ 0;36m \e[0;36mCyan   ${reset}1;36m \e[1;36mCyan bold   0;96m \e[0;96mCyan bright\e[0m    │\n"
  printf "│ 0;37m \e[0;37mWhite  ${reset}1;37m \e[1;37mWhite bold  0;97m \e[0;97mWhite bright\e[0m   │\n"
    echo "│─────────────────────────────────────────────────────│"
  printf "│ 0;40m \e[0;40mBlack  ${reset}1;40m \e[1;40mBlack bold ${reset}0;100m  \e[0;100mBlack bright\e[0m  │\n"
  printf "│ 0;41m \e[0;41mRed    ${reset}1;41m \e[1;41mRed bold ${reset}0;101m    \e[0;101mRed bright\e[0m    │\n"
  printf "│ 0;42m \e[0;42mGreen  ${reset}1;42m \e[1;42mGreen bold ${reset}0;102m  \e[0;102mGreen bright\e[0m  │\n"
  printf "│ 0;43m \e[0;43mYellow ${reset}1;43m \e[1;43mYellow bold ${reset}0;103m \e[0;103mYellow bright\e[0m │\n"
  printf "│ 0;44m \e[0;44mBlue   ${reset}1;44m \e[1;44mBlue bold ${reset}0;104m   \e[0;104mBlue bright\e[0m   │\n"
  printf "│ 0;45m \e[0;45mPurple ${reset}1;45m \e[1;45mPurple bold ${reset}0;105m \e[0;105mPurple bright\e[0m │\n"
  printf "│ 0;46m \e[0;46mCyan   ${reset}1;46m \e[1;46mCyan bold ${reset}0;106m   \e[0;106mCyan bright\e[0m   │\n"
  printf "│ 0;47m \e[0;47mWhite  ${reset}1;47m \e[1;47mWhite bold ${reset}0;107m  \e[0;107mWhite bright\e[0m  │\n"
  echo "╰─────────────────────────────────────────────────────╯"
}

function 0r8ht_src_codes() {
  echo -e "\e[0m  Reset / Normal\e[0m"
  echo -e "\e[1m  Bold or increased intensity\e[0m"
  echo -e "\e[2m  Faint (decreased intensity)\e[0m"
  echo -e "\e[3m  Italic\e[0m"
  echo -e "\e[4m  Underline\e[0m"
  echo -e "\e[5m  Slow Blink\e[0m"
  echo -e "\e[7m  Reverse video\e[0m"
  echo -e "\e[8m  Conceal\e[0m"
  echo -e "\e[9m  Crossed-out\e[0m"
  echo -e "\e[21m  Bold off or Double underline\e[0m"
  echo -e "\e[22m  Normal color or intensity\e[0m"
  echo -e "\e[23m  Not italic\e[0m"
  echo -e "\e[24m  Underline off\e[0m"
  echo -e "\e[25m  Blink off\e[0m"
  echo -e "\e[27m  Positive image\e[0m"
  echo -e "\e[28m  Reveal\e[0m"
  echo -e "\e[29m  Not crossed out\e[0m"
}

echo "256 Colour Demo"

echo -e "\nForeground Colours:"
print_256_colours 38

echo -e "\nBackground Colours:"
print_256_colours 48

echo -e "\n8/16 Colour Demo"
print_8_16_colours 38

echo -e "Graphic Rendition (SGR) Codes:"
0r8ht_src_codes
